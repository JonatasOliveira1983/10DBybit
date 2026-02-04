import asyncio
import logging
from services.firebase_service import firebase_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("InspectSlots")

async def main():
    print("Initializing Firebase...")
    await firebase_service.initialize()
    
    print("Fetching active slots...")
    slots = await firebase_service.get_active_slots()
    
    found_issue = False
    for slot in slots:
        print(f"Slot {slot.get('id')}: {slot}")
        # Check for suspicious status
        if "processada" in str(slot).lower() or "snd" in str(slot).lower():
            print(f"!!! SUSPICIOUS SLOT FOUND: {slot.get('id')}")
            found_issue = True

    if not found_issue:
        print("No slot with 'sndprocessada' logic found in current slots.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
