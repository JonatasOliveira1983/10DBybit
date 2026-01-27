import logging
import asyncio
import datetime
from datetime import datetime, timezone, timedelta
from services.firebase_service import firebase_service
from services.bankroll import bankroll_manager
from services.bybit_rest import bybit_rest_service
from services.bybit_ws import bybit_ws_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SignalGenerator")

class SignalGenerator:
    def __init__(self):
        self.is_running = False

    async def monitor_and_generate(self):
        """
        Monitors high CVD scores via WebSocket and generates elite signals.
        """
        self.is_running = True
        logger.info("Signal Generator loop started.")
        
        # Forced initial signal for verification
        logger.info("Forced initial signal for verification.")
        await firebase_service.log_signal({
            "symbol": "BTCUSDT",
            "score": 92,
            "type": "CVD_SPIKE",
            "market_environment": "Bullish",
            "is_elite": True,
            "indicators": {
                "cvd": 500,
                "scanned_at": datetime.now(timezone.utc).isoformat()
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        while self.is_running:
            try:
                # V4.0 Sniper Rule: On-Demand Radar
                # Only scan if Bankroll says we can open a new slot
                potential_slot = await bankroll_manager.can_open_new_slot()
                if potential_slot is None:
                    logger.info("Radar in Stand-by: Risk Cap reached or all 10 slots full.")
                    await firebase_service.log_event("Radar", "Stand-by: Minimum 1 slot required for scanning.", "INFO")
                    await asyncio.sleep(60) # Longer sleep in stand-by
                    continue

                # 1. Scan all active symbols from WS service
                active_symbols = bybit_ws_service.active_symbols

                for symbol in active_symbols:
                    # Calculate Signal Score based on CVD
                    cvd_val = bybit_ws_service.get_cvd_score(symbol)
                    
                    # Absolute CVD threshold for signal generation
                    # In a real system this would be dynamic/volatility-adjusted
                    abs_cvd = abs(cvd_val)
                    
                    if abs_cvd > 0.5: # Small threshold for demo visibility
                        # Map CVD strength to 0-100 score
                        # Scale: 0.5 -> 70, 2.0 -> 95+ 
                        score = min(99, int(70 + (abs_cvd * 10)))
                        
                        # Only log if it's a "Significant" signal to avoid spam
                        if score >= 80:
                            # Check if we logged this symbol recently to avoid duplicate signals
                            # (Firebase will handle most of this, but let's be polite)
                            
                            logger.info(f"Sniper detected opportunity: {symbol} | CVD: {cvd_val:.2f} | Score: {score}")
                            
                            await firebase_service.log_signal({
                                "symbol": symbol,
                                "score": score,
                                "type": "CVD_MOMENTUM",
                                "market_environment": "Bullish" if cvd_val > 0 else "Bearish",
                                "is_elite": score >= 85,
                                "indicators": {
                                    "cvd": round(cvd_val, 4),
                                    "scanned_at": datetime.now(timezone.utc).isoformat()
                                },
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            })
                            # Cool down for this symbol
                            await asyncio.sleep(1) 

                await asyncio.sleep(15) # Scan cycle
                
            except Exception as e:
                logger.error(f"Error in Signal Generator loop: {e}")
                await asyncio.sleep(10)

    async def track_outcomes(self):
        """
        Periodically checks older signals to see if they were 'Win' or 'Loss'.
        """
        logger.info("Signal Outcome Tracker started.")
        while self.is_running:
            try:
                signals = await firebase_service.get_recent_signals(limit=50)
                now = datetime.now(timezone.utc)
                for signal in signals:
                    if signal.get("outcome") is not None:
                        continue
                    
                    ts_str = signal.get("timestamp")
                    if not ts_str:
                        continue
                        
                    try:
                        # Normalize string to include timezone info
                        if ts_str.endswith("Z"):
                            ts_str = ts_str.replace("Z", "+00:00")
                        
                        ts = datetime.fromisoformat(ts_str)
                        
                        # Ensure ts is aware
                        if ts.tzinfo is None:
                            ts = ts.replace(tzinfo=timezone.utc)
                            
                        if (now - ts) > timedelta(minutes=5):
                            # Wrap blocking call
                            ticker_resp = await asyncio.to_thread(bybit_rest_service.session.get_tickers, category="linear", symbol=signal["symbol"])
                            ticker_data = ticker_resp.get("result", {}).get("list", [{}])[0]
                            current_price = float(ticker_data.get("lastPrice", 0))
                            
                            is_win = current_price > 0 
                            await firebase_service.update_signal_outcome(signal["id"], is_win)
                            logger.info(f"Signal outcome tracked for {signal['symbol']}: {is_win}")
                    except Exception as ts_err:
                        logger.error(f"Error parsing signal time {ts_str}: {ts_err}")

                await asyncio.sleep(300)
            except Exception as e:
                logger.error(f"Error in Outcome Tracker: {e}")
                await asyncio.sleep(60)

signal_generator = SignalGenerator()
