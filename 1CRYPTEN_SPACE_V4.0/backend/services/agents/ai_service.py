import logging
import asyncio
from zhipuai import ZhipuAI
import google.generativeai as genai
from config import settings
from services.firebase_service import firebase_service

logger = logging.getLogger("AIService")

class AIService:
    def __init__(self):
        self.glm_client = None
        self.gemini_model = None
        self._setup_ai()

    def _setup_ai(self):
        """Initializes AI clients if keys are present."""
        glm_key = settings.GLM_API_KEY.strip() if settings.GLM_API_KEY else None
        if glm_key:
            try:
                self.glm_client = ZhipuAI(api_key=glm_key)
                logger.info("GLM-4.7 (ZhipuAI) Client Initialized.")
            except Exception as e:
                logger.error(f"Failed to initialize GLM Client: {e}")

        gemini_key = settings.GEMINI_API_KEY.strip() if settings.GEMINI_API_KEY else None
        if gemini_key:
            try:
                genai.configure(api_key=gemini_key)
                
                # Diagnostic: List models to log what's available
                try:
                    available_models = [m.name for m in genai.list_models()]
                    logger.info(f"Available Gemini Models: {available_models}")
                except Exception as list_err:
                    logger.warning(f"Could not list models (possibly API restricted): {list_err}")
                
                # Try multiple stable/beta names for 1.5-flash
                # Some API keys/regions expect different identifiers
                candidate_names = ['gemini-1.5-flash', 'gemini-1.5-flash-latest', 'models/gemini-1.5-flash']
                
                for model_name in candidate_names:
                    try:
                        self.gemini_model = genai.GenerativeModel(model_name)
                        # Test if it actually works by checking if it was assigned
                        if self.gemini_model:
                             logger.info(f"Gemini Client Initialized with model: {model_name}")
                             break
                    except Exception as mod_err:
                        logger.debug(f"Candidate model {model_name} failed: {mod_err}")
                
                if not self.gemini_model:
                    logger.error("All Gemini 1.5 Flash candidate names failed.")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini Client: {e}")

    async def generate_content(self, prompt: str, system_instruction: str = "Você é um assistente de trading de elite."):
        """
        Generates content using GLM-4.7 primarily, falling back to Gemini.
        """
        text = None
        # Try GLM Primary
        if self.glm_client:
            try:
                logger.info("Attempting generation with GLM-4.7 (glm-4-plus)...")
                response = self.glm_client.chat.completions.create(
                    model="glm-4-plus", 
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": prompt}
                    ],
                    top_p=0.7,
                    temperature=0.9
                )
                text = response.choices[0].message.content
                if text:
                    logger.info("GLM-4-Plus generation successful.")
                    return text.strip()
            except Exception as e:
                logger.warning(f"GLM-4-Plus failed, falling back to Gemini: {e}")
                await firebase_service.log_event("AI_FAILOVER", f"GLM failed: {e}. Switching to Gemini.", "WARNING")

        # Try Gemini Backup
        if self.gemini_model:
            try:
                logger.info("Attempting generation with Gemini-1.5-Flash...")
                full_prompt = f"{system_instruction}\n\n{prompt}"
                response = self.gemini_model.generate_content(full_prompt)
                if response and hasattr(response, 'text'):
                    text = response.text
                    if text:
                        logger.info("Gemini generation successful.")
                        return text.strip()
            except Exception as e:
                logger.error(f"Gemini backup also failed: {e}")
                await firebase_service.log_event("AI_ERROR", f"Both GLM and Gemini failed: {e}", "ERROR")

        return None

ai_service = AIService()
