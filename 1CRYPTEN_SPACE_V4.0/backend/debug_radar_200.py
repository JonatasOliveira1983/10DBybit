import asyncio
import logging
from services.bybit_rest import bybit_rest_service

logging.basicConfig(level=logging.INFO)

async def test_radar_expansion():
    print("Testing Radar Expansion (200 pairs Audit)...")
    
    # 1. Fetch ALL instruments info
    instr_resp = bybit_rest_service.session.get_instruments_info(category="linear")
    instr_list = instr_resp.get("result", {}).get("list", [])
    
    # 2. Check Tickers
    tickers_resp = bybit_rest_service.session.get_tickers(category="linear")
    ticker_list = tickers_resp.get("result", {}).get("list", [])
    
    # 3. Filter USDT pairs
    usdt_tickers = [t for t in ticker_list if t['symbol'].endswith("USDT")]
    usdt_tickers.sort(key=lambda x: float(x.get("turnover24h", 0)), reverse=True)
    
    print(f"Total USDT Tickers found: {len(usdt_tickers)}")
    
    # 4. Deep Audit of top 200 by volume
    top_200_raw = usdt_tickers[:200]
    
    print(f"\nAudit of Top 200 USDT pairs by Volume:")
    count_50x = 0
    count_20x = 0
    for t in top_200_raw:
        sym = t['symbol']
        info = next((i for i in instr_list if i['symbol'] == sym), {})
        max_lev = float(info.get("leverageFilter", {}).get("maxLeverage", 0))
        if max_lev >= 50:
            count_50x += 1
        if max_lev >= 20:
            count_20x += 1
            
        if t == top_200_raw[0] or t == top_200_raw[50] or t == top_200_raw[100] or t == top_200_raw[199]:
            print(f"  Rank: {top_200_raw.index(t)+1} | {sym} | Leverage: {max_lev}x")
    
    print(f"\nSummary of Top 200 by Volume:")
    print(f"  Pairs >= 50x: {count_50x}")
    print(f"  Pairs >= 20x: {count_20x}")

if __name__ == "__main__":
    asyncio.run(test_radar_expansion())
