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
        self.max_cvd_history = 100 # Store last 100 trade events for delta calculation
        self.active_symbols = []

    def handle_trade_message(self, message):
        """Processes trade messages to calculate CVD."""
        try:
            data = message.get("data", [])
            topic = message.get("topic", "")
            symbol = topic.replace("publicTrade.", "")

            if symbol not in self.cvd_data:
                self.cvd_data[symbol] = deque(maxlen=self.max_cvd_history)

            for trade in data:
                side = trade.get("S") # 'Buy' or 'Sell'
                size = float(trade.get("v", 0))
                
                # Buy volume is positive delta, Sell is negative
                delta = size if side == "Buy" else -size
                self.cvd_data[symbol].append({
                    "timestamp": trade.get("T"),
                    "delta": delta
                })
        except Exception as e:
            logger.error(f"Error processing trade message: {e}")

    def get_cvd_score(self, symbol: str) -> float:
        """Returns the current cumulative delta for the stored history."""
        if symbol not in self.cvd_data:
            return 0.0
        return sum(item["delta"] for item in self.cvd_data[symbol])

    def start(self, symbols: list):
        """Starts the WebSocket connection for a list of symbols."""
        self.active_symbols = symbols
        self.ws = WebSocket(
            testnet=settings.BYBIT_TESTNET,
            channel_type="linear",
        )
        
        for symbol in symbols:
            # Subscribe to trades for CVD calculation
            self.ws.trade_stream(symbol=symbol, callback=self.handle_trade_message)
            # Subscribe to tickers for price updates
            self.ws.ticker_stream(symbol=symbol, callback=lambda msg: None) # Placeholder for now

        logger.info(f"Subscribed to {len(symbols)} symbols for CVD monitoring.")

bybit_ws_service = BybitWS()
