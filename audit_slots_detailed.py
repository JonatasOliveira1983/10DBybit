import asyncio
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "1CRYPTEN_SPACE_V4.0/backend")))

from services.firebase_service import firebase_service
from services.bybit_rest import bybit_rest_service
from services.execution_protocol import execution_protocol

async def audit_slots():
    await firebase_service.initialize()
    await bybit_rest_service.initialize()
    
    slots = await firebase_service.get_active_slots()
    print("\n--- AUDITING ACTIVE SLOTS ---")
    
    for s in slots:
        symbol = s.get("symbol")
        if not symbol: continue
        
        slot_id = s["id"]
        side = s.get("side")
        entry = float(s.get("entry_price", 0))
        stop = float(s.get("current_stop", 0))
        
        if entry == 0: continue
        
        try:
            ticker = await bybit_rest_service.get_tickers(symbol=symbol)
            last_price = float(ticker.get("result", {}).get("list", [{}])[0].get("lastPrice", 0))
            
            roi = execution_protocol.calculate_roi(entry, last_price, side)
            
            is_hit = False
            if side == "Buy" and last_price <= stop: is_hit = True
            elif side == "Sell" and last_price >= stop: is_hit = True
            
            status = "🚨 SL HIT!" if is_hit else "✅ OK"
            print(f"Slot {slot_id} | {symbol} | Price: {last_price} | Stop: {stop} | ROI: {roi:.2f}% | {status}")
            
        except Exception as e:
            print(f"Error auditing slot {slot_id} ({symbol}): {e}")

if __name__ == "__main__":
    asyncio.run(audit_slots())
