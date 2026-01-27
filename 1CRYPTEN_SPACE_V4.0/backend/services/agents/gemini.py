import logging
import google.generativeai as genai
from config import settings
from services.firebase_service import firebase_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GeminiAgent")

class GeminiAgent:
    def __init__(self):
        self._model = None
        self.min_score_elite = 60 # Default

    @property
    def model(self):
        """Lazy initialization of the Gemini model."""
        if self._model is None:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self._model = genai.GenerativeModel('gemini-pro')
        return self._model
    async def analyze_journey_and_recalibrate(self):
        """
        Fetches last 100 signals, sends to Gemini for analysis,
        and updates the dynamic Score Elite.
        """
        try:
            # 1. Fetch recent signals
            # response = await firebase_service.get_recent_signals(100) 
            # (Need to implement get_recent_signals in firebase_service)
            
            # Placeholder for signals data
            signals_summary = "Signal data: [List of indicators and outcomes...]"
            
            prompt = f"""
            Analise os últimos 100 sinais de trade do sistema 1CRYPTEN.
            Dados: {signals_summary}
            Quais indicadores tiveram maior taxa de acerto nas últimas 4 horas?
            Retorne APENAS um número inteiro entre 1 e 100 representando o novo 'Score Elite' mínimo para entradas do Capitão.
            """
            
            response = self.model.generate_content(prompt)
            new_score = int(response.text.strip())
            
            if 1 <= new_score <= 100:
                self.min_score_elite = new_score
                logger.info(f"Gemini recalibrated Score Elite to: {new_score}")
                await firebase_service.log_event("Gemini", f"Strategic recalibration complete. New Score Elite threshold: {new_score}", "SUCCESS")
                return new_score
            
            return self.min_score_elite
        except Exception as e:
            logger.error(f"Gemini recalibration failed: {e}")
            return self.min_score_elite

gemini_agent = GeminiAgent()
