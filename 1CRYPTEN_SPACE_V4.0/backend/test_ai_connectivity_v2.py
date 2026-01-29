
import asyncio
import httpx
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv(override=True)

async def test_openrouter():
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    print(f"Testing OpenRouter with key: {key[:8]}...{key[-8:]}")
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "google/gemini-flash-1.5", # Try a different model on OpenRouter
                    "messages": [
                        {"role": "user", "content": "Ping"}
                    ],
                }
            )
            print(f"OpenRouter Status: {response.status_code}")
            print(f"OpenRouter Response Body: {response.text}")
    except Exception as e:
        print(f"OpenRouter Exception: {e}")

async def test_gemini():
    key = os.getenv("GEMINI_API_KEY", "").strip()
    print(f"Testing Gemini with key: {key[:8]}...{key[-8:]}")
    try:
        genai.configure(api_key=key)
        print("Listing available Gemini models...")
        available_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
        print(f"Available models: {available_models}")
        
        # Try the first available one
        if available_models:
            model_name = available_models[0]
            print(f"Trying model: {model_name}")
            model = genai.GenerativeModel(model_name)
            response = model.generate_content("Ping")
            print(f"Gemini ({model_name}) Response: {response.text}")
        else:
            print("No suitable Gemini models found.")
    except Exception as e:
        print(f"Gemini Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_openrouter())
    asyncio.run(test_gemini())
