"""
🛡️ Guardian Agent V4.5.1 - Protocol Elite
==========================================
Responsável por monitorar posições ativas e executar fechamentos.

V4.5.1 Features:
- Overclock Mode: 200ms polling quando SNIPER está em Flash Zone (80%+)
- Martelo do Guardian: Market Close forçado se TP não preencher
- Visual Status: Atualiza status visual dos slots no Firebase
- Detalhes Logs: Telemetria completa para debugging

Author: Antigravity AI
Version: 4.5.1 (Protocol Elite)
"""

import logging
import asyncio
import time
from services.bybit_rest import bybit_rest_service
from services.firebase_service import firebase_service
from services.execution_protocol import execution_protocol
from config import settings

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
logger = logging.getLogger("GuardianAgent")

class GuardianAgent:
    def __init__(self):
        self.max_latency_ms = 2000
        self.is_healthy = True
        
        # V4.5.1: Overclock State
        self.overclock_active = False
        self.normal_interval = 1.0      # 1 second normal
        self.overclock_interval = 0.2   # 200ms in Flash Zone
        
        # Logging counters
        self.loops_since_log = 0
        self.log_interval = 10  # Log status every 10 loops

    async def check_api_health(self):
        """Checks latency and connectivity to Bybit."""
        try:
            start_time = time.time()
            await asyncio.to_thread(bybit_rest_service.session.get_server_time)
            latency = (time.time() - start_time) * 1000
            
            threshold = 5000 if settings.BYBIT_TESTNET else self.max_latency_ms
            
            if latency > threshold:
                logger.warning(f"⚠️ High latency: {latency:.2f}ms")
                self.is_healthy = True
            else:
                self.is_healthy = True
            
            return self.is_healthy, latency

        except Exception as e:
            logger.error(f"🔴 Guardian API disconnection: {e}")
            self.is_healthy = False
            return False, 0

    async def manage_positions(self):
        """
        V4.5.1: Scans positions with Protocol Elite logic.
        - Updates visual_status for each slot
        - Triggers Overclock if any SNIPER is in Flash Zone
        - Executes Guardian Hammer (market close) if needed
        """
        try:
            slots = await firebase_service.get_active_slots()
            active_slots = [s for s in slots if s.get("symbol")]
            
            if not active_slots:
                self.overclock_active = False
                return

            # Batch Ticker Update
            try:
                tickers_resp = await asyncio.to_thread(bybit_rest_service.session.get_tickers, category="linear")
                ticker_list = tickers_resp.get("result", {}).get("list", [])
                price_map = {t["symbol"]: float(t.get("lastPrice", 0)) for t in ticker_list}
            except Exception as te:
                logger.error(f"Guardian batch ticker failure: {te}")
                return

            has_flash_zone = False
            
            for slot in active_slots:
                symbol = slot["symbol"]
                entry = slot.get("entry_price", 0)
                current_stop = slot.get("current_stop", 0)
                side = slot["side"]
                slot_id = slot["id"]
                slot_type = slot.get("slot_type", "SNIPER")
                
                if entry == 0: 
                    continue
                    
                # Get current price
                last_price = price_map.get(symbol, 0)
                if last_price == 0 and "." in symbol:
                    last_price = price_map.get(symbol.split('.')[0], 0)
                
                if last_price == 0: 
                    continue

                # Calculate PnL/ROI
                leverage = getattr(settings, 'LEVERAGE', 50)
                side_norm = (side or "").lower()
                pnl_pct = ((last_price - entry) / entry if side_norm == "buy" else (entry - last_price) / entry) * 100 * leverage
                
                # ==========================================
                # V4.5.1: DETAILED LOGGING
                # ==========================================
                logger.debug(f"📊 [{slot_id}] {symbol} | Side: {side_norm.upper()} | Type: {slot_type}")
                logger.debug(f"   Entry: {entry:.8f} | Current: {last_price:.8f} | Stop: {current_stop:.8f}")
                logger.debug(f"   ROI: {pnl_pct:.2f}% | Target: {execution_protocol.sniper_target_roi}%")

                # ==========================================
                # V4.5.1: VISUAL STATUS UPDATE
                # ==========================================
                slot_data = {
                    "symbol": symbol,
                    "side": side,
                    "entry_price": entry,
                    "current_stop": current_stop,
                    "slot_type": slot_type
                }
                
                visual_status = execution_protocol.get_visual_status(slot_data, pnl_pct)
                
                # Check if in Flash Zone
                if visual_status == execution_protocol.STATUS_FLASH_ZONE:
                    has_flash_zone = True
                    logger.info(f"🟣 FLASH ZONE ACTIVE: {symbol} @ {pnl_pct:.1f}% ROI | Overclock ON")

                # Update Firebase with visual status and current price
                try:
                    await firebase_service.update_slot(slot_id, {
                        "pnl_percent": pnl_pct,
                        "visual_status": visual_status,
                        "current_price": last_price,  # <-- NEW: Backend price for frontend sync
                        "last_guardian_check": time.time()
                    })
                except Exception as ue:
                    logger.warning(f"Failed to update slot {slot_id}: {ue}")

                # ==========================================
                # V4.5.1: SNIPER FLASH CLOSE LOGIC (TP & SL)
                # ==========================================
                if slot_type == "SNIPER":
                    should_close, close_reason = execution_protocol.process_sniper_logic(slot_data, last_price, pnl_pct)
                    
                    if should_close:
                        is_stop_loss = "SL" in close_reason or pnl_pct < 0
                        emoji = "🛑" if is_stop_loss else "🎯"
                        logger.info(f"{emoji} GUARDIAN SNIPER CLOSE: {symbol} | Reason: {close_reason} | ROI: {pnl_pct:.2f}%")
                        
                        # V4.5.2: Close position in BOTH PAPER and REAL modes
                        try:
                            qty = slot.get("qty", 0)
                            pnl_usd = execution_protocol.calculate_pnl(entry, last_price, qty, side)
                            
                            if bybit_rest_service.execution_mode == "PAPER":
                                # Close paper position - check existence first
                                paper_pos = next((p for p in bybit_rest_service.paper_positions if p["symbol"] == symbol or p["symbol"] == bybit_rest_service._strip_p(symbol)), None)
                                
                                # Accurate qty for PnL calculation
                                size = float(paper_pos.get("size", 0)) if paper_pos else float(slot.get("qty", 0))
                                pnl_usd = execution_protocol.calculate_pnl(entry, last_price, size, side)

                                if paper_pos:
                                    logger.info(f"🔨 [PAPER] GUARDIAN HAMMER: Closing {symbol} | Size: {size}")
                                    await bybit_rest_service.close_position(symbol, paper_pos["side"], size)
                                    # Reset slot in Firebase after closure
                                    await firebase_service.hard_reset_slot(slot_id, close_reason, pnl_usd)
                                else:
                                    logger.warning(f"⚠️ [PAPER] Position {symbol} already closed. Cleaning up stuck slot.")
                                    await firebase_service.hard_reset_slot(slot_id, close_reason, pnl_usd)
                            else:
                                # Close real position
                                positions = await bybit_rest_service.get_active_positions(symbol=symbol)
                                for pos in positions:
                                    size = float(pos.get("size", 0))
                                    if size > 0:
                                        logger.info(f"🔨 [REAL] GUARDIAN HAMMER: Closing {symbol} | Size: {size}")
                                        await bybit_rest_service.close_position(symbol, pos["side"], size)
                                        await firebase_service.hard_reset_slot(slot_id, close_reason, pnl_usd)
                        except Exception as close_err:
                            logger.error(f"❌ Failed to close position {symbol}: {close_err}")
                        continue

                # ==========================================
                # V4.5.1: SURF SHIELD LOGIC (Trailing SL)
                # ==========================================
                if slot_type == "SURF":
                    should_close, close_reason, new_stop = execution_protocol.process_surf_logic(slot_data, last_price, pnl_pct)
                    
                    if should_close:
                        is_stop_loss = "SL" in close_reason or "STOP" in close_reason or pnl_pct < 0
                        emoji = "🛑" if is_stop_loss else "🏄"
                        logger.info(f"{emoji} SURF CLOSED: {symbol} | Reason: {close_reason} | ROI: {pnl_pct:.2f}%")
                        
                        # V4.5.2: Close position in BOTH PAPER and REAL modes
                        try:
                            qty = slot.get("qty", 0)
                            pnl_usd = execution_protocol.calculate_pnl(entry, last_price, qty, side)
                            
                            if bybit_rest_service.execution_mode == "PAPER":
                                paper_pos = next((p for p in bybit_rest_service.paper_positions if p["symbol"] == symbol or p["symbol"] == bybit_rest_service._strip_p(symbol)), None)
                                
                                size = float(paper_pos.get("size", 0)) if paper_pos else float(slot.get("qty", 0))
                                pnl_usd = execution_protocol.calculate_pnl(entry, last_price, size, side)

                                if paper_pos:
                                    logger.info(f"🔨 [PAPER] SURF EXIT: Closing {symbol} | Size: {size}")
                                    await bybit_rest_service.close_position(symbol, paper_pos["side"], size)
                                    await firebase_service.hard_reset_slot(slot_id, close_reason, pnl_usd)
                                else:
                                    logger.warning(f"⚠️ [PAPER] SURF {symbol} already closed. Cleaning up stuck slot.")
                                    await firebase_service.hard_reset_slot(slot_id, close_reason, pnl_usd)
                            else:
                                positions = await bybit_rest_service.get_active_positions(symbol=symbol)
                                for pos in positions:
                                    size = float(pos.get("size", 0))
                                    if size > 0:
                                        await bybit_rest_service.close_position(symbol, pos["side"], size)
                                        await firebase_service.hard_reset_slot(slot_id, close_reason, pnl_usd)
                        except Exception as close_err:
                            logger.error(f"❌ Failed to close SURF position {symbol}: {close_err}")
                        continue
                    
                    # Update trailing stop if needed
                    if new_stop is not None:
                        logger.info(f"🏄 SURF TRAILING UPDATE: {symbol} | New SL: {new_stop:.8f}")
                        
                        try:
                            resp = await bybit_rest_service.set_trading_stop(
                                category="linear",
                                symbol=symbol,
                                stopLoss=str(new_stop),
                                slTriggerBy="LastPrice",
                                tpslMode="Full",
                                positionIdx=0
                            )
                            
                            await firebase_service.update_slot(slot_id, {
                                "current_stop": new_stop,
                                "status_risco": visual_status,
                                "pensamento": f"🛡️ Guardian: Stop atualizado para {new_stop:.5f}"
                            })
                        except Exception as se:
                            logger.error(f"Failed to update SL for {symbol}: {se}")

            # Update Overclock state
            self.overclock_active = has_flash_zone
            
            if has_flash_zone:
                logger.info(f"⚡ OVERCLOCK ENGAGED: Polling at {self.overclock_interval}s")

        except Exception as e:
            logger.error(f"Error in manage_positions: {e}", exc_info=True)

    async def monitor_loop(self):
        """
        V4.5.1: Infinite loop with adaptive interval.
        - Normal: 1 second
        - Overclock: 200ms (when SNIPER in Flash Zone)
        """
        logger.info("🛡️ Guardian V4.5.1 Protocol Elite ONLINE")
        logger.info(f"   Normal Interval: {self.normal_interval}s")
        logger.info(f"   Overclock Interval: {self.overclock_interval}s")
        
        while True:
            # 1. Health Check
            await self.check_api_health()
            
            # 2. Position Management
            await self.manage_positions()

            # 3. Adaptive Sleep
            interval = self.overclock_interval if self.overclock_active else self.normal_interval
            
            # Periodic status log
            self.loops_since_log += 1
            if self.loops_since_log >= self.log_interval:
                mode = "OVERCLOCK" if self.overclock_active else "NORMAL"
                logger.info(f"💓 Guardian Heartbeat | Mode: {mode} | Interval: {interval}s")
                self.loops_since_log = 0
            
            await asyncio.sleep(interval)

guardian_agent = GuardianAgent()
