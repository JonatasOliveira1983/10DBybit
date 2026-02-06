
import asyncio
from services.bybit_rest import bybit_rest_service
from services.firebase_service import firebase_service
import json

async def verify_sl():
    print("--- Checking Bybit Positions ---")
    positions = await bybit_rest_service.get_active_positions()
    if not positions:
        print("No active positions on Bybit.")
    else:
        print(json.dumps(positions, indent=2))

    print("\n--- Checking Firestore Slots ---")
    slots = await firebase_service.get_active_slots()
    if not slots:
        print("No active slots in Firestore.")
    else:
        for s in slots:
            if s.get('symbol'):
                 print(f"Slot {s.get('id')}: {s.get('symbol')} | Entry: {s.get('entry_price')} | SL: {s.get('current_stop')} | Side: {s.get('side')}")

if __name__ == "__main__":
    asyncio.run(verify_sl())
