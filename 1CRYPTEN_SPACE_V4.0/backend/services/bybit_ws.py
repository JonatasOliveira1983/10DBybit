import asyncio
import json
import logging
import time
from collections import deque
from pybit.unified_trading import WebSocket
from config import settings
from services.redis_service import redis_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BybitWS")

class BybitWS:
    def __init__(self):
        self.endpoint = "wss://stream-testnet.bybit.com/v5/public/linear" if settings.BYBIT_TESTNET else "wss://stream.bybit.com/v5/public/linear"
        self.ws = None
        # CVD storage: {symbol: {timestamp: delta}}
        self.cvd_data = {} 
        self.prices = {} # {symbol: last_price}
        self.max_cvd_history = 1000 # V5.2.2: Increased to 1000 for better signal capture
        self.active_symbols = []
        
        # V5.1.0: Protocol Drag
        self.btc_variation_1h = 0.0
        self.atr_cache = {} # {symbol: atr_value}
        self.rsi_cache = {} # {symbol: rsi_value}
        self.last_atr_update = 0
        self.loop = None # V5.4.5: Main loop reference

        # 🆕 V6.0: Command Tower Metrics
        self.latency_ms = 0
        self.last_message_time = 0
        self.buffer_health = 100

    def handle_trade_message(self, message):
        """Processes trade messages to calculate CVD."""
        try:
            # 🆕 V6.0: Latency Tracking
            receive_ts = time.time() * 1000
            msg_ts = message.get("ts", receive_ts)
            self.latency_ms = max(0, receive_ts - msg_ts)
            self.last_message_time = receive_ts

            data = message.get("data", [])
            topic = message.get("topic", "")
            # V5.2.2: Keep symbol consistent with topic (No .P suffix for Mainnet/Testnet public topics)
            symbol = topic.replace("publicTrade.", "")

            if symbol not in self.cvd_data:
                self.cvd_data[symbol] = deque(maxlen=self.max_cvd_history)

            for trade in data:
                side = trade.get("S") # 'Buy' or 'Sell'
                size = float(trade.get("v", 0))
                price = float(trade.get("p", 0))
                
                # UPDATE: Normalize CVD to USD Value for fair comparison
                # If price is 0 (unlikely for linear), use last known from ticker
                norm_sym = symbol.replace(".P", "").upper()
                if price == 0: price = self.prices.get(norm_sym, 0)
                else: self.prices[norm_sym] = price # Update last known price from trade event

                delta = (size * price) if side == "Buy" else -(size * price)
                self.cvd_data[symbol].append({
                    "timestamp": trade.get("T"),
                    "delta": delta
                })
                
                # V5.4.0: Persist to Redis Cache for low-latency ROIs
                score = sum(item["delta"] for item in self.cvd_data[symbol])
                if self.loop and self.loop.is_running():
                    asyncio.run_coroutine_threadsafe(redis_service.set_cvd(symbol, score), self.loop)
                    
            # 🆕 V6.0: Push health metrics to Redis
            if self.loop and self.loop.is_running():
                health_data = {"latency": self.latency_ms, "status": "ONLINE", "ts": self.last_message_time}
                asyncio.run_coroutine_threadsafe(redis_service.client.set("ws_health", json.dumps(health_data)), self.loop)
        except Exception as e:
            logger.error(f"Error processing trade message: {e}")

    def handle_ticker_message(self, message):
        """Processes ticker updates to maintain current price references."""
        try:
            data = message.get("data", {})
            topic = message.get("topic", "")
            if "lastPrice" in data:
                norm_sym = symbol.replace(".P", "").upper()
                price = float(data["lastPrice"])
                self.prices[norm_sym] = price
                # V5.4.0: Cache ticker in Redis
                if self.loop and self.loop.is_running():
                    asyncio.run_coroutine_threadsafe(redis_service.set_ticker(norm_sym, price), self.loop)
        except Exception: pass

    def get_current_price(self, symbol: str) -> float:
        """[V5.2.5] Returns the last known price for a symbol."""
        norm_sym = symbol.replace(".P", "").upper()
        return self.prices.get(norm_sym, 0.0)

    def get_cvd_score(self, symbol: str) -> float:
        """Returns the current cumulative delta for the stored history."""
        # V5.2.4: Normalize symbol to match internal keys (remove .P)
        norm_symbol = symbol.replace(".P", "").upper()
        if norm_symbol not in self.cvd_data:
            return 0.0
        return sum(item["delta"] for item in self.cvd_data[norm_symbol])

    async def update_market_context(self):
        """
        V5.1.0: Updates BTC variation and calculates ATR for active symbols.
        Should be called periodically (e.g., every 5-10 mins).
        """
        from services.bybit_rest import bybit_rest_service
        
        try:
            # 1. Update BTC Variation (1h)
            btc_klines = await bybit_rest_service.get_klines(symbol="BTCUSDT", interval="60", limit=2)
            if len(btc_klines) >= 2:
                # Bybit returns newest first: [current, previous]
                curr_close = float(btc_klines[0][4])
                prev_close = float(btc_klines[1][4])
                self.btc_variation_1h = ((curr_close - prev_close) / prev_close) * 100
                logger.info(f"V5.1.0: BTC 1h Variation updated: {self.btc_variation_1h:.2f}%")

            # 2. Update ATR & RSI for active symbols
            now = time.time()
            # V7.2: Sync with Sniper Pulse (Every 1 min if symbols > 0)
            if now - self.last_atr_update > 60: 
                for symbol in self.active_symbols:
                    klines = await bybit_rest_service.get_klines(symbol=symbol, interval="60", limit=16)
                    if len(klines) >= 15:
                        # --- ATR Calculation ---
                        tr_list = []
                        for i in range(1, len(klines)):
                            high, low, prev_close = float(klines[i][2]), float(klines[i][3]), float(klines[i-1][4])
                            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
                            tr_list.append(tr)
                        self.atr_cache[symbol] = sum(tr_list[-14:]) / 14

                        # --- RSI Calculation (14 periods) ---
                        changes = []
                        for i in range(1, len(klines)):
                            changes.append(float(klines[i][4]) - float(klines[i-1][4]))
                        
                        gains = [c if c > 0 else 0 for c in changes[-14:]]
                        losses = [abs(c) if c < 0 else 0 for c in changes[-14:]]
                        
                        avg_gain = sum(gains) / 14
                        avg_loss = sum(losses) / 14
                        
                        if avg_loss == 0:
                            rsi = 100
                        else:
                            rs = avg_gain / avg_loss
                            rsi = 100 - (100 / (1 + rs))
                        
                        self.rsi_cache[symbol] = rsi
                        logger.debug(f"💎 [PULSE] {symbol} | ATR: {self.atr_cache[symbol]:.6f} | RSI: {rsi:.1f}")
                
                self.last_atr_update = now
                logger.info(f"V7.2: Sniper Pulse Metrics (ATR/RSI) updated for {len(self.active_symbols)} symbols.")

        except Exception as e:
            logger.error(f"Error updating market context in BybitWS: {e}")

    async def start(self, symbols: list):
        """Starts the WebSocket connection for a list of symbols (V4.3 Expansion)."""
        self.active_symbols = symbols
        self.loop = asyncio.get_running_loop() # V5.4.5: Capture main loop
        
        self.ws = WebSocket(
            testnet=settings.BYBIT_TESTNET,
            channel_type="linear",
        )
        
        for symbol in symbols:
            api_symbol = symbol.replace(".P", "")
            # Subscribe to trades for CVD calculation (V5 Public Linear)
            self.ws.trade_stream(symbol=api_symbol, callback=self.handle_trade_message)
            # Ticker stream for real-time price & normalization
            self.ws.ticker_stream(symbol=api_symbol, callback=self.handle_ticker_message)

        logger.info(f"BybitWS: Subscribed to {len(symbols)} symbols for CVD & Price monitoring.")

    def stop(self):
        if self.ws:
            self.ws.exit()
            logger.info("Bybit WebSocket stopped.")

bybit_ws_service = BybitWS()
