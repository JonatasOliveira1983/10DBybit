
import asyncio
import sys
import os

# Add parent directory to sys.path to find services
sys.path.append(os.getcwd())

from services.firebase_service import firebase_service

async def check_all_slots():
    await firebase_service.initialize_db()
    slots = await firebase_service.get_active_slots()
    active = [s for s in slots if s.get('symbol')]
    print("--- ALL ACTIVE SLOTS ---")
    for s in active:
        print(f"ID: {s.get('id')}, Symbol: {s.get('symbol')}, Type: {s.get('slot_type')}, ROI: {s.get('pnl_percent')}%")
    print("------------------------")

if __name__ == "__main__":
    asyncio.run(check_all_slots())
