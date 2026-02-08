"""
🛡️ Protocolo de Execução Elite V11.0 - Smart Stop Loss Protocol
==========================================================
Módulo responsável por executar lógica de fechamento independente por slot.
Implementa Smart SL com 4 fases: SAFE → RISK_ZERO → PROFIT_LOCK → MEGA_PULSE.

Author: Antigravity AI
Version: 11.0 (Smart Stop Loss Protocol)

V11.0 Changes:
- PHASE_SAFE: SL inicial em -50% ROI (entrada)
- PHASE_RISK_ZERO: SL move para entry quando ROI >= 30%
- PHASE_PROFIT_LOCK: SL trava 80% do lucro quando ROI >= 100%
- PHASE_MEGA_PULSE: Trailing dinâmico baseado em Gás (CVD) para ROI >= 100%
"""

import logging
import time
from typing import Tuple, Optional, Dict, Any

logger = logging.getLogger("ExecutionProtocol")

# V11.0 Smart SL Protocol Phases
SMART_SL_PHASES = {
    "PHASE_SAFE": {"trigger_roi": 0, "stop_roi": -50.0, "icon": "🔴", "color": "red"},
    "PHASE_RISK_ZERO": {"trigger_roi": 30.0, "stop_roi": 0.0, "icon": "🛡️", "color": "green"},
    "PHASE_PROFIT_LOCK": {"trigger_roi": 100.0, "stop_roi": 80.0, "icon": "🟡", "color": "gold"},
    "PHASE_MEGA_PULSE": {"trigger_roi": 100.0, "trailing_gap": 20.0, "icon": "💎", "color": "diamond"}
}

