import logging
from pybit.unified_trading import HTTP
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BybitREST")

class BybitREST:
    def __init__(self):
        self._session = None
        self.category = settings.BYBIT_CATEGORY

    @property
    def session(self):
        """Lazy initialization of the Bybit HTTP session."""
        if self._session is None:
            self._session = HTTP(
                testnet=settings.BYBIT_TESTNET,
                api_key=settings.BYBIT_API_KEY,
                api_secret=settings.BYBIT_API_SECRET,
                enable_time_sync=True,
                recv_window=20000,
            )


        return self._session
    def get_top_100_usdt_pairs(self):
        """Fetches top 100 perpetual USDT pairs by 24h turnover."""
        try:
            tickers = self.session.get_tickers(category=self.category)
            result = tickers.get("result", {}).get("list", [])
            
            # Filter USDT.P pairs (usually end in USDT or have linear category)
            # In V5, linear symbols are like BTCUSDT
            usdt_pairs = [t for t in result if t["symbol"].endswith("USDT")]
            
            # Sort by 24h turnover (volatility/liquidity)
            sorted_pairs = sorted(usdt_pairs, key=lambda x: float(x.get("turnover24h", 0)), reverse=True)
            
            return [p["symbol"] for p in sorted_pairs[:100]]
        except Exception as e:
            logger.error(f"Error fetching top pairs: {e}")
            return []

    def get_wallet_balance(self):
        """Fetches the total equity from the Bybit account (UNIFIED or CONTRACT)."""
        try:
            # Try UNIFIED first
            logger.info("Fetching balance (UNIFIED)...")
            try:
                response = self.session.get_wallet_balance(accountType="UNIFIED")
                result = response.get("result", {}).get("list", [{}])[0]
                equity = float(result.get("totalEquity", 0))
                logger.info(f"UNIFIED Equity: {equity}")
                if equity > 0: return equity
            except Exception as ue: 
                logger.warning(f"UNIFIED balance fetch failed: {ue}")
            
            # Try CONTRACT if UNIFIED fails or is 0
            logger.info("Fetching balance (CONTRACT)...")
            response = self.session.get_wallet_balance(accountType="CONTRACT")
            result = response.get("result", {}).get("list", [{}])[0]
            coins = result.get("coin", [])
            usdt_coin = next((c for c in coins if c.get("coin") == "USDT"), {})
            equity = float(usdt_coin.get("equity", 0))
            logger.info(f"CONTRACT Equity: {equity}")
            return equity
        except Exception as e:
            logger.error(f"Error fetching wallet balance: {e}")
            return 0.0

    def get_active_positions(self):
        """Fetches all currently open linear positions."""
        try:
            response = self.session.get_positions(category="linear", settleCoin="USDT")
            pos_list = response.get("result", {}).get("list", [])
            # Filter for positions with size > 0
            active = [p for p in pos_list if float(p.get("size", 0)) > 0]
            return active
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return []

    def get_instrument_info(self, symbol: str):
        """Fetches precision and lot size filtering for a symbol."""
        try:
            response = self.session.get_instruments_info(category="linear", symbol=symbol)
            return response.get("result", {}).get("list", [{}])[0]
        except Exception as e:
            logger.error(f"Error fetching instrument info for {symbol}: {e}")
            return {}




    def place_atomic_order(self, symbol: str, side: str, qty: float, sl_price: float, tp_price: float = None):
        """
        Sends a Market Order with Stop Loss in the same request.
        This is the Lv 0 Sniper execution.
        """
        try:
            order_params = {
                "category": self.category,
                "symbol": symbol,
                "side": side,
                "orderType": "Market",
                "qty": str(qty),
                "stopLoss": str(sl_price),
                "tpTriggerBy": "LastPrice",
                "slTriggerBy": "LastPrice",
                "tpslMode": "Full", # Use Full T/SL mode
            }
            if tp_price:
                order_params["takeProfit"] = str(tp_price)

            response = self.session.place_order(**order_params)
            logger.info(f"Atomic order placed for {symbol}: {response}")
            return response
        except Exception as e:
            logger.error(f"Failed to place atomic order for {symbol}: {e}")
            return None

    def close_position(self, symbol: str, side: str, qty: float):
        """Closes a position at market."""
        try:
            # Side is the current position side, so we sell to close a long
            close_side = "Sell" if side == "Buy" else "Buy"
            response = self.session.place_order(
                category=self.category,
                symbol=symbol,
                side=close_side,
                orderType="Market",
                qty=str(qty),
                reduceOnly=True
            )
            return response
        except Exception as e:
            logger.error(f"Error closing position for {symbol}: {e}")
            return None

bybit_rest_service = BybitREST()
