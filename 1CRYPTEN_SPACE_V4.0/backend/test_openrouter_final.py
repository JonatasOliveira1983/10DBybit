
import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv(override=True)

async def test_prefixed_openrouter():
    raw_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    prefixed_key = raw_key if raw_key.startswith("sk-or-v1-") else f"sk-or-v1-{raw_key}"
    print(f"Testing OpenRouter with Prefixed Key: {prefixed_key[:12]}...")
    
    models = [
        "deepseek/deepseek-chat",
        "google/gemini-flash-1.5",
        "openai/gpt-3.5-turbo"
    ]
    
    for model in models:
        print(f"\n--- Testing Model: {model} ---")
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {prefixed_key}",
                        "HTTP-Referer": "http://localhost:5001",
                        "X-Title": "1CRYPTEN",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": "Hello, respond with 'Success' if you hear me."}],
                    }
                )
                print(f"Status: {response.status_code}")
                if response.status_code == 200:
                    print(f"Response: {response.json()['choices'][0]['message']['content']}")
                else:
                    print(f"Error: {response.text}")
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_prefixed_openrouter())
