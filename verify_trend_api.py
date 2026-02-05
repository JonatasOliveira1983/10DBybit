import asyncio
import json
import httpx

async def test_trend_api():
    symbol = "BTCUSDT"
    url = f"http://127.0.0.1:8080/api/trend/{symbol}"
    print(f"Testing trend API for {symbol} at {url}...")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                print("API Response:")
                print(json.dumps(data, indent=2))
                
                # Check for new fields
                if 'accumulation_boxes' in data:
                    print("✅ 'accumulation_boxes' found.")
                else:
                    print("❌ 'accumulation_boxes' NOT found.")
                    
                if 'liquidity_zones' in data:
                    print("✅ 'liquidity_zones' found.")
                else:
                    print("❌ 'liquidity_zones' NOT found.")
            else:
                print(f"❌ API returned status code {response.status_code}")
    except Exception as e:
        print(f"❌ Error connecting to API: {e}")

if __name__ == "__main__":
    asyncio.run(test_trend_api())
