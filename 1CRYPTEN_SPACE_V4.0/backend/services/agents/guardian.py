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
            # Wrap blocking call
            await asyncio.to_thread(bybit_rest_service.session.get_server_time)
            latency = (time.time() - start_time) * 1000
            
            if latency > self.max_latency_ms:
                logger.warning(f"High latency detected: {latency:.2f}ms. Guardian is cautious.")
                await firebase_service.log_event("Guardian", f"High latency: {latency:.2f}ms. Performance may be impacted.", "WARNING")
                self.is_healthy = False
            else:
                self.is_healthy = True
                # Pulse on success
                await firebase_service.log_event("Guardian", f"Safe Sync Active (Latency: {latency:.1f}ms)", "DEBUG")
            
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

            # Get current prices
            symbols = [s["symbol"] for s in active_slots]
            # Since we can't fetch batch tickers easily with logic here, let's do one-by-one or optimize later
            # Optimization: Fetch all linear tickers and filter? Too heavy 100+
            # Let's verify price individually for safety
            
            for slot in active_slots:
                symbol = slot["symbol"]
                entry = slot.get("entry_price", 0)
                current_stop = slot.get("current_stop", 0)
                side = slot["side"]
                
                if entry == 0: continue

                # Check if already at Breakeven (approximate)
                # Tolerance 0.1%
                is_breakeven = False
                if side == "Buy" and current_stop >= entry * 0.999: is_breakeven = True
                if side == "Sell" and current_stop <= entry * 1.001: is_breakeven = True
                
                if is_breakeven:
                    continue # Already safe

                # Fetch current price
                ticker = await asyncio.to_thread(bybit_rest_service.session.get_tickers, category="linear", symbol=symbol)
                last_price = float(ticker.get("result", {}).get("list", [{}])[0].get("lastPrice", 0))
                
                if last_price == 0: continue

                # Calculate PnL %
                if side == "Buy":
                    pnl_pct = (last_price - entry) / entry * 100
                else:
                    pnl_pct = (entry - last_price) / entry * 100
                
                # Check Trigger
                # Always update PnL in DB periodically? Too much write?
                # Let's update PnL only if significant change or simply use frontend for display.
                # User complaint: "Zero profit". Maybe just log it?
                # BETTER: Update slot PnL every check so frontend has fallback.
                if True:
                     try:
                         # Throttle updates? No, 100 docs is fine for now on small scale.
                         # Actually, let's only update if we are NOT moving stop, to populate dashboard.
                         # If moving stop, we update below.
                         await firebase_service.update_slot(slot["id"], {
                             "pnl_percent": pnl_pct
                         })
                     except: pass

                if pnl_pct >= settings.BREAKEVEN_TRIGGER_PERCENT: # 1.5%
                    logger.info(f"Guardian: {symbol} in profit ({pnl_pct:.2f}%). Moving SL to Entry ({entry}).")
                    
                    # Move SL on Exchange
                    try:
                        # Use session directly
                        resp = await asyncio.to_thread(
                            bybit_rest_service.session.set_trading_stop,
                            category="linear",
                            symbol=symbol,
                            stopLoss=str(entry), # Move to exact entry
                            slTriggerBy="LastPrice",
                            tpslMode="Full",
                            positionIdx=0 # 0 for One-Way Mode
                        )
                        
                        if resp.get("retCode") == 0:
                            # Update Firebase with PnL and new Stop
                            await firebase_service.update_slot(slot["id"], {
                                "current_stop": entry,
                                "status_risco": "RISK_FREE (GUARDIAN)",
                                "pnl_percent": pnl_pct, # Persist PnL for frontend
                                "pensamento": f"🛡️ Lucro de {pnl_pct:.2f}% atingido. Stop movido para 0-0. Risco reciclado."
                            })
                            await firebase_service.log_event("Guardian", f"🛡️ SECURED: {symbol} SL moved to Entry. Profit: {pnl_pct:.2f}%", "SUCCESS")
                        else:
                             logger.error(f"Failed to move SL for {symbol}: {resp}")

                    except Exception as e:
                        logger.error(f"Error moving SL for {symbol}: {e}")

        except Exception as e:
            logger.error(f"Error in manage_positions: {e}")

    async def monitor_loop(self):
        """Infinite loop to monitor system health and positions."""
        while True:
            # 1. Health Check
            healthy, lat = await self.check_api_health()
            if not healthy:
                logger.critical("SYSTEM UNHEALTHY - GUARDIAN MAY PAUSE TRADING")
            
            # 2. Position Management (Auto-Breakeven)
            if healthy:
                await self.manage_positions()

            await asyncio.sleep(10) # Check every 10s

guardian_agent = GuardianAgent()
