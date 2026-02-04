import asyncio
import logging
import sys
import io
from services.firebase_service import firebase_service

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ForceClear")

async def main():
    print("Initializing Firebase...")
    await firebase_service.initialize()
    
    # Force reset Slot 1
    print("Force clearing Slot 1...")
    await firebase_service.hard_reset_slot(1, "MANUAL_FIX_ZOMBIE_STATE", 0.0)
    
    # Verify
    print("Verifying...")
    slot = await firebase_service.get_slot(1)
    print(f"Slot 1 State: {slot}")

if __name__ == "__main__":
    asyncio.run(main())
