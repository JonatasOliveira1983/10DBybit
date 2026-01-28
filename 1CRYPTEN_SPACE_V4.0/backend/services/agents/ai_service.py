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
        self.backoff_until = 0 # Timestamp to avoid calls during quota limits
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
                    models = list(genai.list_models())
                    available_names = [m.name for m in models]
                    logger.info(f"Available Gemini Models: {available_names}")
                    
                    # Try to find a flash model in the list
                    found_model = None
                    for m in models:
                        if 'flash' in m.name.lower() and 'generateContent' in m.supported_generation_methods:
                            found_model = m.name
                            break
                    
                    if found_model:
                        self.gemini_model = genai.GenerativeModel(found_model)
                        logger.info(f"Gemini Client Initialized with detected model: {found_model}")
                    else:
                        # Fallback to standard names if list failed or nothing found
                        self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
                        logger.info("Gemini Client fallback to 'gemini-1.5-flash'")
                except Exception as list_err:
                    logger.warning(f"Could not list models: {list_err}. Falling back to default name.")
                    self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
            except Exception as e:
                logger.error(f"Failed to initialize Gemini Client: {e}")

    async def generate_content(self, prompt: str, system_instruction: str = "Você é um assistente de trading de elite."):
        """
        Generates content using GLM-4.7 primarily, falling back to Gemini.
        """
        import time
        if time.time() < self.backoff_until:
            logger.info(f"AI Quota Backoff active. Skipping call. (Remaining: {int(self.backoff_until - time.time())}s)")
            return None

        text = None
        # Try GLM Primary
        if self.glm_client:
            try:
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
                if text: return text.strip()
            except Exception as e:
                err_str = str(e).lower()
                if "429" in err_str or "quota" in err_str:
                    logger.warning("GLM Quota hit. Backing off for 60s.")
                    self.backoff_until = time.time() + 60
                logger.warning(f"GLM-4-Plus failed: {e}")

        # Try Gemini Backup
        if self.gemini_model:
            try:
                full_prompt = f"{system_instruction}\n\n{prompt}"
                response = self.gemini_model.generate_content(full_prompt)
                if response and hasattr(response, 'text'):
                    text = response.text
                    if text: return text.strip()
            except Exception as e:
                err_str = str(e).lower()
                if "429" in err_str or "quota" in err_str or "exhausted" in err_str:
                    # If we hit 429 on the backup, it's serious. Back off for 5 mins.
                    logger.warning("Gemini Quota exhausted. Backing off AI for 300s.")
                    self.backoff_until = time.time() + 300
                    await firebase_service.log_event("AI_QUOTA", "Gemini Quota hit. Backing off for 5 minutes.", "WARNING")
                logger.error(f"Gemini also failed: {e}")

        return None

        return None

ai_service = AIService()
