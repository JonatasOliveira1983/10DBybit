import logging
from services.bybit_rest import bybit_rest_service
from services.bybit_ws import bybit_ws_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ContrarianAgent")

class ContrarianAgent:
    def __init__(self):
        self.funding_threshold = 0.0008 # 0.08%

    async def check_flip_opportunity(self, symbol: str):
        """
        Monitors for extreme sentiment and exaustão in price/volume.
        Triggers the P.I.R. (Protocolo de Identificação de Reversão).
        """
        try:
            # 1. Fetch current funding rate from Bybit
            tickers = bybit_rest_service.session.get_tickers(category="linear", symbol=symbol)
            ticker_data = tickers.get("result", {}).get("list", [{}])[0]
            funding_rate = float(ticker_data.get("fundingRate", 0))
            
            # 2. Get CVD delta from our WebSocket service
            cvd_score = bybit_ws_service.get_cvd_score(symbol)
            
            # 3. Decision Logic (Flip)
            # Scenario: Extreme Long funding + High Price + Falling CVD = Absorption/Exhaustion
            if funding_rate > self.funding_threshold and cvd_score < 0:
                logger.warning(f"Extreme Long Sentiment detected for {symbol} with CVD exhaustion. Triggering FLIP SHORT.")
                return "SHORT"
            
            # Scenario: Extreme Short funding + Low Price + Rising CVD = Bottoming/Absorption
            if funding_rate < -self.funding_threshold and cvd_score > 0:
                logger.warning(f"Extreme Short Sentiment detected for {symbol} with CVD absorption. Triggering FLIP LONG.")
                return "LONG"
                
            return None
        except Exception as e:
            logger.error(f"Error checking flip for {symbol}: {e}")
            return None

contrarian_agent = ContrarianAgent()
