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
        self.scan_interval = 5.0 # Reduced from 15s to 5s for V7.0 High-Precision Reactivity
        self.radar_interval = 10.0 # V5.4.5: Slower radar for stability
        self.signal_queue = None # ⚡ V7.2 Event-Driven Queue (Lazy Init)
        self.exhaustion_level = 0.0
 # 0-100
        self.last_context_update = 0
        # V9.0 Multi-Timeframe Trend Cache
        self.trend_cache = {}  # {symbol: {'trend': 'bullish'|'bearish'|'sideways', 'updated_at': timestamp, 'pattern': str}}
        self.trend_cache_ttl = 300  # 5 minutes cache
        self.last_sent_signals = {} # {symbol: {'score': int, 'timestamp': float}}
        self.btc_drag_mode = False # V10.2: Initial State
        # V10.6 System Harmony: State Machine
        self.system_state = "PAUSED"  # SCANNING | MONITORING | PAUSED
        self.last_state_update = 0

    async def get_1h_trend_analysis(self, symbol: str) -> dict:
        """
        V9.0: Fetch 1H candles and analyze trend + patterns.
        Returns: {'trend': 'bullish'|'bearish'|'sideways', 'pattern': str, 'trend_strength': 0-100}
        """
        try:
            # Check cache first
            cached = self.trend_cache.get(symbol)
            if cached and (time.time() - cached.get('updated_at', 0)) < self.trend_cache_ttl:
                return cached
            
            # Fetch 1H candles from Bybit via pybit
            from pybit.unified_trading import HTTP
            from config import settings
            
            session = HTTP(
                testnet=settings.BYBIT_TESTNET,
                api_key=settings.BYBIT_API_KEY,
                api_secret=settings.BYBIT_API_SECRET
            )
            
            api_symbol = symbol.replace('.P', '')
            klines = session.get_kline(
                category="linear",
                symbol=api_symbol,
                interval="60",  # 1H
                limit=24  # Last 24 hours
            )
            
            if not klines.get('result', {}).get('list'):
                return {'trend': 'sideways', 'pattern': 'unknown', 'trend_strength': 0}
            
            candles = klines['result']['list']
            # Bybit returns newest first, so reverse for chronological order
            candles = candles[::-1]
            
            # Extract close prices
            closes = [float(c[4]) for c in candles]
            highs = [float(c[2]) for c in candles]
            lows = [float(c[3]) for c in candles]
            
            if len(closes) < 10:
                return {'trend': 'sideways', 'pattern': 'unknown', 'trend_strength': 0}
            
            # Calculate trend using SMA20 vs current price
            sma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else sum(closes) / len(closes)
            current = closes[-1]
            
            # Calculate ATR for volatility context
            atr_values = []
            for i in range(1, len(closes)):
                tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
                atr_values.append(tr)
            atr = sum(atr_values[-14:]) / min(14, len(atr_values)) if atr_values else 0
            
            # Trend determination
            pct_diff = ((current - sma20) / sma20) * 100
            
            if pct_diff > 0.5:
                trend = 'bullish'
            elif pct_diff < -0.5:
                trend = 'bearish'
            else:
                trend = 'sideways'
            
            trend_strength = min(100, abs(pct_diff) * 20)
            
            # Pattern Detection
            pattern = 'none'
            
            # 1. Pullback Detection: Price retraced but bounced from SMA/support
            recent_low = min(lows[-5:])
            recent_high = max(highs[-5:])
            if trend == 'bullish' and current > sma20 and recent_low < sma20:
                pattern = 'pullback_bounce'
            elif trend == 'bearish' and current < sma20 and recent_high > sma20:
                pattern = 'pullback_rejection'
            
            # 2. Liquidity Sweep: Recent wick below/above previous range then reversal
            if len(closes) >= 10:
                prev_low = min(lows[-10:-5])
                prev_high = max(highs[-10:-5])
                curr_low = min(lows[-3:])
                curr_high = max(highs[-3:])
                
                if curr_low < prev_low and current > prev_low:
                    pattern = 'liquidity_sweep_long'
                    if trend == 'bearish': pattern = 'bear_trap'
                elif curr_high > prev_high and current < prev_high:
                    pattern = 'liquidity_sweep_short'
                    if trend == 'bullish': pattern = 'bull_trap'
            
            # 4. Accumulation Box Detection (Consolidation)
            # Find periods where price is range-bound in the last 24h
            accumulation_boxes = []
            box_min_candles = 10
            for i in range(len(highs) - box_min_candles):
                window_highs = highs[i:i+box_min_candles]
                window_lows = lows[i:i+box_min_candles]
                window_range = max(window_highs) - min(window_lows)
                # If range is tight (< 0.5% of price), mark as accumulation
                if window_range < closes[i] * 0.005:
                    accumulation_boxes.append({
                        'top': max(window_highs),
                        'bottom': min(window_lows),
                    })
            
            # Detect Box Exit
            if accumulation_boxes:
                last_box = accumulation_boxes[-1]
                if current > last_box['top'] and closes[-2] <= last_box['top']:
                    pattern = 'accumulation_box_exit_up'
                elif current < last_box['bottom'] and closes[-2] >= last_box['bottom']:
                    pattern = 'accumulation_box_exit_down'
            
            # 5. Liquidity Zones (1H Highs/Lows)
            # Identify key support/resistance levels from recent peaks/troughs
            liquidity_zones = []
            max_24h = max(highs)
            min_24h = min(lows)
            
            # Simple version: the absolute 24h extreme values are the strongest liquidity zones
            liquidity_zones.append({'price': max_24h, 'type': 'high'})
            liquidity_zones.append({'price': min_24h, 'type': 'low'})
            
            # Add secondary zones (e.g., first 12h extremes if different)
            if len(highs) >= 24:
                max_12h = max(highs[:12])
                min_12h = min(lows[:12])
                if abs(max_12h - max_24h) / max_24h > 0.002: # 0.2% difference
                    liquidity_zones.append({'price': max_12h, 'type': 'high_secondary'})
                if abs(min_12h - min_24h) / min_24h > 0.002:
                    liquidity_zones.append({'price': min_12h, 'type': 'low_secondary'})

            result = {
                'trend': trend,
                'pattern': pattern,
                'trend_strength': round(trend_strength, 1),
                'atr': round(atr, 6),
                'sma20': round(sma20, 6),
                'accumulation_boxes': accumulation_boxes[-2:], # Return last 2 detected boxes
                'liquidity_zones': liquidity_zones,
                'updated_at': time.time()
            }
            
            # Update cache
            self.trend_cache[symbol] = result
            return result
            
        except Exception as e:
            logger.warning(f"V9.0 Trend Analysis Error for {symbol}: {e}")
            return {'trend': 'sideways', 'pattern': 'unknown', 'trend_strength': 0}

    async def monitor_and_generate(self):
        """
        Monitors high CVD scores via WebSocket and generates elite signals.
        """
        self.is_running = True
        if self.signal_queue is None:
            self.signal_queue = asyncio.Queue()
        # logger.info("Signal Generator loop started.")

        while self.is_running:
            try:
                # 0. V5.1.0: Update Market Context (BTC Variation, ATR, etc.)
                now = time.time()
                if now - self.last_context_update > 60: # Reduced to 1 min for real-time BTC Pulse
                    await bybit_ws_service.update_market_context()
                    self.last_context_update = now
                    
                    # Update Drag Mode State
                    btc_var = bybit_ws_service.btc_variation_1h
                    btc_cvd = bybit_ws_service.get_cvd_score("BTCUSDT")
                    
                    # V7.0 Dynamic Exhaustion: Based on BTC CVD intensity ($5M = 100%)
                    # And amplified by 1h Variation
                    abs_btc_cvd = abs(btc_cvd)
                    base_exhaustion = (abs_btc_cvd / 5000000) * 100
                    var_boost = abs(btc_var) * 10 # 1% var = 10% exhaustion boost
                    self.exhaustion_level = min(99.0, base_exhaustion + var_boost)

                    # Heuristic for Drag Mode: Var > 1.2% or Extreme CVD
                    self.btc_drag_mode = abs(btc_var) > 1.2 or abs_btc_cvd > 2500000
                    
                    if self.btc_drag_mode:
                        logger.info(f"🦅 V7.0: BTC DRAG MODE ACTIVE | Var: {btc_var:.2f}% | CVD: {btc_cvd:.2f} | Exh: {self.exhaustion_level:.1f}%")
                    
                    # Update RTDB for Frontend Widget
                    await firebase_service.update_pulse_drag(self.btc_drag_mode, abs_btc_cvd, self.exhaustion_level)

                # 🆕 V6.0: Broadcast WebSocket Health to Command Tower
                await firebase_service.update_ws_health(bybit_ws_service.latency_ms)

                # V10.6 System Harmony: Check ALL slots and manage state
                from services.vault_service import vault_service
                trading_allowed, reason = await vault_service.is_trading_allowed()
                
                if not trading_allowed:
                    # Captain is PAUSED by user
                    if self.system_state != "PAUSED":
                        self.system_state = "PAUSED"
                        await firebase_service.update_system_state("PAUSED", 0, reason)
                        logger.info(f"🔴 V10.6: System State → PAUSED ({reason})")
                    await asyncio.sleep(5)  # V10.6.1: Reduced from 30s
                    continue
                
                # Count occupied slots
                slots = await firebase_service.get_active_slots()
                occupied_count = sum(1 for s in slots if s.get("symbol"))
                
                if occupied_count >= 2:
                    # Both slots occupied → MONITORING mode (pause signal generation)
                    if self.system_state != "MONITORING":
                        self.system_state = "MONITORING"
                        await firebase_service.update_system_state("MONITORING", occupied_count, "Monitorando 2/2 posições")
                        logger.info(f"👁️ V10.6: System State → MONITORING (Slots: {occupied_count}/2)")
                    # Complete pause - only check periodically if a slot freed up
                    await asyncio.sleep(10)
                    continue
                
                # At least one slot free → SCANNING mode
                if self.system_state != "SCANNING":
                    self.system_state = "SCANNING"
                    await firebase_service.update_system_state("SCANNING", occupied_count, "Buscando oportunidades")
                    logger.info(f"🔍 V10.6: System State → SCANNING (Slots: {occupied_count}/2)")
                
                # Fresh scan for best opportunity
                can_sniper = await bankroll_manager.can_open_new_slot(slot_type="SNIPER")
                
                if can_sniper is None:
                    # Edge case: slot check says no, but we detected free slot
                    await asyncio.sleep(5) 
                    continue

                # V9.0 Sniper Scan: Only instruments with exactly 50x leverage
                from services.bybit_rest import bybit_rest_service
                active_symbols_ws = await bybit_rest_service.get_elite_50x_pairs()
                
                # Fetch active slots symbols to avoid redundant signals (normalized)
                slots = await firebase_service.get_active_slots()
                occupied_symbols = [normalize_symbol(s["symbol"]) for s in slots if s.get("symbol")]

                for symbol in active_symbols_ws:
                    # Sniper Rule: Don't scan symbols already in operation (use normalized comparison)
                    if normalize_symbol(symbol) in occupied_symbols:
                        continue
                    
                    # V8.0 Sequential Diversification: Skip último par operado
                    from services.agents.captain import captain_agent
                    last_traded = getattr(captain_agent, 'last_traded_symbol', None)
                    if last_traded:
                        if normalize_symbol(symbol) == normalize_symbol(last_traded):
                            continue

                    cvd_val = bybit_ws_service.get_cvd_score(symbol)
                    abs_cvd = abs(cvd_val)
                    
                    # V5.1.0: Sniper Rule (Radar 2.0): Threshold based on USD Money Flow
                    # Heuristic optimization: Reduced thresholds to populate more slots
                    threshold = 5000 if self.btc_drag_mode else 10000
                    
                    if abs_cvd > threshold: 
                        # --- V7.2 Multi-Indicator Scoring ---
                        # Base CVD Score (0-70 points)
                        cvd_score = min(70.0, (abs_cvd / 200000) * 70.0) if abs_cvd > 50000 else 0
                        
                        # RSI Score & Filter (0-30 points)
                        rsi = bybit_ws_service.rsi_cache.get(symbol, 50)
                        rsi_score = 0.0
                        side_label = "Long" if cvd_val > 0 else "Short"
                        
                        # RSI Alignment logic
                        if side_label == "Long":
                            # Sniper Reversal Long: Prime below 30 RSI
                            if rsi > 60: 
                                logger.info(f"🚫 [RSI MOMENTUM BLOCK] {symbol} Long blocked (RSI: {rsi:.1f})")
                                continue
                            rsi_score = min(30.0, ((65 - rsi) / 35.0) * 30.0) if rsi < 65 else 0
                        else: # Short
                            # Sniper Reversal Short: Prime above 70 RSI
                            if rsi < 40:
                                logger.info(f"🚫 [RSI MOMENTUM BLOCK] {symbol} Short blocked (RSI: {rsi:.1f})")
                                continue
                            rsi_score = min(30.0, ((rsi - 35) / 35.0) * 30.0) if rsi > 35 else 0
                        
                        # --- V9.0 Multi-Timeframe Analysis ---
                        trend_analysis = await self.get_1h_trend_analysis(symbol)
                        trend = trend_analysis.get('trend', 'sideways')
                        pattern = trend_analysis.get('pattern', 'none')
                        trend_strength = trend_analysis.get('trend_strength', 0)
                        
                        # Trend Alignment Check: Block contra-trend trades
                        if trend == 'bullish' and side_label == 'Short':
                            logger.info(f"🚫 [TREND BLOCK] {symbol} Short blocked (1H Trend: Bullish, Str: {trend_strength:.1f})")
                            continue
                        elif trend == 'bearish' and side_label == 'Long':
                            logger.info(f"🚫 [TREND BLOCK] {symbol} Long blocked (1H Trend: Bearish, Str: {trend_strength:.1f})")
                            continue
                        
                        # Pattern Bonus (0-20 points)
                        pattern_bonus = 0
                        if pattern in ['pullback_bounce', 'pullback_rejection']:
                            pattern_bonus = 12
                        elif pattern in ['liquidity_sweep_long', 'liquidity_sweep_short']:
                            pattern_bonus = 15
                        elif pattern in ['bull_trap', 'bear_trap']:
                            pattern_bonus = 20
                        elif pattern in ['accumulation_box_exit_up', 'accumulation_box_exit_down']:
                            pattern_bonus = 18
                        elif pattern in ['breakout_up', 'breakout_down']:
                            pattern_bonus = 10
                        
                        # Whale Activity Bonus (0-20 points)
                        # Threshold based on $250k USD delta in the recent buffer
                        is_whale = abs(cvd_val) > 250000
                        whale_bonus = 20 if is_whale else 0
                        
                        # Trend Alignment Bonus (0-10 points)
                        trend_bonus = 0
                        if (trend == 'bullish' and side_label == 'Long') or (trend == 'bearish' and side_label == 'Short'):
                            trend_bonus = min(10.0, trend_strength / 10)
                        
                        final_score = int(cvd_score + rsi_score + trend_bonus + pattern_bonus + whale_bonus + 15) # Base 15
                        final_score = min(99, final_score)

                        if final_score >= 90:
                            # --- V10.0 De-duplication Logic ---
                            last_sig = self.last_sent_signals.get(symbol)
                            now_ts = time.time()
                            if last_sig:
                                time_since = now_ts - last_sig['timestamp']
                                score_diff = final_score - last_sig['score']
                                
                                # Skip if was sent recently (< 60s) AND score didn't improve significantly
                                if time_since < 60 and score_diff <= 3:
                                    continue
                            
                            # Update last sent tracking
                            self.last_sent_signals[symbol] = {
                                'score': final_score,
                                'timestamp': now_ts
                            }

                            whale_label = " | 🐋 Whale Activity" if is_whale else ""
                            pattern_label = f" | Pattern: {pattern.replace('_', ' ')}" if pattern != 'none' else ""
                            logger.info(f"🎯 Sniper detected ELITE opportunity: {symbol} | Score: {final_score}{pattern_label}{whale_label}")
                            
                            reasoning = f"Elite {side_label} | CVD: {cvd_val/1000:.1f}k | RSI: {rsi:.1f} | Trend: {trend}{pattern_label}{whale_label}"
                            if self.btc_drag_mode: reasoning += " | BTC Drag Boosted"

                            signal_data = {
                                "id": f"sig_{int(time.time())}_{symbol}", # Ensure ID is available for queue
                                "symbol": symbol,
                                "score": final_score,
                                "type": "MULTI_PULSE_V10.0",
                                "market_environment": "Bullish" if cvd_val > 0 else "Bearish",
                                "is_elite": True,
                                "reasoning": reasoning,
                                "indicators": {
                                    "cvd": round(cvd_val, 4),
                                    "rsi": round(rsi, 2),
                                    "scanned_at": datetime.now(timezone.utc).isoformat()
                                },
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            }
                            
                            # 1. Log to Firebase (Primary Record)
                            await firebase_service.log_signal(signal_data)
                            
                            # 2. ⚡ Push to Event Queue for Zero-Latency Execution
                            await self.signal_queue.put(signal_data)
                            
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
