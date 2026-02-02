import asyncio
import logging
from services.firebase_service import firebase_service
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ForceReset")

async def force_reset_everything():
    await firebase_service.initialize()
    if not firebase_service.db:
        print("❌ Firebase DB not initialized.")
        return

    # More exhaustive list of collections based on typical 1CRYPTEN versions
    collections_to_wipe = [
        "trade_history", 
        "journey_signals", 
        "banca_history", 
        "signals", 
        "slots", 
        "slots_ativos", 
        "logs", 
        "system_events",
        "banca_status",
        "vault_management"
    ]
    
    for coll_name in collections_to_wipe:
        print(f"🧹 Wiping collection: {coll_name}...")
        try:
            # Delete in larger batches
            ref = firebase_service.db.collection(coll_name)
            deleted = 0
            while True:
                docs = list(ref.limit(500).stream())
                if not docs:
                    break
                batch = firebase_service.db.batch()
                for doc in docs:
                    batch.delete(doc.reference)
                batch.commit()
                deleted += len(docs)
                print(f"  Deleted {deleted} docs from {coll_name}...")
            print(f"✅ Total {deleted} docs deleted from {coll_name}.")
        except Exception as e:
            print(f"❌ Error wiping {coll_name}: {e}")

    # Explicitly clear cycle status if vault_management is a flat document structure
    try:
        print("💎 Resetting Vault Cycle...")
        firebase_service.db.collection("vault_management").document("current_cycle").delete()
        print("✅ Current cycle document deleted.")
    except Exception as e:
        print(f"❌ Error deleting cycle: {e}")

if __name__ == "__main__":
    asyncio.run(force_reset_everything())
