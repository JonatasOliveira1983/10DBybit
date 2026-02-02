import asyncio
import logging
from services.firebase_service import firebase_service
import os
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DeepDebug")

async def verify_system_state():
    await firebase_service.initialize()
    if not firebase_service.db:
        print("❌ Firebase DB not initialized.")
        return

    collections = ["slots_ativos", "trade_history", "journey_signals", "banca_status", "vault_management", "signals", "slots"]
    
    print("\n--- FIREBASE STATE CHECK ---")
    for coll_name in collections:
        try:
            # We use a small limit to avoid timeouts if something is still huge
            docs = list(firebase_service.db.collection(coll_name).limit(10).stream())
            print(f"Collection '{coll_name}': {len(docs)} documents found (checked first 10).")
            for doc in docs:
                print(f"  [{doc.id}]: {json.dumps(doc.to_dict(), indent=2)[:200]}...")
        except Exception as e:
            print(f"Collection '{coll_name}': ERROR - {e}")

    print("\n--- LOCAL FILE STATE CHECK ---")
    files_to_check = [
        "paper_storage.json",
        "1CRYPTEN_SPACE_V4.0/backend/paper_storage.json",
        "1CRYPTEN_SPACE_V4.0/backend/services/agents/paper_storage.json",
        "services/paper_storage.json"
    ]
    for f in files_to_check:
        full_path = f # assuming cwd is backend or similar
        print(f"File '{f}': {'EXISTS' if os.path.exists(f) else 'NOT FOUND'}")
        if os.path.exists(f):
             with open(f, 'r') as content:
                 try:
                     data = json.load(content)
                     print(f"  Positions: {len(data.get('positions', []))}")
                     print(f"  History: {len(data.get('history', []))}")
                 except:
                     print("  Error reading/parsing file.")

if __name__ == "__main__":
    asyncio.run(verify_system_state())
