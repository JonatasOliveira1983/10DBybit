import asyncio
from services.firebase_service import firebase_service

async def dump_all_slots():
    print("Initializing Firebase...")
    await firebase_service.initialize()
    print("Fetching ALL active slots...")
    slots = await firebase_service.get_active_slots()
    
    print(f"Total Slots Retrieved: {len(slots)}")
    for s in slots:
        print(f"Slot {s.get('id')}: {s.get('symbol')} | Side: {s.get('side')} | Entry: {s.get('entry_price')} | PnL: {s.get('pnl_percent')}")

if __name__ == "__main__":
    asyncio.run(dump_all_slots())
