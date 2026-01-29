import logging
import asyncio
import time
from services.bybit_rest import bybit_rest_service
from services.firebase_service import firebase_service
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GuardianAgent")

class GuardianAgent:
    def __init__(self):
        self.max_latency_ms = 2000 # 2000ms threshold for Testnet
        self.is_healthy = True

    async def check_api_health(self):
        """Checks latency and connectivity to Bybit."""
        try:
            start_time = time.time()
            await asyncio.to_thread(bybit_rest_service.session.get_server_time)
            latency = (time.time() - start_time) * 1000
            
            # Increase threshold for Testnet/Global environments to avoid spam
            threshold = 5000 if settings.BYBIT_TESTNET else self.max_latency_ms
            
            if latency > threshold:
                logger.warning(f"High latency: {latency:.2f}ms. Guardian is alert.")
                self.is_healthy = True # Still healthy, just slow
            else:
                self.is_healthy = True
            
            return self.is_healthy, latency

        except Exception as e:
            logger.error(f"Guardian detected API disconnection: {e}")
            self.is_healthy = False
            return False, 0

    async def manage_positions(self):
        """
        Scans active positions and moves SL to Entry (Breakeven) if profit > threshold.
        This enables 'Risk Free' status, unlocking new slots.
        """
        try:
            slots = await firebase_service.get_active_slots()
            active_slots = [s for s in slots if s.get("symbol")]
            
            if not active_slots:
                return

            # Batch Ticker Update (Saves 10 network rounds)
            try:
                tickers_resp = await asyncio.to_thread(bybit_rest_service.session.get_tickers, category="linear")
                ticker_list = tickers_resp.get("result", {}).get("list", [])
                price_map = {t["symbol"]: float(t.get("lastPrice", 0)) for t in ticker_list}
            except Exception as te:
                logger.error(f"Guardian batch ticker failure: {te}")
                return

            for slot in active_slots:
                symbol = slot["symbol"]
                entry = slot.get("entry_price", 0)
                current_stop = slot.get("current_stop", 0)
                side = slot["side"]
                
                if entry == 0: continue
                last_price = price_map.get(symbol, 0)
                if last_price == 0 and "." in symbol:
                    last_price = price_map.get(symbol.split('.')[0], 0)
                
                if last_price == 0: continue

                # Calculate PnL %
                leverage = getattr(settings, 'LEVERAGE', 50)
                side_norm = (side or "").lower()
                pnl_pct = ((last_price - entry) / entry if side_norm == "buy" else (entry - last_price) / entry) * 100 * leverage
                
                # AUDIT LOG: Identify discrepancy between Price/Entry and PNL
                if symbol == "VIRTUALUSDT" or symbol == "WLFIUSDT":
                    logger.info(f"[AUDIT] {symbol}: Side={side_norm}, Entry={entry}, Last={last_price}, ROI={pnl_pct:.2f}%")

                # Define Trailing Surf Logic (Lucro % -> Novo Stop em relação à entrada %)
                # Ex: Se lucro é 6%, move stop para +3% da entrada.
                surf_rules = [
                    {"trigger": 10.0, "stop_pct": 7.0},
                    {"trigger": 6.0,  "stop_pct": 3.0},
                    {"trigger": 3.0,  "stop_pct": 1.5},
                    {"trigger": settings.BREAKEVEN_TRIGGER_PERCENT, "stop_pct": 0.0} # Breakeven
                ]

                target_stop_pct = None
                for rule in surf_rules:
                    if pnl_pct >= rule["trigger"]:
                        target_stop_pct = rule["stop_pct"]
                        break
                
                if target_stop_pct is None: continue

                # Calculate new price for the Stop
                # For Long: Entry * (1 + target_stop_pct/100/leverage)
                # For Short: Entry * (1 - target_stop_pct/100/leverage)
                # Note: target_stop_pct is in terms of UNLEVERAGED profit to stay safe
                safe_offset = (target_stop_pct / leverage) / 100
                new_stop_price = entry * (1 + safe_offset) if side == "Buy" else entry * (1 - safe_offset)
                
                # Check if this move is actually an improvement (Trailing only)
                is_improvement = False
                side_norm = (side or "").lower()
                if side_norm == "buy" and new_stop_price > current_stop: is_improvement = True
                if side_norm == "sell" and new_stop_price < current_stop and current_stop > 0: is_improvement = True
                if side_norm == "sell" and current_stop == 0: is_improvement = True # First stop

                # Always update PnL in Firebase for UI
                try:
                    await firebase_service.update_slot(slot["id"], {"pnl_percent": pnl_pct})
                except: pass
                
                if not is_improvement: continue

                # Execution: Move SL on Exchange
                try:
                    logger.info(f"Guardian SURF: {symbol} Profit {pnl_pct:.2f}%. Moving SL to {new_stop_price:.5f} (+{target_stop_pct}% ROI).")
                    resp = await bybit_rest_service.set_trading_stop(
                        category="linear",
                        symbol=symbol,
                        stopLoss=str(new_stop_price),
                        slTriggerBy="LastPrice",
                        tpslMode="Full",
                        positionIdx=0
                    )
                    
                    ret_code = resp.get("retCode")
                    if ret_code in [0, 34040]: # 0 = OK, 34040 = Already set
                        status_msg = f"SURF_ACTIVE ({target_stop_pct}% ROI)" if target_stop_pct > 0 else "RISK_FREE (GUARDIAN)"
                        await firebase_service.update_slot(slot["id"], {
                            "current_stop": new_stop_price,
                            "status_risco": status_msg,
                            "pnl_percent": pnl_pct,
                            "pensamento": f"🏄 Surfando {symbol}: Lucro de {pnl_pct:.2f}% atingido. Stop movido para +{target_stop_pct:.1f}% ROI."
                        })
                        if ret_code == 0:
                            await firebase_service.log_event("Guardian", f"🏄 SURF: {symbol} SL moved to {new_stop_price:.5f}. Profit: {pnl_pct:.2f}%", "SUCCESS")
                    else:
                         logger.error(f"Failed to move SL for {symbol}: {resp}")

                except Exception as e:
                    if "34040" not in str(e):
                        logger.error(f"Error moving SL for {symbol}: {e}")

        except Exception as e:
            logger.error(f"Error in manage_positions: {e}")

    async def monitor_loop(self):
        """Infinite loop to monitor system health and positions."""
        while True:
            # 1. Health Check
            await self.check_api_health()
            
            # 2. Position Management (Auto-Breakeven)
            await self.manage_positions()

            await asyncio.sleep(15) # Check every 15s

guardian_agent = GuardianAgent()
