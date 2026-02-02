import asyncio
import json
from services.bybit_rest import bybit_rest_service

async def run():
    await bybit_rest_service.initialize()
    t = await bybit_rest_service.get_tickers()
    all_tickers = t.get('result', {}).get('list', [])
    k_tickers = [x for x in all_tickers if x['symbol'].startswith('K')]
    print(json.dumps(k_tickers, indent=2))
    
    # Also check for exact KASUSDT
    kas = [x for x in all_tickers if x['symbol'] == 'KASUSDT']
    print(f"\nEXACT KASUSDT: {kas}")
    
    # Check for any ticker with price around 4.5
    price_match = [x for x in all_tickers if 4.0 < float(x.get('lastPrice', 0)) < 5.0]
    print(f"\nPRICES AROUND 4.5: {price_match}")

if __name__ == "__main__":
    asyncio.run(run())
