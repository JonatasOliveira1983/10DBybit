import asyncio
import logging
import sys
import io
import json
from services.firebase_service import firebase_service

# Force UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger("InspectTop")

async def main():
    print("Initializing Firebase...")
    await firebase_service.initialize()
    
    print("Fetching active slots...")
    slots = await firebase_service.get_active_slots()
    
    # Filter for slots 1-5
    top_slots = [s for s in slots if s.get('id') <= 5]
    
    print("--- TOP SLOTS REPORT ---")
    for slot in top_slots:
        print(f"SLOT {slot.get('id')}:")
        print(json.dumps(slot, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())
