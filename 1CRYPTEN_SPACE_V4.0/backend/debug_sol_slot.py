import asyncio
from services.firebase_service import firebase_service
from services.bybit_rest import bybit_rest_service

async def inspect_sol_slot():
    print("Fetching active slots...")
    slots = await firebase_service.get_active_slots()
    
    sol_slot = next((s for s in slots if s.get("symbol") and "SOL" in s.get("symbol")), None)
    
    if not sol_slot:
        print("No active SOL slot found.")
        return

    print("\n--- SOLUSDT SLOT DETAILS ---")
    print(f"ID: {sol_slot.get('id')}")
    print(f"Symbol: {sol_slot.get('symbol')}")
    print(f"Side: {sol_slot.get('side')}")
    print(f"Entry Price: {sol_slot.get('entry_price')}")
    print(f"Current Stop: {sol_slot.get('current_stop')}")
    print(f"PnL %: {sol_slot.get('pnl_percent')}")
    print(f"Status Risk: {sol_slot.get('status_risco')}")
    
    # Try to find timestamp (might not be on slot directly depending on schema, check logs?)
    # Usually slots don't have 'created_at' in the minimal schema unless added.
    # We can check the chart history for this price.
    
    entry = sol_slot.get('entry_price')
    print(f"\nVerifying Market Price for {sol_slot.get('symbol')}...")
    ticker = await asyncio.to_thread(bybit_rest_service.session.get_tickers, category="linear", symbol=sol_slot.get('symbol'))
    last_price = float(ticker.get("result", {}).get("list", [{}])[0].get("lastPrice", 0))
    print(f"Current Market Price: {last_price}")
    
    if entry:
        diff = ((last_price - entry) / entry) * 100
        print(f"Calculated Price Move: {diff:.2f}%")
        print(f"Implied PnL (50x): {diff * 50:.2f}%")

if __name__ == "__main__":
    asyncio.run(inspect_sol_slot())
