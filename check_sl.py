import asyncio
import os
import sys

# Add backend to path
backend_path = os.path.join(os.getcwd(), '1CRYPTEN_SPACE_V4.0', 'backend')
if os.path.exists(backend_path):
    os.chdir(backend_path)
    sys.path.append('.')
else:
    sys.path.append('.')

from services.firebase_service import firebase_service

async def verify():
    await firebase_service.initialize()
    slots = await firebase_service.get_active_slots()
    print("--- ACTIVE SLOTS ---")
    for s in slots:
        if s.get("symbol"):
            entry = s.get("entry_price", 0)
            stop = s.get("current_stop", 0)
            if entry > 0:
                dist = abs(stop - entry) / entry * 100
                print(f"Slot {s['id']}: {s['symbol']} | Entry: {entry} | Stop: {stop} | Dist: {dist:.2f}%")
        else:
            print(f"Slot {s['id']}: Empty")

if __name__ == "__main__":
    asyncio.run(verify())
