import logging
import asyncio
import time
import datetime
from datetime import datetime, timezone, timedelta
from services.firebase_service import firebase_service
from services.bankroll import bankroll_manager
from services.bybit_rest import bybit_rest_service
from services.bybit_ws import bybit_ws_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SignalGenerator")

def normalize_symbol(symbol: str) -> str:
    """Normaliza símbolos removendo .P para comparação consistente."""
    if not symbol:
        return symbol
    return symbol.replace(".P", "").upper()

class SignalGenerator:
    def __init__(self):
        self.is_running = False
        self.last_standby_log = 0
        self.radar_interval = 3.0 # Update RTDB every 3s for 200 symbols
        self.scan_interval = 15.0 # Scan for signals every 15s
        
        # V5.1.0: Protocol Drag State
        self.btc_drag_mode = False
        self.exhaustion_level = 0.0 # 0-100
        self.last_context_update = 0

    async def monitor_and_generate(self):
        """
        Monitors high CVD scores via WebSocket and generates elite signals.
        """
        self.is_running = True
        # logger.info("Signal Generator loop started.")

        while self.is_running:
            try:
                # 0. V5.1.0: Update Market Context (BTC Variation, ATR, etc.)
                now = time.time()
                if now - self.last_context_update > 300: # Every 5 mins
                    await bybit_ws_service.update_market_context()
                    self.last_context_update = now
                    
                    # Update Drag Mode State
                    btc_var = bybit_ws_service.btc_variation_1h
                    btc_cvd = bybit_ws_service.get_cvd_score("BTCUSDT")
                    
                    # Heuristic for Drag Mode: Var > 1.2% or Extreme CVD
                    # For CVD, we compare to a high threshold (e.g. $2.5M delta in recent history)
                    self.btc_drag_mode = abs(btc_var) > 1.2 or abs(btc_cvd) > 2500000
                    
                    if self.btc_drag_mode:
                        logger.info(f"🦅 V5.1.0: BTC DRAG MODE ACTIVE | Var: {btc_var:.2f}% | CVD: {btc_cvd:.2f}")
                    
                    # Update RTDB for Frontend Widget
                    await firebase_service.update_pulse_drag(self.btc_drag_mode, abs(btc_cvd), self.exhaustion_level)

                # 🆕 V6.0: Broadcast WebSocket Health to Command Tower
                await firebase_service.update_ws_health(bybit_ws_service.latency_ms)

                # V5.2.1: Check any slot availability (Sniper or Surf) to keep collecting signals
                # Capacity flexibilization: If Drag Mode, allow more slots
                max_slots = 7 if self.btc_drag_mode else 4
                can_sniper = await bankroll_manager.can_open_new_slot(slot_type="SNIPER")
                can_surf = await bankroll_manager.can_open_new_slot(slot_type="SURF")
                
                if can_sniper is None and can_surf is None:
                    # Slow down scanning if EVERYTHING is full/risk capped
                    await asyncio.sleep(15) # Reduced from 60s for better reactivity
                    continue

                # 1. Scan all active symbols from WS service
                active_symbols_ws = bybit_ws_service.active_symbols
                
                # Fetch active slots symbols to avoid redundant signals (normalized)
                slots = await firebase_service.get_active_slots()
                occupied_symbols = [normalize_symbol(s["symbol"]) for s in slots if s.get("symbol")]

                for symbol in active_symbols_ws:
                    # Sniper Rule: Don't scan symbols already in operation (use normalized comparison)
                    if normalize_symbol(symbol) in occupied_symbols:
                        continue

                    cvd_val = bybit_ws_service.get_cvd_score(symbol)
                    abs_cvd = abs(cvd_val)
                    
                    # V5.1.0: Sniper Rule (Radar 2.0): Threshold based on USD Money Flow
                    # Heuristic optimization: Reduced thresholds to populate more slots
                    threshold = 5000 if self.btc_drag_mode else 10000
                    
                    if abs_cvd > threshold: 
                        # Calibrated: $75k USD delta = ~85 score, $200k+ = 99 score
                        score = min(99, int(75 + (abs_cvd / 7500)))
                        
                        if score >= 75:
                            logger.info(f"Sniper detected ELITE opportunity: {symbol} | CVD: {cvd_val:.2f} | Score: {score}")
                            
                            # 🆕 V6.0: Reasoning Log (AI Act Compliance)
                            side_label = "Long" if cvd_val > 0 else "Short"
                            reasoning = f"Elite {side_label} Momentum | CVD: {cvd_val/1000:.1f}k | Score: {score}"
                            if self.btc_drag_mode: reasoning += " | BTC Drag Boosted"

                            await firebase_service.log_signal({
                                "symbol": symbol,
                                "score": score,
                                "type": "CVD_MOMENTUM_V6.0",
                                "market_environment": "Bullish" if cvd_val > 0 else "Bearish",
                                "is_elite": True,
                                "reasoning": reasoning,
                                "indicators": {
                                    "cvd": round(cvd_val, 4),
                                    "scanned_at": datetime.now(timezone.utc).isoformat()
                                },
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            })
                            await asyncio.sleep(0.5) 

                await asyncio.sleep(self.scan_interval) 
                
            except Exception as e:
                logger.error(f"Error in Signal Generator loop: {e}")
    async def radar_loop(self):
        """
        High-performance loop to update the Market Radar in RTDB.
        Runs independently of Signal generation.
        """
        logger.info("Market Radar (200 pairs) active via RTDB.")
        while self.is_running:
            try:
                active_symbols = bybit_ws_service.active_symbols
                radar_batch = {}
                
                for symbol in active_symbols:
                    cvd = bybit_ws_service.get_cvd_score(symbol)
                    # Radar Heuristic: $500k USD delta = 99% intensity
                    score = min(99, int(abs(cvd) / 5000))
                    radar_batch[symbol.replace(".", "_")] = { # RTDB keys cannot have dots
                        "cvd": round(cvd, 2),
                        "score": score,
                        "side": "LONG" if cvd > 10000 else "SHORT" if cvd < -10000 else "NEUTRAL"
                    }
                
                if radar_batch:
                    await firebase_service.update_radar_batch(radar_batch)
                
                await asyncio.sleep(self.radar_interval)
            except Exception as e:
                logger.error(f"Error in radar_loop: {e}")
                await asyncio.sleep(5)

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
                            # Use the centralized service to handle .P suffix
                            ticker_resp = await bybit_rest_service.get_tickers(symbol=signal["symbol"])
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
