import asyncio
import firebase_admin
from firebase_admin import credentials, firestore
import os
import logging
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ResetSystem")

async def reset_system():
    logger.info("🚀 Starting Full System Reset V5.4.5...")
    
    # 1. Initialize Firebase
    sys.path.append(os.getcwd())
    try:
        from config import settings
        cred_path = settings.FIREBASE_CREDENTIALS_PATH
    except:
        cred_path = "serviceAccountKey.json"

    if not os.path.exists(cred_path):
        logger.error(f"❌ Credentials not found.")
        return

    try:
        firebase_admin.get_app()
    except ValueError:
        firebase_admin.initialize_app(credentials.Certificate(cred_path))

    fs = firestore.client()
    
    # 2. Reset Active Slots (PRIORITY)
    logger.info("🔄 Resetting Active Slots (1-10)...")
    batch = fs.batch()
    for i in range(1, 11):
        doc_ref = fs.collection("slots_ativos").document(str(i))
        batch.set(doc_ref, {
            "id": i,
            "symbol": None,
            "side": None,
            "entry_price": 0,
            "current_stop": 0,
            "status_risco": "LIVRE",
            "pnl_percent": 0,
            "pensamento": "Aguardando sinal..."
        })
    batch.commit()
    logger.info("✅ Slots reset.")

    # 3. Clear Firestore Collections
    collections_to_clear = [
        "trade_history",
        "system_logs",
        "banca_history",
        "journey_signals"
    ]
    
    for coll in collections_to_clear:
        logger.info(f"🗑️ Clearing Firestore collection: {coll}...")
        docs = fs.collection(coll).stream()
        count = 0
        for doc in docs:
            doc.reference.delete()
            count += 1
        logger.info(f"✅ Deleted {count} documents from {coll}")

    # 4. Reset Banca Status
    logger.info("💰 Resetting Banca Status...")
    fs.collection("banca_status").document("status").set({
        "saldo_total": 100.0,
        "risco_real_percent": 0.0,
        "slots_disponiveis": 10
    })
    
    # 5. Local Files
    if os.path.exists("paper_storage.json"):
        os.remove("paper_storage.json")
        logger.info("✅ Deleted local paper_storage.json")

    logger.info("🏁 SYSTEM RESET COMPLETE. READY FOR BOOT.")

if __name__ == "__main__":
    asyncio.run(reset_system())
