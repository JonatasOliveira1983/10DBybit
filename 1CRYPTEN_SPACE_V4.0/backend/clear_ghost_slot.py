import asyncio
import logging
import sys
import io
from services.firebase_service import firebase_service

# Force UTF-8 for stdout/stderr to handle emojis on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ClearGhost")

async def main():
    print("Initializing Firebase...")
    await firebase_service.initialize()
    
    print("Scanning for ghost slots...")
    slots = await firebase_service.get_active_slots()
    
    processed_count = 0
    for slot in slots:
        slot_id = slot.get('id')
        
        # Safely print slot info
        try:
            print(f"Checking Slot {slot_id}...")
        except Exception:
            print(f"Checking Slot {slot_id} (unicode error avoided)...")

        # Check specifically for the reported issue "sndprocessada" or similar
        s_str = str(slot).lower()
        if "processada" in s_str or "snd" in s_str:
            print(f"!!! FOUND GHOST SLOT: {slot_id} - Clearing...")
            await firebase_service.hard_reset_slot(slot_id, "GHOST_CLEAR_CMD", 0.0)
            processed_count += 1
            
    if processed_count == 0:
        print("No obvious ghost slots found by string match.")
        
    print("Done.")

if __name__ == "__main__":
    asyncio.run(main())