class ExecutionProtocol:
    """
    Executa a lógica de fechamento para cada slot de forma independente.
    Cada ordem tem seu próprio 'contrato de execução'.
    
    V11.0 Smart Stop Loss Protocol:
    - PHASE_SAFE: SL em -50% ROI (proteção inicial)
    - PHASE_RISK_ZERO: SL em entry quando ROI >= 30%
    - PHASE_PROFIT_LOCK: SL trava 80% do lucro quando ROI >= 100%
    - PHASE_MEGA_PULSE: Trailing com gap de 20% ROI + verificação de Gás
    """
    
    def __init__(self):
        self.leverage = 50
        
        # === SNIPER CONFIG (Slot 1 & 2) ===
        self.sniper_target_roi = 100.0    # 100% ROI = 2% movimento @ 50x
        self.sniper_stop_roi = -50.0      # Stop Loss inicial = -50% ROI (1% movimento)
        self.flash_zone_threshold = 80.0  # Zona Roxa: 80% do target (ROI >= 80%)
        
        # V11.0: Smart SL Phase Thresholds
        self.phase_risk_zero_trigger = 30.0   # ROI para mover SL para entry
        self.phase_profit_lock_trigger = 100.0 # ROI para travar 80% do lucro
        self.mega_pulse_trailing_gap = 20.0    # Gap de ROI para trailing
        
        # === VISUAL STATUS CODES ===
        self.STATUS_SCANNING = "SCANNING"       # Azul - slot livre
        self.STATUS_IN_TRADE = "IN_TRADE"       # Dourado - posição aberta
        self.STATUS_RISK_ZERO = "RISK_ZERO"     # Verde - stop na entrada ou acima
        self.STATUS_FLASH_ZONE = "FLASH_ZONE"   # Roxo Neon - alvo iminente
        self.STATUS_TRAILING = "TRAILING"       # Amarelo Ouro - SL foi movido
        self.STATUS_MEGA_PULSE = "MEGA_PULSE"   # 💎 V11.0: Trailing Profit (ROI > 100%)
        self.STATUS_PROFIT_LOCK = "PROFIT_LOCK" # 🟡 V11.0: Lucro travado em 80%
        
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
        [V11.0] SMART STOP-LOSS PROTOCOL:
        4 fases de proteção inteligente baseado em ROI e Gás (CVD).
        
        PHASE_SAFE:       ROI < 30%  → SL em -50% ROI (entrada)
        PHASE_RISK_ZERO:  ROI >= 30% → SL move para entry (0% ROI)
        PHASE_PROFIT_LOCK: ROI >= 100% → SL trava em 80% do lucro
        PHASE_MEGA_PULSE: ROI >= 100% + Gás favorável → Trailing dinâmico
        """
        symbol = slot_data.get("symbol", "UNKNOWN")
        side = slot_data.get("side", "Buy")
        entry = slot_data.get("entry_price", 0)
        current_sl = slot_data.get("current_stop", 0)
        side_norm = side.lower()
        
        # 🛡️ 1. Universal Stop Loss Check
        if current_sl > 0:
            if (side_norm == "buy" and current_price <= current_sl) or \
               (side_norm == "sell" and current_price >= current_sl):
                phase = self.get_sl_phase(roi)
                logger.info(f"🛑 SNIPER SL HIT: {symbol} Price={current_price} | SL={current_sl} | Phase={phase}")
                return True, f"SNIPER_SL_{phase} ({roi:.1f}%)", None

        # 🛑 HARD STOP LOSS (-50% ROI)
        if roi <= -50.0:
            logger.warning(f"🛑 SNIPER HARD SL: {symbol} ROI={roi:.1f}%")
            return True, f"SNIPER_SL_HARD_STOP ({roi:.1f}%)", None
        
        # V11.0: Determinar fase atual do Smart SL
        phase = self.get_sl_phase(roi)
        
        # 🌟 PHASE_MEGA_PULSE: Trailing dinâmico com verificação de Gás
        if roi >= self.phase_profit_lock_trigger:
            gas_favorable = await self._check_gas_favorable(symbol, side)
            
            if gas_favorable:
                # Trailing Profit Mode: SL segue com gap de 20% ROI
                target_stop_roi = max(80.0, roi - self.mega_pulse_trailing_gap)
                phase_label = "MEGA_PULSE"
            else:
                # Gás desfavorável: Travar em 80% do lucro (PROFIT_LOCK)
                target_stop_roi = 80.0
                phase_label = "PROFIT_LOCK"
            
            price_offset_pct = target_stop_roi / (self.leverage * 100)
            new_stop = entry * (1 + price_offset_pct) if side_norm == "buy" else entry * (1 - price_offset_pct)
            
            from services.bybit_rest import bybit_rest_service
            new_stop = await bybit_rest_service.round_price(symbol, new_stop)
            
            # Só atualiza se for melhoria
            if (side_norm == "buy" and new_stop > current_sl) or (side_norm == "sell" and (current_sl == 0 or new_stop < current_sl)):
                logger.info(f"💎 SNIPER {phase_label}: {symbol} ROI={roi:.1f}% | Gás={'OK' if gas_favorable else 'CONTRA'} | SL: {new_stop:.6f}")
                return False, None, new_stop
            
            return False, None, None

        # 🛡️ PHASE_RISK_ZERO: Mover SL para entry quando ROI >= 30%
        if roi >= self.phase_risk_zero_trigger:
            target_stop_roi = 0.0  # SL na entrada (Risk Zero)
            
            price_offset_pct = target_stop_roi / (self.leverage * 100)  # = 0
            new_stop = entry * (1 + price_offset_pct) if side_norm == "buy" else entry * (1 - price_offset_pct)
            
            from services.bybit_rest import bybit_rest_service
            new_stop = await bybit_rest_service.round_price(symbol, new_stop)
            
            # Só atualiza se SL ainda não está na entry ou melhor
            if side_norm == "buy":
                if current_sl < new_stop:
                    logger.info(f"🛡️ SNIPER RISK_ZERO: {symbol} ROI={roi:.1f}% | SL → Entry: {new_stop:.6f}")
                    return False, None, new_stop
            else:
                if current_sl == 0 or current_sl > new_stop:
                    logger.info(f"🛡️ SNIPER RISK_ZERO: {symbol} ROI={roi:.1f}% | SL → Entry: {new_stop:.6f}")
                    return False, None, new_stop
        
        # 🔴 PHASE_SAFE: Manter SL inicial (-50% ROI)
        # Nenhuma ação necessária, SL já foi definido na abertura
        
        return False, None, None
    
    def get_sl_phase(self, roi: float) -> str:
        """
        V11.0: Retorna a fase atual do Smart SL baseado no ROI.
        """
        if roi >= 100.0:
            return "MEGA_PULSE"
        elif roi >= 30.0:
            return "RISK_ZERO"
        else:
            return "SAFE"
    
    def get_sl_phase_info(self, roi: float) -> Dict[str, Any]:
        """
        V11.0: Retorna informações completas da fase atual para o frontend.
        """
        phase = self.get_sl_phase(roi)
        phase_key = f"PHASE_{phase}"
        info = SMART_SL_PHASES.get(phase_key, SMART_SL_PHASES["PHASE_SAFE"])
        return {
            "phase": phase,
            "icon": info.get("icon", "🔴"),
            "color": info.get("color", "red"),
            "stop_roi": info.get("stop_roi", -50.0)
        }
    
    async def _check_gas_favorable(self, symbol: str, side: str) -> bool:
        """
        V11.0: Verifica se o Gás (CVD/momentum) é favorável para trailing.
        Returns True se o CVD está a favor da posição.
        """
        try:
            from services.redis_service import redis_service
            cvd = await redis_service.get_cvd(symbol)
            side_norm = side.lower()
            
            # Gás favorável: CVD positivo para Long, negativo para Short
            if side_norm == "buy":
                favorable = cvd > 5000  # CVD positivo forte
            else:
                favorable = cvd < -5000  # CVD negativo forte
            
            logger.debug(f"🏎️ GAS CHECK: {symbol} | Side={side} | CVD={cvd:.2f} | Favorable={favorable}")
            return favorable
        except Exception as e:
            logger.warning(f"Gas check failed: {e}")
            return False  # Default: conservador (trava lucro)
    
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
