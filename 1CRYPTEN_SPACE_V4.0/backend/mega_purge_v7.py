import asyncio
import firebase_admin
from firebase_admin import credentials, firestore, db
import os
import json
import logging
import sys
import shutil
from datetime import datetime, timezone

# Add current directory to path for imports
sys.path.append(os.getcwd())

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MegaPurgeV7")

async def delete_collection(db, collection_ref, batch_size=400):
    """Recursively deletes a collection and its subcollections."""
    docs = collection_ref.limit(batch_size).get()
    deleted = 0

    for doc in docs:
        # 1. Recursively delete subcollections
        for sub_coll in doc.reference.collections():
            await delete_collection(db, sub_coll, batch_size)
        
        # 2. Delete the document itself
        doc.reference.delete()
        deleted += 1

    if deleted >= batch_size:
        return await delete_collection(db, collection_ref, batch_size)
    return deleted

async def mega_purge_v7():
    logger.info("💥 INITIATING MEGA PURGE V7.0 - SYSTEM TOTAL ANNIHILATION...")
    
    # 1. Credentials
    try:
        from config import settings
        cred_path = settings.FIREBASE_CREDENTIALS_PATH
    except:
        cred_path = "serviceAccountKey.json"

    if not os.path.exists(cred_path):
        logger.error(f"❌ Credentials not found at {cred_path}")
        return

    # 2. Firebase Initialization
    try:
        firebase_admin.get_app()
    except ValueError:
        options = {}
        try:
            from config import settings
            db_url = getattr(settings, 'FIREBASE_DATABASE_URL', None)
            if db_url:
                options['databaseURL'] = db_url
        except:
            pass
        firebase_admin.initialize_app(credentials.Certificate(cred_path), options)

    fs = firestore.client()
    try:
        rtdb = db.reference("/")
    except Exception as e:
        logger.warning(f"⚠️ Realtime DB not available: {e}")
        rtdb = None

    # 3. Firestore Recursive Purge
    logger.info("🗑️ Recursively Purging ALL Firestore Collections...")
    collections_to_wipe = [
        "slots_ativos", "journey_signals", "trade_history", 
        "system_logs", "banca_history", "vault_management",
        "banca_status", "system_status"
    ]
    
    for coll_name in collections_to_wipe:
        logger.info(f"   🔥 Deep cleaning collection: {coll_name}...")
        coll_ref = fs.collection(coll_name)
        deleted_count = await delete_collection(fs, coll_ref)
        logger.info(f"   ✅ {coll_name}: Purged.")

    # 4. Initialize Clean Core Documents for V7.0 SNIPER
    logger.info("🏗️ Initializing Clean V7.0 SNIPER Protocol...")
    
    # 4.1 Slots - All as SNIPER, focusing on Slot 1
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
            "pnl_usd": 0,
            "slot_type": "SNIPER",
            "pensamento": "🔄 Sniper V7.0 Neutral Ground",
            "updated_at": datetime.now(timezone.utc).isoformat()
        })
    batch.commit()

    # 4.2 Vault - V7.0 Alignment
    fs.collection("vault_management").document("current_cycle").set({
        "sniper_wins": 0,
        "cycle_number": 1,
        "total_trades_cycle": 0,
        "cycle_profit": 0.0,
        "cycle_losses": 0.0,
        "surf_profit": 0.0,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "vault_total": 0.0,
        "accumulated_vault": 100.0,
        "cautious_mode": False
    })

    # 4.3 Banca - V7.0 Alignment
    fs.collection("banca_status").document("status").set({
        "id": "status",
        "saldo_total": 100.0,
        "risco_real_percent": 0.0,
        "slots_disponiveis": 1, 
        "total_trades_cycle": 0,
        "lucro_total_acumulado": 0.0,
        "lucro_ciclo": 0.0,
        "vault_total": 0.0,
        "updated_at": datetime.now(timezone.utc).isoformat()
    })

    # 5. RTDB Purge
    if rtdb:
        logger.info("⚡ Wiping Realtime Database...")
        rtdb.delete() 
        logger.info("   ✅ RTDB Annihilated.")

    # 6. Local State Annihilation
    logger.info("📂 Cleaning Local Manifests...")
    
    if os.path.exists("paper_storage.json"):
        with open("paper_storage.json", "w") as f:
            json.dump({"positions": [], "balance": 100.0, "history": []}, f, indent=2)
        logger.info("   ✅ paper_storage.json reset.")

    # Logs Directory
    log_dir = "logs"
    if os.path.exists(log_dir):
        shutil.rmtree(log_dir)
        os.makedirs(log_dir)
        logger.info("   ✅ Logs directory cleared.")

    logger.info("🏁 MEGA PURGE V7.0 COMPLETE. System is pure.")

if __name__ == "__main__":
    asyncio.run(mega_purge_v7())
