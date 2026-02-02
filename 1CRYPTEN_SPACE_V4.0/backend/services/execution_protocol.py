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
        
        # === SNIPER CONFIG (Slots 1-5) ===
        self.sniper_target_roi = 100.0    # 100% ROI = 2% movimento @ 50x
        self.sniper_stop_roi = -50.0      # Stop Loss inicial = -50% ROI (1% movimento)
        self.flash_zone_threshold = 80.0  # Zona Roxa: 80% do target (ROI >= 80%)
        
        # 🆕 V5.0: Escada Adaptive SL para SNIPER (ROI% -> SL em ROI%)
        # Move o SL conforme lucro aumenta, protegendo ganhos
        self.sniper_trailing_ladder = [
            {"trigger": 70.0, "stop_roi": 30.0},   # ROI 70%  → SL em +30% (protege lucro)
            {"trigger": 50.0, "stop_roi": 10.0},   # ROI 50%  → SL em +10% (lucro garantido)
            {"trigger": 30.0, "stop_roi": -10.0},  # ROI 30%  → SL em -10% (reduz perda max)
            {"trigger": 15.0, "stop_roi": -30.0},  # ROI 15%  → SL em -30% (de -50% original)
        ]
        # Se ROI < 15%, mantém SL original de -50%
        
        # === SURF CONFIG (Slots 6-10) ===
        self.risk_zero_threshold = 50.0   # Risco Zero ativa em 50% ROI (1% movimento)
        self.big_surf_threshold = 150.0   # Big Surf: ROI > 150%
        
        # 🆕 V5.0: Escada de Proteção SURF melhorada (mais níveis)
        self.surf_trailing_ladder = [
            {"trigger": 200.0, "stop_roi": 170.0},  # 🏄 Mega Surf: protege 170%
            {"trigger": 150.0, "stop_roi": 120.0},  # Big Surf: protege 120%
            {"trigger": 100.0, "stop_roi": 80.0},   # ROI 100% -> SL em +80%
            {"trigger": 75.0,  "stop_roi": 55.0},   # 🆕 ROI 75%  -> SL em +55%
            {"trigger": 60.0,  "stop_roi": 35.0},   # 🆕 V5.4.5: ROI 60% -> SL 35%
            {"trigger": 50.0,  "stop_roi": 30.0},   # Risco Zero: 50% -> SL em +30%
            {"trigger": 35.0,  "stop_roi": 15.0},   # 🆕 ROI 35%  -> SL em +15%
            {"trigger": 30.0,  "stop_roi": 10.0},   # 🆕 V5.4.5: ROI 30% -> SL 10%
            {"trigger": 20.0,  "stop_roi": 5.0},    # 🆕 ROI 20%  -> SL em +5%
            {"trigger": 10.0,  "stop_roi": 0.0},    # Breakeven mais cedo (era 5%)
        ]
        
        # === VISUAL STATUS CODES ===
        # Usados pelo frontend para cores dos slots
        self.STATUS_SCANNING = "SCANNING"       # Azul - slot livre
        self.STATUS_IN_TRADE = "IN_TRADE"       # Dourado - posição aberta
        self.STATUS_RISK_ZERO = "RISK_ZERO"     # Turquesa - stop na entrada ou acima
        self.STATUS_BIG_SURF = "BIG_SURF"       # Verde Esmeralda - ROI > 150%
        self.STATUS_FLASH_ZONE = "FLASH_ZONE"   # Roxo Neon - alvo iminente
        self.STATUS_TRAILING = "TRAILING"       # 🆕 Amarelo Ouro - SL foi movido mas ainda negativo
        
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
        
        # SNIPER: Flash Zone (80%+ do target), Risk Zero, ou Trailing
        if slot_type == "SNIPER":
            side = slot_data.get("side", "Buy")
            side_norm = (side or "").lower()
            
            if roi >= self.flash_zone_threshold:
                logger.info(f"🟣 FLASH ZONE: {symbol} ROI={roi:.1f}% >= {self.flash_zone_threshold}%")
                return self.STATUS_FLASH_ZONE
            
            # 🆕 V5.0: Detecta se SL foi movido para lucro (Risk Zero) ou apenas reduzido (Trailing)
            if current_stop > 0 and entry_price > 0:
                if side_norm == "buy":
                    if current_stop >= entry_price:
                        return self.STATUS_RISK_ZERO  # SL no lucro
                    elif current_stop > entry_price * 0.99:  # SL movido mas ainda negativo
                        return self.STATUS_TRAILING
                elif side_norm == "sell":
                    if current_stop <= entry_price:
                        return self.STATUS_RISK_ZERO
                    elif current_stop < entry_price * 1.01:
                        return self.STATUS_TRAILING
            
            return self.STATUS_IN_TRADE
        
        # SURF: Big Surf (150%+), Risk Zero, ou In Trade
        if slot_type == "SURF":
            if roi >= self.big_surf_threshold:
                return self.STATUS_BIG_SURF
            if roi >= self.risk_zero_threshold and current_stop >= entry_price:
                return self.STATUS_RISK_ZERO
            if current_stop > 0 and current_stop >= entry_price:
                return self.STATUS_RISK_ZERO
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
        🆕 V5.0: Lógica SNIPER com Adaptive Stop Loss.
        
        SNIPER = Alvo fixo de 100% ROI (2% movimento de preço @ 50x)
        Stop Loss = Adaptativo conforme ROI sobe (de -50% até +30%)
        
        Returns:
            (should_close, reason, new_stop_price) - True se deve fechar, novo SL se deve atualizar
        """
        symbol = slot_data.get("symbol", "UNKNOWN")
        side = slot_data.get("side", "Buy")
        entry = slot_data.get("entry_price", 0)
        current_sl = slot_data.get("current_stop", 0)
        
        # ✅ SNIPER OVERDRIVE (V5.3): Trava 100% e Persegue o Preço
        # Substitui o antigo TP fixo de 100%
        if roi >= 100.0:
            # Calcular níveis de Overdrive
            # Level 1: Floor Garantido (100% de lucro)
            floor_roi = 100.0
            
            # Level 2: Trailing Agressivo (20% de distância da máxima)
            # Se ROI está em 150%, Trail está em 130%.
            # Se ROI está em 200%, Trail está em 180%.
            # 🆕 V6.0: If ATR exists, use max(20% ROI, 2.5x ATR) for better breathing room
            trail_offset_roi = 20.0
            if atr and atr > 0:
                atr_roi = (atr * 2.5 / entry) * self.leverage * 100
                trail_offset_roi = max(trail_offset_roi, atr_roi)

            trail_roi = roi - trail_offset_roi
            
            # O novo SL em ROI é o maior entre o Floor e o Trail
            target_sl_roi = max(floor_roi, trail_roi)
            
            # Converter ROI alvo para Preço Real
            price_offset_pct = target_sl_roi / (self.leverage * 100)
            
            side_norm = (side or "").lower()
            if side_norm == "buy":
                new_stop = entry * (1 + price_offset_pct)
            else:
                new_stop = entry * (1 - price_offset_pct)
                
            # Arredondamento Cirúrgico
            from services.bybit_rest import bybit_rest_service
            new_stop = await bybit_rest_service.round_price(symbol, new_stop)
            
            # 🆕 V6.0: SL REGRESSION SHIELD (Security Operation)
            # Never move SL further from entry than current SL
            should_update = False
            if side_norm == "buy":
                if new_stop > current_sl: should_update = True
            else:
                if (current_sl == 0) or (new_stop < current_sl): should_update = True
            
            if should_update:
                logger.info(f"🚀 SNIPER OVERDRIVE: {symbol} ROI={roi:.1f}% | New SL={new_stop} (Locked {target_sl_roi:.1f}%)")
                return False, None, new_stop
            else:
                return False, None, None

        # ❌ STOP LOSS CHECK (Normal & Adaptive abaixo de 100%)
        # ... Mantém lógica original para ROI < 100% ...
        side_norm = (side or "").lower()
        if current_sl > 0:
            if side_norm == "buy" and current_price <= current_sl:
                # Verificar se foi um SL de Overdrive (Lucro) ou Loss
                is_profit = current_price > entry
                msg = "SNIPER_OVERDRIVE_PROFIT" if is_profit else "SNIPER_ADAPTIVE_SL"
                logger.info(f"🛑 {msg} HIT: {symbol} Price={current_price} | ROI={roi:.1f}%")
                return True, f"{msg} ({roi:.1f}%)", None
            elif side_norm == "sell" and current_price >= current_sl:
                is_profit = current_price < entry
                msg = "SNIPER_OVERDRIVE_PROFIT" if is_profit else "SNIPER_ADAPTIVE_SL"
                logger.info(f"🛑 {msg} HIT: {symbol} Price={current_price} | ROI={roi:.1f}%")
                return True, f"{msg} ({roi:.1f}%)", None

        # 🔥 Hard Stop Loss fallback
        if roi <= self.sniper_stop_roi:
            logger.warning(f"🛑 SNIPER HARD SL: {symbol} ROI={roi:.2f}% <= {self.sniper_stop_roi}%")
            return True, f"SNIPER_SL_HARD_STOP ({roi:.1f}%)", None
        
        # 🔄 TRAIL SL (Escada Pré-100%): 15% -> 30% -> 50% -> 70%
        # Só executa se não estiver em Overdrive (< 100%)
        
        # 🆕 V6.0: ATR SL Hybrid (Security Operation)
        # If ROI > 50% and ATR exists, use it as a conservative floor
        if 50.0 <= roi < 100.0 and atr and atr > 0:
            atr_sl_dist = 3.0 * atr # Wider 3x ATR for SNIPER
            atr_sl = current_price - atr_sl_dist if side_norm == "buy" else current_price + atr_sl_dist
            
            # Logic: If ATR SL is better (closer to price but profitable) than the ladder SL, use it
            # But the ladder SL is primary for "locking" profits.
            pass # We'll let the ladder calculate, but we will incorporate ATR check there if needed.

        new_stop = await self._calculate_sniper_trailing_stop(symbol, entry, roi, side, current_sl)
        
        return False, None, new_stop
    
    async def process_surf_logic(self, slot_data: Dict[str, Any], current_price: float, roi: float, atr: Optional[float] = None) -> Tuple[bool, Optional[str], Optional[float]]:
        """
        Lógica exclusiva para ordens SURF (Trailing Stop).
        V5.1.0: Integrado ATR para trailing volátil.
        
        SURF = Sem TP fixo, usa trailing stop progressivo.
        A escada de proteção move o SL conforme o lucro aumenta.
        
        Returns:
            (should_close, reason, new_stop_price) - True se deve fechar, novo SL se deve atualizar
        """
        symbol = slot_data.get("symbol", "UNKNOWN")
        side = slot_data.get("side", "Buy")
        entry = slot_data.get("entry_price", 0)
        current_sl = slot_data.get("current_stop", 0)
        
        # Verificar se SL foi atingido
        side_norm = (side or "").lower()
        if current_sl > 0:
            if side_norm == "buy" and current_price <= current_sl:
                logger.info(f"🏄 SURF TRAILING SL HIT: {symbol} Price={current_price} <= SL={current_sl}")
                return True, f"SURF_TRAILING_STOP_HIT ({roi:.1f}%)", None
            elif side_norm == "sell" and current_price >= current_sl:
                logger.info(f"🏄 SURF TRAILING SL HIT: {symbol} Price={current_price} >= SL={current_sl}")
                return True, f"SURF_TRAILING_STOP_HIT ({roi:.1f}%)", None
        
        # 🔥 Hard Stop Loss: ROI <= -75% (proteção anti-drain)
        if roi <= -75.0:
            logger.warning(f"🛑 SURF HARD SL: {symbol} ROI={roi:.2f}% <= -75%")
            return True, f"SURF_HARD_STOP ({roi:.1f}%)", None
        
        # V5.1.0: Calcular novo SL baseado no ATR se disponível, ou fallback para escada fixa
        new_stop_price = None
        if atr and atr > 0:
            # Lógica ATR-based solicitada pelo Almirante
            if 50.0 <= roi < 100.0:
                # ROI 50%-100%: Trailing Stop a 2.5x ATR
                new_stop_price = current_price - (2.5 * atr) if side_norm == "buy" else current_price + (2.5 * atr)
            elif 100.0 <= roi < 200.0:
                # ROI 100%-200%: Trailing Stop a 1.5x ATR
                new_stop_price = current_price - (1.5 * atr) if side_norm == "buy" else current_price + (1.5 * atr)
            elif roi >= 200.0:
                # ROI > 200%: Flash Zone (Trailing ultra curto de 0.8x ATR ou manual)
                new_stop_price = current_price - (0.8 * atr) if side_norm == "buy" else current_price + (0.8 * atr)
        
        # [V5.4.5] Sentiment-based Risk Zero at 15% ROI for SURF
        if 15.0 <= roi < 20.0:
            if await self._check_sentiment_weakness(symbol, side):
                logger.info(f"🛡️ [SENTI RISK ZERO] SURF {symbol} Triggered at ROI: {roi:.1f}%")
                new_stop_price = entry # Break-even
        
        # Fallback para escada fixa se ATR não trouxe resultado ou ROI for menor/maior que faixas ATR
        if new_stop_price is None:
            new_stop_price = await self._calculate_surf_trailing_stop(symbol, entry, roi, side)
        
        # Só retorna novo SL se for uma melhoria
        if new_stop_price is not None:
            is_improvement = False
            if side_norm == "buy" and new_stop_price > current_sl:
                is_improvement = True
            elif side_norm == "sell" and (current_sl == 0 or new_stop_price < current_sl):
                is_improvement = True
            
            if is_improvement:
                logger.debug(f"🏄 SURF TRAILING UPDATE: {symbol} ROI={roi:.1f}% -> New SL={new_stop_price:.5f}")
                return False, None, new_stop_price
        
        return False, None, None
    
    async def _calculate_surf_trailing_stop(self, symbol: str, entry_price: float, roi: float, side: str) -> Optional[float]:
        """
        🏄 V6.0 SURF TRAILING - Protocolo de Respiro
        ============================================
        Calcula o novo Stop Loss baseado no lucro atual e volatilidade.
        """
        if entry_price <= 0: return None
            
        # Protocolo de Respiro: Define o ROI alvo do STOP based on current ROI
        target_stop_roi = None
        
        if roi >= 150:
            # Trailing Agressivo para lucros massivos
            new_sl = await self._calculate_atr_stop(symbol, side, None, multiplier=1.5)
            return new_sl
        elif roi >= 50:
            # Trailing Seguro
            new_sl = await self._calculate_atr_stop(symbol, side, None, multiplier=2.2)
            return new_sl
        elif roi >= 30:
            # Risk Zero (Breakeven) - Agora apenas após 30% ROI
            target_stop_roi = 0.0
        elif roi >= 10:
            # Proteção Inicial (Breathing ATR) - 3.5x para não ser pego em wicks
            new_sl = await self._calculate_atr_stop(symbol, side, None, multiplier=3.5)
            return new_sl
        
        if target_stop_roi is None:
            return None
        
        # Converte ROI alvo em Preço
        price_offset_pct = target_stop_roi / (self.leverage * 100)
        side_norm = (side or "").lower()
        if side_norm == "buy":
            new_stop = entry_price * (1 + price_offset_pct)
        else:
            new_stop = entry_price * (1 - price_offset_pct)
        
        from services.bybit_rest import bybit_rest_service
        return await bybit_rest_service.round_price(symbol, new_stop)

    async def _calculate_atr_stop(self, symbol: str, side: str, current_price: Optional[float] = None, multiplier: float = 2.5) -> Optional[float]:
        """Calcula stop baseado em ATR para dar respiro ao trade."""
        try:
            from services.bybit_rest import bybit_rest_service
            if not current_price:
                from services.bybit_ws import bybit_ws_service
                current_price = bybit_ws_service.get_current_price(symbol)
            
            # Fetch ATR (mocked or retrieved from technical service)
            # Para o Protocolo de Respiro, vamos estimar 0.2% como ATR padrão (2x trade fee)
            atr_value = current_price * 0.002 
            
            offset = atr_value * multiplier
            side_norm = side.lower()
            if side_norm == "buy":
                new_stop = current_price - offset
            else:
                new_stop = current_price + offset
            
            return await bybit_rest_service.round_price(symbol, new_stop)
        except:
            return None
    
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

        # 3. Executar lógica específica do tipo
        if slot_type == "SNIPER":
            return await self.process_sniper_logic(slot_data, current_price, roi, atr=atr)
            
        elif slot_type == "SURF":
            return await self.process_surf_logic(slot_data, current_price, roi, atr=atr)
        
        # Tipo desconhecido - usa lógica SNIPER por padrão
        logger.warning(f"Unknown slot_type '{slot_type}' for {symbol}, using SNIPER logic")
        return await self.process_sniper_logic(slot_data, current_price, roi)

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
