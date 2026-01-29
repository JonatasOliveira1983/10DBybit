import asyncio
import logging
from services.bybit_rest import bybit_rest_service

logging.basicConfig(level=logging.INFO)

async def test_final_naming():
    print("Verifying Final Sniper List & Naming...")
    symbols = await asyncio.to_thread(bybit_rest_service.get_top_200_usdt_pairs)
    print(f"Total Elite Symbols: {len(symbols)}")
    if len(symbols) > 0:
        print(f"Sample (First 10): {symbols[:10]}")
        print(f"Check suffix: All end with .P? {all(s.endswith('.P') for s in symbols)}")

if __name__ == "__main__":
    asyncio.run(test_final_naming())
