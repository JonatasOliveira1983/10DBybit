import asyncio
import logging
import sys
import io
import json
from services.firebase_service import firebase_service

# Force UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

logging.basicConfig(level=logging.ERROR) # Only show errors to keep output clean
logger = logging.getLogger("InspectV2")

async def main():
    print("Initializing Firebase...")
    await firebase_service.initialize()
    
    print("Fetching active slots...")
    slots = await firebase_service.get_active_slots()
    
    print("--- SLOTS REPORT ---")
    has_active = False
    for slot in slots:
        # Check if slot is "active" (has a symbol) or has ANY content that isn't default
        is_empty = (slot.get('symbol') is None) and (slot.get('status_risco') == 'LIVRE')
        
        if not is_empty or slot.get('id') == 1: # Always show Slot 1
            print(f"SLOT {slot.get('id')}:")
            print(json.dumps(slot, indent=2, ensure_ascii=False))
            has_active = True
            
            if slot.get('symbol'):
                has_active = True

    if not has_active:
        print("All slots appear to be empty/LIVRE.")

if __name__ == "__main__":
    asyncio.run(main())
