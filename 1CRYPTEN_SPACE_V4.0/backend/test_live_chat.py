
import asyncio
import httpx

async def test_live_chat():
    url = "http://localhost:5001/api/chat"
    payload = {
        "message": "Olá Capitão, você está me ouvindo via OpenRouter?",
        "symbol": "BTCUSDT"
    }
    print(f"Testing Live Chat at {url}...")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            print(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                print(f"Captain Response: {response.json()['response']}")
            else:
                print(f"Error Response: {response.text}")
    except Exception as e:
        print(f"Exception during live chat test: {e}")

if __name__ == "__main__":
    asyncio.run(test_live_chat())
