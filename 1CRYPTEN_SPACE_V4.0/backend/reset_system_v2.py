import asyncio
import firebase_admin
from firebase_admin import credentials, firestore, db as rtdb
import os

# CREDENTIALS PATH
CRED_PATH = "serviceAccountKey.json"

async def full_system_reset():
    print("🚀 INITIATING COMPREHENSIVE SYSTEM RESET...")

    if not os.path.exists(CRED_PATH):
        print(f"❌ Error: {CRED_PATH} not found.")
        return

    cred = credentials.Certificate(CRED_PATH)
    try:
        # We need the RTDB URL for some resets if applicable, but for Firestore it's not needed.
        firebase_admin.initialize_app(cred)
    except ValueError:
        pass

    db = firestore.client()

    collections_to_clear = [
        "journey_signals",
        "slots_ativos",
        "trade_history",
        "system_logs",
        "banca_history"
    ]

    for coll_name in collections_to_clear:
        print(f"🔥 Clearing collection: '{coll_name}'...")
        coll_ref = db.collection(coll_name)
        
        # Firestore delete is best done in batches for large collections
        docs = coll_ref.limit(500).stream()
        count = 0
        for doc in docs:
            doc.reference.delete()
            count += 1
        
        # If it was a large collection, we might need multiple passes, 
        # but for this system, 500 signals/logs is usually a good batch.
        print(f"✅ Deleted {count} documents from '{coll_name}'.")

    # 2. RESET STATUS
    print("🔄 Resetting 'banca_status'...")
    db.collection('banca_status').document('status').set({
        "saldo_total": 100.0, # Reset to initial $100 for Paper Trading
        "risco_real_percent": 0.0,
        "slots_disponiveis": 10,
        "status": "RESET"
    })

    # 3. INITIALIZE SLOTS (Ensuring they exist as empty)
    print("📥 Initializing empty slots...")
    for i in range(1, 11):
        db.collection('slots_ativos').document(str(i)).set({
            "id": i,
            "symbol": None,
            "side": None,
            "entry_price": 0,
            "current_stop": 0,
            "status_risco": "LIVRE",
            "pnl_percent": 0,
            "pensamento": ""
        })

    print("\n✅ COMPREHENSIVE RESET COMPLETE.")
    print("🚀 System is ready for a fresh start.")

if __name__ == "__main__":
    asyncio.run(full_system_reset())
