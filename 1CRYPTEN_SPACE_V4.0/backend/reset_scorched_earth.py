import asyncio
import firebase_admin
from firebase_admin import credentials, firestore, db
import os
import logging
import sys
from datetime import datetime, timezone

# Add current directory to path for imports
sys.path.append(os.getcwd())

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ScorchedEarthReset")

async def reset_scorched_earth():
    logger.info("🔥 STARTING SCORCHED EARTH RESET V6.0...")
    
    # 1. Initialize Firebase
    try:
        from config import settings
        cred_path = settings.FIREBASE_CREDENTIALS_PATH
    except:
        cred_path = "serviceAccountKey.json"

    if not os.path.exists(cred_path):
        logger.error(f"❌ Credentials not found at {cred_path}")
        return

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

    # 2. Reset Active Slots (slots_ativos)
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
            "pnl_usd": 0,
            "slot_type": None,
            "pensamento": "🔄 Reset Total para V6.0 - Disponível",
            "updated_at": datetime.now(timezone.utc).isoformat()
        })
    batch.commit()
    logger.info("✅ Slots reset.")

    # 3. Reset Vault Management (current_cycle)
    logger.info("🏦 Resetting Vault Cycle to #1...")
    vault_ref = fs.collection("vault_management").document("current_cycle")
    vault_ref.set({
        "sniper_wins": 0,
        "cycle_number": 1,
        "cycle_profit": 0.0,
        "cycle_losses": 0.0,
        "surf_profit": 0.0,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "in_admiral_rest": False,
        "rest_until": None,
        "vault_total": 0.0,
        "cautious_mode": False,
        "min_score_threshold": 75,
        "total_trades_cycle": 0,
        "accumulated_vault": 0.0
    })
    logger.info("✅ Vault Cycle Reset.")

    # 4. Clear Firestore History & Logs
    collections_to_clear = [
        "journey_signals",
        "trade_history",
        "system_logs",
        "banca_history"
    ]
    
    for coll in collections_to_clear:
        logger.info(f"🗑️ Clearing Firestore collection: {coll}...")
        docs = fs.collection(coll).stream()
        count = 0
        batch = fs.batch()
        batch_count = 0
        
        for doc in docs:
            batch.delete(doc.reference)
            count += 1
            batch_count += 1
            if batch_count >= 400: # Firestore batch limit is 500
                batch.commit()
                batch = fs.batch()
                batch_count = 0
        
        if batch_count > 0:
            batch.commit()
        logger.info(f"✅ Deleted {count} documents from {coll}")

    # 5. Reset Banca Status
    logger.info("💰 Resetting Banca Status...")
    fs.collection("banca_status").document("status").set({
        "id": "status",
        "saldo_total": 0.0, # User reported $30.42 but request implies a clean wipe.
        "risco_real_percent": 0.0,
        "slots_disponiveis": 10,
        "updated_at": datetime.now(timezone.utc).isoformat()
    })
    logger.info("✅ Banca Status reset.")

    # 6. Realtime DB Cleanup
    if rtdb:
        logger.info("⚡ Cleaning up Realtime Database (RTDB)...")
        rtdb_paths = ["chat_history", "live_slots", "system_pulse", "system_cooldowns", "market_radar"]
        for path in rtdb_paths:
            rtdb.child(path).delete()
            logger.info(f"✅ Deleted RTDB path: /{path}")

    # 7. Local File Cleanup
    if os.path.exists("paper_storage.json"):
        os.remove("paper_storage.json")
        logger.info("✅ Deleted local paper_storage.json")

    logger.info("🏁 SCORCHED EARTH RESET COMPLETE! SYSTEM IS CLEAN.")

if __name__ == "__main__":
    asyncio.run(reset_scorched_earth())
