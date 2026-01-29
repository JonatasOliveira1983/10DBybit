
import asyncio
import httpx
import google.generativeai as genai
from config import settings
import os
from dotenv import load_dotenv

load_dotenv(override=True)

async def test_openrouter():
    key = os.getenv("OPENROUTER_API_KEY")
    print(f"Testing OpenRouter with key: {key[:5]}...{key[-5:]}")
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {key}",
                },
                json={
                    "model": "deepseek/deepseek-chat",
                    "messages": [
                        {"role": "user", "content": "Hello, are you working?"}
                    ],
                }
            )
            print(f"OpenRouter Status: {response.status_code}")
            if response.status_code == 200:
                print(f"OpenRouter Response: {response.json()['choices'][0]['message']['content']}")
            else:
                print(f"OpenRouter Error: {response.text}")
    except Exception as e:
        print(f"OpenRouter Exception: {e}")

async def test_gemini():
    key = os.getenv("GEMINI_API_KEY")
    print(f"Testing Gemini with key: {key[:5]}...{key[-5:]}")
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content("Hello, are you working?")
        print(f"Gemini Response: {response.text}")
    except Exception as e:
        print(f"Gemini Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_openrouter())
    asyncio.run(test_gemini())
