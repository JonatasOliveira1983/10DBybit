import logging
import asyncio
from datetime import datetime, timezone
from services.firebase_service import firebase_service
from services.bankroll import bankroll_manager
from services.agents.gemini import gemini_agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CaptainAgent")

class CaptainAgent:
    def __init__(self):
        self.is_running = False

    async def monitor_signals(self):
        """
        Monitors the journey_signals table for elite signals and executes trades via BankrollManager.
        """
        self.is_running = True
        await firebase_service.log_event("Captain", "Sniper mode activated. Monitoring elite signals.", "SUCCESS")
        
        while self.is_running:
            try:
                # 1. Fetch recent signals not yet processed
                signals = await firebase_service.get_recent_signals(limit=10)
                logger.info(f"Captain scanned {len(signals)} signals.")
                await firebase_service.log_event("Captain", f"Scanning {len(signals)} potential entries...", "DEBUG")

                
                # Get current time to only process NEW signals (last 5 mins)
                now = datetime.now(timezone.utc)
                
                for signal in signals:
                    # 1.1 Refresh active slots each signal to avoid double entry
                    active_slots = await firebase_service.get_active_slots()
                    active_symbols = [s["symbol"] for s in active_slots if s.get("symbol")]

                    # Skip if already has an outcome (means it was already processed)

                    if signal.get("outcome") is not None:
                        continue

                    # Sniper Rule: Skip BTCUSDT (Only use BTC as market compass)
                    if "BTCUSDT" in signal["symbol"]:
                        logger.info(f"Skipping {signal['symbol']}: Sniper mode uses BTC only as compass.")
                        continue

                    if signal["symbol"] in active_symbols:
                        logger.info(f"Skipping {signal['symbol']}: Already in active slot.")
                        await firebase_service.log_event("Captain", f"Symbol {signal['symbol']} skipped: Already in an active slot.", "DEBUG")
                        continue

                    # Efficiency: Use fixed threshold (85) since ML is disabled
                    sniper_threshold = 85
                    if signal["score"] < sniper_threshold:
                         await firebase_service.log_event("Captain", f"Signal for {signal['symbol']} (Score: {signal['score']}) below Sniper threshold ({sniper_threshold}). Ignoring.", "DEBUG")
                         continue


                    # 3. Try to open position
                    logger.info(f"Captain executing Elite Signal: {signal['symbol']} (Score: {signal['score']})")
                    await firebase_service.log_event("Captain", f"Executing Sniping protocol for {signal['symbol']} (Score: {signal['score']})", "SUCCESS")
                    
                    # Side logic: CVD > 0 -> Buy, CVD < 0 -> Sell (simple)
                    cvd = signal.get("indicators", {}).get("cvd", 0)
                    side = "Buy" if cvd >= 0 else "Sell"
                    
                    # Execute via BankrollManager
                    await bankroll_manager.open_position(
                        symbol=signal["symbol"],
                        side=side
                    )

                await asyncio.sleep(5) # Accelerated Sniper Scan (5s)
            except Exception as e:
                logger.error(f"Error in Captain monitor loop: {e}")
                await asyncio.sleep(5)

captain_agent = CaptainAgent()
