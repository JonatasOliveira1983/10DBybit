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
        raw_key = settings.OPENROUTER_API_KEY.strip() if settings.OPENROUTER_API_KEY else None
        if raw_key and not raw_key.startswith("sk-or-v1-"):
            self.openrouter_key = f"sk-or-v1-{raw_key}"
        else:
            self.openrouter_key = raw_key
        self._setup_ai()

    def _setup_ai(self):
        """Initializes AI clients if keys are present."""
        glm_key = settings.GLM_API_KEY.strip() if settings.GLM_API_KEY else None
        if glm_key:
            try:
                self.glm_client = ZhipuAI(api_key=glm_key)
                logger.info("GLM-4-Flash Client Initialized.")
            except Exception as e:
                logger.error(f"Failed to initialize GLM Client: {e}")

        gemini_key = settings.GEMINI_API_KEY.strip() if settings.GEMINI_API_KEY else None
        if gemini_key:
            try:
                genai.configure(api_key=gemini_key)
                # Correcting to a stable model name
                self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
                logger.info("Gemini Backup Initialized (v1.5).")
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
                async with httpx.AsyncClient(timeout=20.0) as client:
                    response = await client.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.openrouter_key}",
                            "HTTP-Referer": "https://1crypten.space", 
                            "X-Title": "1CRYPTEN Space V4.0",
                        },
                        json={
                            "model": "deepseek/deepseek-chat", # Primary
                            "fallback_models": ["openai/gpt-3.5-turbo", "google/gemini-flash-1.5"],
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
                def _glm_sync():
                    return self.glm_client.chat.completions.create(
                        model="glm-4", # Removed -flash to use standard GLM-4
                        messages=[
                            {"role": "system", "content": system_instruction},
                            {"role": "user", "content": prompt}
                        ]
                    )
                response = await asyncio.to_thread(_glm_sync)
                text = response.choices[0].message.content
                if text: return text.strip()
            except Exception as e:
                logger.warning(f"GLM Fallback failed: {e}")

        # 3. Fallback: Gemini (Multi-model name resilience)
        if self.gemini_model:
            # Try multiple common name patterns if the primary fail with 404
            models_to_try = [
                self.gemini_model, # The one defined in init
                'gemini-2.5-flash',
                'gemini-2.0-flash',
                'gemini-1.5-flash',
                'models/gemini-2.5-flash',
                'models/gemini-1.5-flash'
            ]
            
            for m_obj in models_to_try:
                try:
                    full_prompt = f"{system_instruction}\n\n{prompt}"
                    # If it's a string, we need to create a temporary model object
                    def _gemini_sync():
                        if isinstance(m_obj, str):
                            temp_model = genai.GenerativeModel(m_obj)
                            return temp_model.generate_content(full_prompt)
                        else:
                            return m_obj.generate_content(full_prompt)
                            
                    response = await asyncio.to_thread(_gemini_sync)
                        
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
