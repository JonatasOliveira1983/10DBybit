"""
🛡️ Protocolo de Execução Elite V4.5.1
=========================================
Módulo responsável por executar lógica de fechamento independente por slot.
Implementa Flash Close (SNIPER) e Surf Shield (SURF) com telemetria visual.

Author: Antigravity AI
Version: 4.5.1 (Protocol Elite)
"""

import logging
import time
from typing import Tuple, Optional, Dict, Any

logger = logging.getLogger("ExecutionProtocol")

class ExecutionProtocol:
    """
    Executa a lógica de fechamento para cada slot de forma independente.
    Cada ordem tem seu próprio 'contrato de execução'.
    
    V4.5.1 Protocol Elite:
    - SNIPER: Flash Close com TP nativo + Guardian Overclock
    - SURF: Surf Shield com Risco Zero automático
    """
    
    def __init__(self):
        self.leverage = 50
        
        # === SNIPER CONFIG (Slots 1-5) ===
        self.sniper_target_roi = 100.0    # 100% ROI = 2% movimento @ 50x
        self.sniper_stop_roi = -50.0      # Stop Loss = -50% ROI (1% movimento)
        self.flash_zone_threshold = 80.0  # Zona Roxa: 80% do target (ROI >= 80%)
        
        # === SURF CONFIG (Slots 6-10) ===
        self.risk_zero_threshold = 50.0   # Risco Zero ativa em 50% ROI (1% movimento)
        self.big_surf_threshold = 150.0   # Big Surf: ROI > 150%
        
        # Escada de Proteção SURF (ROI% -> SL em ROI%)
        self.surf_trailing_ladder = [
            {"trigger": 150.0, "stop_roi": 120.0},  # Big Surf: protege 120%
            {"trigger": 100.0, "stop_roi": 80.0},   # ROI 100% -> SL em +80%
            {"trigger": 50.0,  "stop_roi": 30.0},   # Risco Zero: 50% -> SL em +30%
            {"trigger": 25.0,  "stop_roi": 10.0},   # ROI 25% -> SL em +10%
            {"trigger": 10.0,  "stop_roi": 5.0},    # ROI 10% -> SL em +5%
            {"trigger": 5.0,   "stop_roi": 0.0},    # ROI 5%  -> SL em Breakeven (0%)
        ]
        
        # === VISUAL STATUS CODES ===
        # Usados pelo frontend para cores dos slots
        self.STATUS_SCANNING = "SCANNING"       # Azul - slot livre
        self.STATUS_IN_TRADE = "IN_TRADE"       # Dourado - posição aberta
        self.STATUS_RISK_ZERO = "RISK_ZERO"     # Turquesa - stop na entrada
        self.STATUS_BIG_SURF = "BIG_SURF"       # Verde Esmeralda - ROI > 150%
        self.STATUS_FLASH_ZONE = "FLASH_ZONE"   # Roxo Neon - alvo iminente
        
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
        
        # SNIPER: Flash Zone (80%+ do target)
        if slot_type == "SNIPER":
            if roi >= self.flash_zone_threshold:
                logger.info(f"🟣 FLASH ZONE: {symbol} ROI={roi:.1f}% >= {self.flash_zone_threshold}%")
                return self.STATUS_FLASH_ZONE
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
    
    def process_sniper_logic(self, slot_data: Dict[str, Any], current_price: float, roi: float) -> Tuple[bool, Optional[str]]:
        """
        Lógica exclusiva para ordens SNIPER.
        
        SNIPER = Alvo fixo de 100% ROI (2% movimento de preço @ 50x)
        Stop Loss = -50% ROI (1% movimento de preço)
        
        Returns:
            (should_close, reason) - True se deve fechar a posição
        """
        symbol = slot_data.get("symbol", "UNKNOWN")
        
        # ✅ TAKE PROFIT: ROI >= 100%
        if roi >= self.sniper_target_roi:
            logger.info(f"🎯 SNIPER TP HIT: {symbol} ROI={roi:.2f}% >= {self.sniper_target_roi}% | Price={current_price}")
            return True, f"SNIPER_TP_100_ROI ({roi:.1f}%)"
        
        # ❌ STOP LOSS: ROI <= -50%
        if roi <= self.sniper_stop_roi:
            logger.warning(f"🛑 SNIPER SL HIT: {symbol} ROI={roi:.2f}% <= {self.sniper_stop_roi}%")
            return True, f"SNIPER_SL_HARD_STOP ({roi:.1f}%)"
        
        return False, None
    
    def process_surf_logic(self, slot_data: Dict[str, Any], current_price: float, roi: float) -> Tuple[bool, Optional[str], Optional[float]]:
        """
        Lógica exclusiva para ordens SURF (Trailing Stop).
        
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
        
        # Calcular novo SL baseado na escada de proteção
        new_stop_price = self._calculate_surf_trailing_stop(entry, roi, side)
        
        # Só retorna novo SL se for uma melhoria
        if new_stop_price is not None:
            is_improvement = False
            if side_norm == "buy" and new_stop_price > current_sl:
                is_improvement = True
            elif side_norm == "sell" and (current_sl == 0 or new_stop_price < current_sl):
                is_improvement = True
                
            if is_improvement:
                logger.info(f"🏄 SURF TRAILING UPDATE: {symbol} ROI={roi:.1f}% -> New SL={new_stop_price:.5f}")
                return False, None, new_stop_price
        
        return False, None, None
    
    def _calculate_surf_trailing_stop(self, entry_price: float, roi: float, side: str) -> Optional[float]:
        """
        Calcula o novo Stop Loss baseado na escada de proteção.
        
        Returns:
            Novo preço de SL ou None se não atingiu nenhum gatilho
        """
        if entry_price <= 0:
            return None
            
        # Encontra o nível da escada correspondente ao ROI atual
        target_stop_roi = None
        for level in self.surf_trailing_ladder:
            if roi >= level["trigger"]:
                target_stop_roi = level["stop_roi"]
                break
        
        if target_stop_roi is None:
            return None
        
        # Converte ROI de stop para preço
        # stop_roi é em termos de ROI alavancado, então precisamos converter para movimento de preço
        # ROI = price_diff * leverage * 100
        # price_diff = stop_roi / (leverage * 100)
        price_offset_pct = target_stop_roi / (self.leverage * 100)
        
        side_norm = (side or "").lower()
        if side_norm == "buy":
            new_stop = entry_price * (1 + price_offset_pct)
        else:  # Sell/Short
            new_stop = entry_price * (1 - price_offset_pct)
        
        return new_stop
    
    def process_order_logic(self, slot_data: Dict[str, Any], current_price: float) -> Tuple[bool, Optional[str], Optional[float]]:
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
        
        # 2. Executar lógica específica do tipo
        if slot_type == "SNIPER":
            should_close, reason = self.process_sniper_logic(slot_data, current_price, roi)
            return should_close, reason, None
            
        elif slot_type == "SURF":
            return self.process_surf_logic(slot_data, current_price, roi)
        
        # Tipo desconhecido - usa lógica SNIPER por padrão
        logger.warning(f"Unknown slot_type '{slot_type}' for {symbol}, using SNIPER logic")
        should_close, reason = self.process_sniper_logic(slot_data, current_price, roi)
        return should_close, reason, None


# Instância global
execution_protocol = ExecutionProtocol()
