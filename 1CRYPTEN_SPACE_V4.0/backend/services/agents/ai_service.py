import logging
import asyncio
import time
import httpx
from zhipuai import ZhipuAI
import google.generativeai as genai
from config import settings
from services.firebase_service import firebase_service

logger = logging.getLogger("AIService")

class AIService:
    def __init__(self):
        self.glm_client = None
        self.gemini_model = None
        self.backoff_until = 0 
        self.openrouter_key = settings.OPENROUTER_API_KEY.strip() if settings.OPENROUTER_API_KEY else None
        self._setup_ai()

    def _setup_ai(self):
        """Initializes AI clients if keys are present."""
        glm_key = settings.GLM_API_KEY.strip() if settings.GLM_API_KEY else None
        if glm_key:
            try:
                self.glm_client = ZhipuAI(api_key=glm_key)
                logger.info("GLM-4.7 Client Initialized.")
            except Exception as e:
                logger.error(f"Failed to initialize GLM Client: {e}")

        gemini_key = settings.GEMINI_API_KEY.strip() if settings.GEMINI_API_KEY else None
        if gemini_key:
            try:
                genai.configure(api_key=gemini_key)
                self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
                logger.info("Gemini Backup Initialized.")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
        
        if self.openrouter_key:
            logger.info("OpenRouter (Primary) Configured.")

    async def generate_content(self, prompt: str, system_instruction: str = "Você é um assistente de trading de elite."):
        """
        Generates content using OpenRouter (DeepSeek) primarily, falling back to GLM/Gemini.
        """
        if time.time() < self.backoff_until:
            logger.info(f"AI Quota Backoff active. Skipping call.")
            return None

        # 1. Primary: OpenRouter (DeepSeek V3 - High Performance/Low Cost)
        if self.openrouter_key:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.openrouter_key}",
                            "HTTP-Referer": "https://1crypten.space", 
                            "X-Title": "1CRYPTEN Space V4.0",
                        },
                        json={
                            "model": "deepseek/deepseek-chat", # DeepSeek V3
                            "messages": [
                                {"role": "system", "content": system_instruction},
                                {"role": "user", "content": prompt}
                            ],
                            "temperature": 0.7
                        },
                        timeout=15.0
                    )
                    if response.status_code == 200:
                        data = response.json()
                        text = data['choices'][0]['message']['content']
                        if text: return text.strip()
                    elif response.status_code == 429:
                        logger.warning("OpenRouter Quota hit. Backing off.")
                        self.backoff_until = time.time() + 60
            except Exception as e:
                logger.warning(f"OpenRouter Primary failed: {e}")

        # 2. Fallback: GLM
        if self.glm_client:
            try:
                response = self.glm_client.chat.completions.create(
                    model="glm-4-plus", 
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": prompt}
                    ]
                )
                text = response.choices[0].message.content
                if text: return text.strip()
            except Exception as e:
                logger.warning(f"GLM Fallback failed: {e}")

        # 3. Fallback: Gemini
        if self.gemini_model:
            try:
                full_prompt = f"{system_instruction}\n\n{prompt}"
                response = self.gemini_model.generate_content(full_prompt)
                if response and hasattr(response, 'text'):
                    return response.text.strip()
            except Exception as e:
                logger.error(f"All AI providers failed: {e}")
                if "429" in str(e):
                    self.backoff_until = time.time() + 300

        return None

ai_service = AIService()

ai_service = AIService()
