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
                if last_price == 0: continue

                # Calculate PnL %
                leverage = getattr(settings, 'LEVERAGE', 50)
                pnl_pct = ((last_price - entry) / entry if side == "Buy" else (entry - last_price) / entry) * 100 * leverage
                
                # Check if already at Breakeven
                is_breakeven = False
                if side == "Buy" and current_stop >= entry: is_breakeven = True
                if side == "Sell" and current_stop <= entry and current_stop > 0: is_breakeven = True

                # Always update PnL in Firebase for UI
                try:
                    await firebase_service.update_slot(slot["id"], {"pnl_percent": pnl_pct})
                except: pass
                
                if is_breakeven: continue

                if pnl_pct >= settings.BREAKEVEN_TRIGGER_PERCENT: # 1.5%
                    logger.info(f"Guardian: {symbol} in profit ({pnl_pct:.2f}%). Moving SL to Entry.")
                    
                    # Move SL on Exchange
                    try:
                        resp = await asyncio.to_thread(
                            bybit_rest_service.session.set_trading_stop,
                            category="linear",
                            symbol=symbol,
                            stopLoss=str(entry),
                            slTriggerBy="LastPrice",
                            tpslMode="Full",
                            positionIdx=0
                        )
                        
                        ret_code = resp.get("retCode")
                        if ret_code in [0, 34040]: # 0 = OK, 34040 = Already set
                            await firebase_service.update_slot(slot["id"], {
                                "current_stop": entry,
                                "status_risco": "RISK_FREE (GUARDIAN)",
                                "pnl_percent": pnl_pct,
                                "pensamento": f"🛡️ Lucro de {pnl_pct:.2f}% atingido. Stop movido para entrada. Risco reciclado."
                            })
                            if ret_code == 0:
                                await firebase_service.log_event("Guardian", f"🛡️ SECURED: {symbol} SL moved to Entry. Profit: {pnl_pct:.2f}%", "SUCCESS")
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
