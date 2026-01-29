import asyncio
import json
import logging
from collections import deque
from pybit.unified_trading import WebSocket
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BybitWS")

class BybitWS:
    def __init__(self):
        self.endpoint = "wss://stream-testnet.bybit.com/v5/public/linear" if settings.BYBIT_TESTNET else "wss://stream.bybit.com/v5/public/linear"
        self.ws = None
        # CVD storage: {symbol: {timestamp: delta}}
        self.cvd_data = {} 
        self.prices = {} # {symbol: last_price}
        self.max_cvd_history = 100 # Store last 100 trade events for delta calculation
        self.active_symbols = []

    def handle_trade_message(self, message):
        """Processes trade messages to calculate CVD."""
        try:
            data = message.get("data", [])
            topic = message.get("topic", "")
            raw_symbol = topic.replace("publicTrade.", "")
            symbol = f"{raw_symbol}.P"

            if symbol not in self.cvd_data:
                self.cvd_data[symbol] = deque(maxlen=self.max_cvd_history)

            for trade in data:
                side = trade.get("S") # 'Buy' or 'Sell'
                size = float(trade.get("v", 0))
                price = float(trade.get("p", 0))
                
                # UPDATE: Normalize CVD to USD Value for fair comparison
                # If price is 0 (unlikely for linear), use last known from ticker
                if price == 0: price = self.prices.get(symbol, 0)
                else: self.prices[symbol] = price # Update last known price from trade event

                delta = (size * price) if side == "Buy" else -(size * price)
                self.cvd_data[symbol].append({
                    "timestamp": trade.get("T"),
                    "delta": delta
                })
        except Exception as e:
            logger.error(f"Error processing trade message: {e}")

    def handle_ticker_message(self, message):
        """Processes ticker updates to maintain current price references."""
        try:
            data = message.get("data", {})
            topic = message.get("topic", "")
            raw_symbol = topic.replace("tickers.", "")
            symbol = f"{raw_symbol}.P"
            
            if "lastPrice" in data:
                self.prices[symbol] = float(data["lastPrice"])
        except Exception: pass

    def get_cvd_score(self, symbol: str) -> float:
        """Returns the current cumulative delta for the stored history."""
        if symbol not in self.cvd_data:
            return 0.0
        return sum(item["delta"] for item in self.cvd_data[symbol])

    async def start(self, symbols: list):
        """Starts the WebSocket connection for a list of symbols (V4.3 Expansion)."""
        self.active_symbols = symbols
        
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
