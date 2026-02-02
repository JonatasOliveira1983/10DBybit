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
logger = logging.getLogger("ScorchedEarthV2")

async def scorched_earth_v2():
    logger.info("🔥 STARTING SCORCHED EARTH V2 - SYSTEM ANNIHILATION...")
    
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

    # 3. Firestore Purge
    logger.info("🗑️ Purging Firestore Collections...")
    collections = [
        "slots_ativos", "journey_signals", "trade_history", 
        "system_logs", "banca_history", "vault_management",
        "banca_status", "system_status"
    ]
    
    for coll in collections:
        logger.info(f"   Deleting {coll}...")
        docs = fs.collection(coll).stream()
        count = 0
        batch = fs.batch()
        for doc in docs:
            batch.delete(doc.reference)
            count += 1
            if count % 400 == 0:
                batch.commit()
                batch = fs.batch()
        batch.commit()
        logger.info(f"   ✅ {coll}: {count} docs deleted.")

    # 4. Initialize Core Docs
    logger.info("🏗️ Initializing Clean Core Documents...")
    
    # 4.1 Slots
    batch = fs.batch()
    for i in range(1, 11):
        slot_type = "SURF" if i <= 5 else "SNIPER"
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
            "slot_type": slot_type,
            "pensamento": "🔄 Reset V6.0 SURF-FIRST",
            "updated_at": datetime.now(timezone.utc).isoformat()
        })
    batch.commit()

    # 4.2 Vault
    fs.collection("vault_management").document("current_cycle").set({
        "sniper_wins": 0,
        "cycle_number": 1,
        "cycle_profit": 0.0,
        "cycle_losses": 0.0,
        "surf_profit": 0.0,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "vault_total": 0.0,
        "accumulated_vault": 100.0,
        "cautious_mode": False
    })

    # 4.3 Banca
    fs.collection("banca_status").document("status").set({
        "id": "status",
        "saldo_total": 100.0,
        "risco_real_percent": 0.0,
        "slots_disponiveis": 10,
        "lucro_total_acumulado": 0.0,
        "lucro_ciclo": 0.0,
        "vault_total": 0.0,
        "updated_at": datetime.now(timezone.utc).isoformat()
    })

    # 5. RTDB Purge
    if rtdb:
        logger.info("⚡ Wiping RTDB...")
        rtdb.delete() # Full wipe of entire tree
        logger.info("   ✅ RTDB fully annihilated.")

    # 6. Local State Annihilation
    logger.info("📂 Cleaning Local Files...")
    
    # Paper Storage
    with open("paper_storage.json", "w") as f:
        json.dump({"positions": [], "balance": 100.0, "history": []}, f, indent=2)
    logger.info("   ✅ paper_storage.json reset.")

    # Logs Directory
    log_dir = "logs"
    if os.path.exists(log_dir):
        shutil.rmtree(log_dir)
        os.makedirs(log_dir)
        logger.info("   ✅ Logs directory cleared.")

    logger.info("🏁 SCORCHED EARTH V2 COMPLETE. System is now PURE.")

if __name__ == "__main__":
    asyncio.run(scorched_earth_v2())
