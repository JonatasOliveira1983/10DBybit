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
            return None

        # 1. Primary: OpenRouter (DeepSeek V3 - High Performance/Low Cost)
        if self.openrouter_key:
            try:
                # Use a specific timeout to avoid hanging the whole system during high latency
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.openrouter_key}",
                            "HTTP-Referer": "https://1crypten.space", 
                            "X-Title": "1CRYPTEN Space V4.0",
                        },
                        json={
                            "model": "deepseek/deepseek-chat",
                            "messages": [
                                {"role": "system", "content": system_instruction},
                                {"role": "user", "content": prompt}
                            ],
                            "temperature": 0.7
                        }
                    )
                    if response.status_code == 200:
                        data = response.json()
                        text = data['choices'][0]['message']['content']
                        if text: return text.strip()
                    else:
                        logger.warning(f"OpenRouter returned {response.status_code}: {response.text}")
                        if response.status_code == 429:
                             self.backoff_until = time.time() + 60
            except Exception as e:
                logger.warning(f"OpenRouter connection error: {e}")

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

        # 3. Fallback: Gemini (Multi-model name resilience)
        if self.gemini_model:
            # Try multiple common name patterns if the primary fail with 404
            models_to_try = [
                self.gemini_model, # The one defined in init
                'gemini-1.5-flash-latest',
                'models/gemini-1.5-flash'
            ]
            
            for m_obj in models_to_try:
                try:
                    full_prompt = f"{system_instruction}\n\n{prompt}"
                    # If it's a string, we need to create a temporary model object
                    if isinstance(m_obj, str):
                        temp_model = genai.GenerativeModel(m_obj)
                        response = temp_model.generate_content(full_prompt)
                    else:
                        response = m_obj.generate_content(full_prompt)
                        
                    if response and hasattr(response, 'text'):
                        return response.text.strip()
                except Exception as e:
                    if "404" in str(e): continue # Try next model
                    logger.error(f"Gemini provider error with {m_obj}: {e}")
                    if "429" in str(e):
                        self.backoff_until = time.time() + 300
                        break

        return None

ai_service = AIService()

ai_service = AIService()
