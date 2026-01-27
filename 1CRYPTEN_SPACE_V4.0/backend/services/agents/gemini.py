import logging
import asyncio
from services.agents.ai_service import ai_service
from services.firebase_service import firebase_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GeminiAgent")

class GeminiAgent:
    def __init__(self):
        self.min_score_elite = 60 # Default

    async def analyze_journey_and_recalibrate(self):
        """
        Fetches last 100 signals and uses AI to recalibrate the dynamic Score Elite.
        """
        try:
            # Placeholder for signals data (would be fetched from Firestore in production)
            signals_summary = "Signal data showing high volatility in last 4h with CVD trends favoring volume exaustão."
            
            prompt = f"""
            Analise o ambiente de mercado atual do sistema 1CRYPTEN.
            Dados recentes: {signals_summary}
            Quais indicadores tiveram maior taxa de acerto?
            Retorne APENAS um número inteiro entre 1 e 100 representando o novo 'Score Elite' mínimo para entradas.
            """
            
            response_text = await ai_service.generate_content(
                prompt=prompt,
                system_instruction="Você é o estrategista chefe do sistema 1CRYPTEN. Sua missão é calibrar a agressividade do radar."
            )
            
            if response_text and response_text.isdigit():
                new_score = int(response_text)
                if 1 <= new_score <= 100:
                    self.min_score_elite = new_score
                    logger.info(f"AI recalibrated Score Elite to: {new_score}")
                    await firebase_service.log_event("AI_Strategist", f"Strategic recalibration complete. New threshold: {new_score}", "SUCCESS")
                    return new_score
            
            return self.min_score_elite
        except Exception as e:
            logger.error(f"AI recalibration failed: {e}")
            return self.min_score_elite

gemini_agent = GeminiAgent()
