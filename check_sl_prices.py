import asyncio
import os
import sys
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "1CRYPTEN_SPACE_V4.0/backend")))

from services.bybit_rest import bybit_rest_service
from services.execution_protocol import execution_protocol

async def check_sl_status():
    await bybit_rest_service.initialize()
    
    with open("1CRYPTEN_SPACE_V4.0/backend/paper_storage.json", "r") as f:
        state = json.load(f)
    
    positions = state.get("positions", [])
    print(f"Checking {len(positions)} active positions...")
    
    for pos in positions:
        symbol = pos["symbol"]
        side = pos["side"]
        entry = float(pos["avgPrice"])
        sl = float(pos.get("stopLoss", 0))
        
        if sl == 0:
            print(f"Skipping {symbol} (No SL set)")
            continue
            
        try:
            ticker = await bybit_rest_service.get_tickers(symbol=symbol)
            current_price = float(ticker.get("result", {}).get("list", [{}])[0].get("lastPrice", 0))
            
            roi = execution_protocol.calculate_roi(entry, current_price, side)
            
            is_hit = False
            if side == "Buy" and current_price <= sl:
                is_hit = True
            elif side == "Sell" and current_price >= sl:
                is_hit = True
                
            status = "❌ SL HIT" if is_hit else "✅ HEALTHY"
            print(f"{symbol} ({side}) | Price: {current_price} | Entry: {entry} | SL: {sl} | ROI: {roi:.2f}% | {status}")
            
        except Exception as e:
            print(f"Error checking {symbol}: {e}")

if __name__ == "__main__":
    asyncio.run(check_sl_status())
