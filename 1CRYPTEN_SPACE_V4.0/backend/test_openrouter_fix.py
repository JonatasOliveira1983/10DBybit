
import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv(override=True)

async def test_openrouter_variants():
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    print(f"Testing OpenRouter with key: {key[:8]}...{key[-8:]}")
    
    variants = [
        {"model": "deepseek/deepseek-chat", "desc": "Default DeepSeek"},
        {"model": "google/gemini-flash-1.5", "desc": "Gemini via OpenRouter"},
        {"model": "meta-llama/llama-3.1-8b-instruct:free", "desc": "Free Model"},
    ]
    
    for v in variants:
        print(f"\n--- Testing {v['desc']} ({v['model']}) ---")
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {key}",
                        "HTTP-Referer": "http://localhost:5001",
                        "X-Title": "1CRYPTEN",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": v["model"],
                        "messages": [{"role": "user", "content": "Hi"}],
                    }
                )
                print(f"Status: {response.status_code}")
                print(f"Response: {response.text}")
        except Exception as e:
            print(f"Exception: {e}")

async def test_key_with_prefix():
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not key.startswith("sk-or-v1-"):
        prefixed_key = f"sk-or-v1-{key}"
        print(f"\n--- Testing with prefixed key: {prefixed_key[:12]}... ---")
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {prefixed_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "meta-llama/llama-3.1-8b-instruct:free",
                        "messages": [{"role": "user", "content": "Hi"}],
                    }
                )
                print(f"Status: {response.status_code}")
                print(f"Response: {response.text}")
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_openrouter_variants())
    asyncio.run(test_key_with_prefix())
