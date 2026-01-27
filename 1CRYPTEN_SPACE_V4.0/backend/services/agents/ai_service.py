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
                available_models = [m.name for m in genai.list_models()]
                logger.info(f"Available Gemini Models: {available_models}")
                
                # Using the latest stable model name
                self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
                logger.info("Gemini-1.5-Flash Client Initialized.")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini Client or list models: {e}")

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
