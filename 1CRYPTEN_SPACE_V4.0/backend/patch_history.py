
import asyncio
import logging
from services.firebase_service import firebase_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HistoryPatch")

async def patch_history():
    await firebase_service.initialize()
    
    print("🩹 Starting History Patch...")
    docs = firebase_service.db.collection("trade_history").stream()
    
    count = 0
    for doc in docs:
        data = doc.to_dict()
        if data.get("slot_type") is None:
            print(f"🔧 Patching doc {doc.id} ({data.get('symbol')})...")
            # Default to SNIPER for now as most were SNIPER
            await asyncio.to_thread(doc.reference.update, {"slot_type": "SNIPER"})
            count += 1
            
    print(f"✅ Patched {count} documents.")

if __name__ == "__main__":
    asyncio.run(patch_history())
