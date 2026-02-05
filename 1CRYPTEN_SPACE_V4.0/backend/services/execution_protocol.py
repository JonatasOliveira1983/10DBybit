"""
🛡️ Protocolo de Execução Elite V5.0 - Adaptive Stop Loss
==========================================================
Módulo responsável por executar lógica de fechamento independente por slot.
Implementa Flash Close (SNIPER), Surf Shield (SURF) e Adaptive SL com telemetria visual.

Author: Antigravity AI
Version: 5.0 (Adaptive Stop Loss)

V5.0 Changes:
- SNIPER: Adaptive SL que move conforme ROI sobe (não mais fixo)
- SURF: Escada melhorada com mais níveis de proteção
- NEW: Status TRAILING para indicar SL em movimento
"""

import logging
import time
from typing import Tuple, Optional, Dict, Any

logger = logging.getLogger("ExecutionProtocol")

class ExecutionProtocol:
    """
    Executa a lógica de fechamento para cada slot de forma independente.
    Cada ordem tem seu próprio 'contrato de execução'.
    
    V5.0 Adaptive Stop Loss:
    - SNIPER: Flash Close com TP nativo + Adaptive Trailing SL
    - SURF: Surf Shield com escada granular melhorada
    """
    
    def __init__(self):
        self.leverage = 50
        
        # === SNIPER CONFIG (Slot 1) ===
        self.sniper_target_roi = 100.0    # 100% ROI = 2% movimento @ 50x
        self.sniper_stop_roi = -50.0      # Stop Loss inicial = -50% ROI (1% movimento)
        self.flash_zone_threshold = 80.0  # Zona Roxa: 80% do target (ROI >= 80%)
        
        # 🆕 V10.2: Relaxed Adaptive SL for SNIPER (ATR-Aware context)
        # We start trailing later to allow for "breathing" and "sniper" candle wicks.
        self.sniper_trailing_ladder = [
            {"trigger": 80.0, "stop_roi": 40.0},   # ROI 80%  → SL at +40% (Lock nice profit)
            {"trigger": 50.0, "stop_roi": 10.0},   # ROI 50%  → SL at +10% (Risk Zero Shield)
            {"trigger": 30.0, "stop_roi": -20.0},  # ROI 30%  → SL at -20% (instead of -10% or -50%)
        ]
        # Se ROI < 30%, mantém SL original dinâmico (ATR-based)
        
        # === VISUAL STATUS CODES ===
        # Usados pelo frontend para cores dos slots
        self.STATUS_SCANNING = "SCANNING"       # Azul - slot livre
        self.STATUS_IN_TRADE = "IN_TRADE"       # Dourado - posição aberta
        self.STATUS_RISK_ZERO = "RISK_ZERO"     # Turquesa - stop na entrada ou acima
        self.STATUS_FLASH_ZONE = "FLASH_ZONE"   # Roxo Neon - alvo iminente
        self.STATUS_TRAILING = "TRAILING"       # 🆕 Amarelo Ouro - SL foi movido mas ainda negativo
        self.STATUS_MEGA_PULSE = "MEGA_PULSE"   # 💎 V7.2: Sniper Trailing Profit (ROI > 100%)
        
    def get_visual_status(self, slot_data: Dict[str, Any], roi: float) -> str:
        """
        Determina o status visual do slot baseado no estado atual.
        
        Returns:
            Status code para coloração do slot no frontend
        """
        symbol = slot_data.get("symbol")
        slot_type = slot_data.get("slot_type", "SNIPER")
        current_stop = slot_data.get("current_stop", 0)
        entry_price = slot_data.get("entry_price", 0)
        
        # Slot vazio
        if not symbol or entry_price <= 0:
            return self.STATUS_SCANNING
        
        # SNIPER: Mega Pulse (ROI >= 100%), Flash Zone (80%+), Risk Zero, ou In Trade
        if slot_type == "SNIPER":
            if roi >= 100.0:
                return self.STATUS_MEGA_PULSE
            
            if roi >= self.flash_zone_threshold:
                return self.STATUS_FLASH_ZONE

            # V5.0: Detecta se SL foi movido para lucro (Risk Zero) ou apenas reduzido (Trailing)
            side = slot_data.get("side", "Buy")
            side_norm = (side or "").lower()
            if current_stop > 0 and entry_price > 0:
                if side_norm == "buy":
                    if current_stop >= entry_price:
                        return self.STATUS_RISK_ZERO
                    elif current_stop > entry_price * 0.99:
                        return self.STATUS_TRAILING
                elif side_norm == "sell":
                    if current_stop <= entry_price:
                        return self.STATUS_RISK_ZERO
                    elif current_stop < entry_price * 1.01:
                        return self.STATUS_TRAILING
            
            return self.STATUS_IN_TRADE
        
        return self.STATUS_IN_TRADE
        

    def calculate_roi(self, entry_price: float, current_price: float, side: str) -> float:
        """
        Calcula o ROI real considerando alavancagem 50x.
        
        Args:
            entry_price: Preço de entrada
            current_price: Preço atual
            side: 'Buy' ou 'Sell'
            
        Returns:
            ROI em porcentagem (ex: 100.0 = 100% de lucro)
        """
        if entry_price <= 0:
            return 0.0
            
        side_norm = (side or "").lower()
        
        if side_norm == "buy":
            price_diff = (current_price - entry_price) / entry_price
        else:  # Sell/Short
            price_diff = (entry_price - current_price) / entry_price
            
        roi = price_diff * self.leverage * 100
        
        # V6.0: ROI Sanity Guard - Cap extreme values to prevent UI breakage
        # This prevents the -600,000% ROI bug from naming collisions
        if roi > 5000: roi = 5000
        if roi < -5000: roi = -5000
        
        return roi
    
    async def _check_sentiment_weakness(self, symbol: str, side: str) -> bool:
        """
        V5.4.5: Checks if sentiment (CVD) is contradicting the trade.
        Returns True if 'weakness' is detected.
        """
        from services.redis_service import redis_service
        cvd = await redis_service.get_cvd(symbol)
        side_norm = side.lower()
        
        # Weakness threshold: 10k USD delta in opposite direction
        if side_norm == "buy" and cvd < -10000:
            logger.info(f"🛡️ [SENTI WEAKNESS] {symbol} | Long trade with Negative CVD: {cvd:.2f}")
            return True
        elif side_norm == "sell" and cvd > 10000:
            logger.info(f"🛡️ [SENTI WEAKNESS] {symbol} | Short trade with Positive CVD: {cvd:.2f}")
            return True
            
        return False

    async def process_sniper_logic(self, slot_data: Dict[str, Any], current_price: float, roi: float, atr: Optional[float] = None) -> Tuple[bool, Optional[str], Optional[float]]:
        """
        [V7.0] SINGLE TRADE SNIPER LOGIC:
        Strictly adhering to:
        1. Fixed 100% ROI Take Profit / MEGA_PULSE Trailing.
        2. Maximum 50% Loss Stop Loss.
        3. Trailed SL Hit Detection.
        """
        symbol = slot_data.get("symbol", "UNKNOWN")
        side = slot_data.get("side", "Buy")
        entry = slot_data.get("entry_price", 0)
        current_sl = slot_data.get("current_stop", 0)
        
        # 🛡️ 1. Universal Stop Loss Check
        side_norm = side.lower()
        if current_sl > 0:
            if (side_norm == "buy" and current_price <= current_sl) or \
               (side_norm == "sell" and current_price >= current_sl):
                logger.info(f"🛑 SNIPER SL HIT: {symbol} Price={current_price} | SL={current_sl}")
                return True, f"SNIPER_STOP_LOSS_HIT ({roi:.1f}%)", None

        # 🎯 V7.2 SNIPER TRAILING TARGET (MEGA_PULSE)
        if roi >= 100.0:
            # Trailing Profit Mode: Lock 80% and follow with 20% gap
            target_stop_roi = max(80.0, roi - 20.0) 
            
            # Convert target_stop_roi to price
            price_offset_pct = target_stop_roi / (self.leverage * 100)
            side_norm = side.lower()
            new_stop = entry * (1 + price_offset_pct) if side_norm == "buy" else entry * (1 - price_offset_pct)
            
            from services.bybit_rest import bybit_rest_service
            new_stop = await bybit_rest_service.round_price(symbol, new_stop)
            
            # Only update if it's an improvement to avoid SL regressions
            if (side_norm == "buy" and new_stop > current_sl) or (side_norm == "sell" and (current_sl == 0 or new_stop < current_sl)):
                logger.info(f"💎 SNIPER MEGA_PULSE: {symbol} ROI={roi:.1f}% | New trailing SL: {new_stop:.6f}")
                return False, None, new_stop
            
            return False, None, None # Continue trailing

        # 🛑 HARD STOP LOSS (50%)
        if roi <= -50.0:
            logger.warning(f"🛑 SNIPER HARD SL (50%): {symbol} ROI={roi:.1f}%")
            return True, f"SNIPER_SL_HARD_STOP ({roi:.1f}%)", None
        # If ROI > 50% and ATR exists, use it as a conservative floor
        if 50.0 <= roi < 100.0 and atr and atr > 0:
            atr_sl_dist = 3.0 * atr # Wider 3x ATR for SNIPER
            atr_sl = current_price - atr_sl_dist if side_norm == "buy" else current_price + atr_sl_dist
            
            # Logic: If ATR SL is better (closer to price but profitable) than the ladder SL, use it
            # But the ladder SL is primary for "locking" profits.
            pass # We'll let the ladder calculate, but we will incorporate ATR check there if needed.

        new_stop = await self._calculate_sniper_trailing_stop(symbol, entry, roi, side, current_sl)
        
        return False, None, new_stop
    
        new_stop = await self._calculate_sniper_trailing_stop(symbol, entry, roi, side, current_sl)
        
        return False, None, new_stop
    
    async def _calculate_sniper_trailing_stop(self, symbol: str, entry_price: float, roi: float, side: str, current_sl: float) -> Optional[float]:
        """
        🆕 V5.0: Calcula o novo Stop Loss para SNIPER baseado na escada adaptativa.
        
        A escada move o SL conforme o ROI aumenta:
        - ROI < 15%  → Mantém SL original (-50% ROI = entry * 0.99)
        - ROI >= 15% → SL em -30% ROI
        - ROI >= 30% → SL em -10% ROI
        - ROI >= 50% → SL em +10% ROI (lucro garantido)
        - ROI >= 70% → SL em +30% ROI (protege 30% de lucro)
        
        Returns:
            Novo preço de SL ou None se não deve atualizar
        """
        if entry_price <= 0:
            return None
        
        # Encontra o nível da escada correspondente ao ROI atual
        target_stop_roi = None
        for level in self.sniper_trailing_ladder:
            if roi >= level["trigger"]:
                target_stop_roi = level["stop_roi"]
                break
        
        if target_stop_roi is None:
            return None  # ROI < 15%, mantém SL original
        
        # Converte ROI de stop para preço
        price_offset_pct = target_stop_roi / (self.leverage * 100)
        
        side_norm = (side or "").lower()
        if side_norm == "buy":
            new_stop = entry_price * (1 + price_offset_pct)
        else:  # Sell/Short
            new_stop = entry_price * (1 - price_offset_pct)
        
        # Só retorna se for uma melhoria (SL mais alto para Long, mais baixo para Short)
        if side_norm == "buy":
            if current_sl > 0 and new_stop <= current_sl:
                return None  # Não regride
        else:
            if current_sl > 0 and new_stop >= current_sl:
                return None  # Não regride
        
        # V5.2.4: Surgical Precision Rounding
        from services.bybit_rest import bybit_rest_service
        new_stop = await bybit_rest_service.round_price(symbol, new_stop)

        return new_stop
    
    async def process_order_logic(self, slot_data: Dict[str, Any], current_price: float) -> Tuple[bool, Optional[str], Optional[float]]:
        """
        Executa a lógica exclusiva por tipo de ordem.
        
        Args:
            slot_data: Dados do slot (symbol, side, entry_price, slot_type, current_stop, etc.)
            current_price: Preço atual do mercado
            
        Returns:
            (should_close, reason, new_stop_price)
            - should_close: True se a ordem deve ser encerrada
            - reason: Motivo do encerramento
            - new_stop_price: Novo SL para atualizar (apenas SURF)
        """
        entry = slot_data.get("entry_price", 0)
        side = slot_data.get("side", "Buy")
        slot_type = slot_data.get("slot_type", "SNIPER")
        symbol = slot_data.get("symbol", "UNKNOWN")
        
        if entry <= 0 or current_price <= 0:
            return False, None, None
        
        # 1. Calcular ROI Real (Alavancagem 50x)
        roi = self.calculate_roi(entry, current_price, side)
        
        # 2. Get ATR for volatility-based decisions
        from services.bybit_ws import bybit_ws_service
        atr = bybit_ws_service.atr_cache.get(symbol)

        # 3. Executar lógica Sniper
        return await self.process_sniper_logic(slot_data, current_price, roi, atr=atr)

    def calculate_pnl(self, entry_price: float, exit_price: float, qty: float, side: str) -> float:
        """
        Calcula o PnL realizado em USD considerando taxas de corretagem (taker).
        """
        if entry_price <= 0 or qty <= 0:
            return 0.0
            
        side_norm = (side or "").lower()
        if side_norm == "buy":
            raw_pnl = qty * (exit_price - entry_price)
        else: # Sell/Short
            raw_pnl = qty * (entry_price - exit_price)
            
        # Estimativa de taxa (abertura + fechamento ~ 0.12%)
        fee = (qty * exit_price) * 0.0012
        return raw_pnl - fee


# Instância global
execution_protocol = ExecutionProtocol()
