import asyncio
import firebase_admin
from firebase_admin import credentials, firestore, db
import os
import json
import logging
import sys
from datetime import datetime, timezone

# Add current directory to path for imports
sys.path.append(os.getcwd())

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TotalCleanSweep")

async def total_clean_sweep():
    logger.info("🌪️ STARTING TOTAL CLEAN SWEEP & PROTOCOL ALIGNMENT...")
    
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

    # 2. Reset Firestore Collections
    
    # 2.1 Slots Ativos
    logger.info("🔄 Resetting all 10 Slots to LIVRE...")
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
            "pensamento": "🔄 Reset V6.0 - Sistema Limpo",
            "updated_at": datetime.now(timezone.utc).isoformat()
        })
    batch.commit()

    # 2.2 Vault Management
    logger.info("🏦 Resetting Vault to Cycle #1 and $100 Balance...")
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
        "accumulated_vault": 100.0  # Aligned for 5% margin protocol
    })

    # 2.3 Banca Status
    logger.info("💰 Setting Banca Status to $100...")
    fs.collection("banca_status").document("status").set({
        "id": "status",
        "saldo_total": 100.0,
        "risco_real_percent": 0.0,
        "slots_disponiveis": 10,
        "updated_at": datetime.now(timezone.utc).isoformat()
    })

    # 2.4 Cleanup History & Logs
    collections_to_clear = ["journey_signals", "trade_history", "system_logs", "banca_history"]
    for coll in collections_to_clear:
        logger.info(f"🗑️ Clearing Firestore collection: {coll}...")
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
        logger.info(f"✅ {coll}: {count} docs deleted.")

    # 3. Realtime DB Cleanup
    if rtdb:
        logger.info("⚡ Wiping RTDB paths...")
        for path in ["chat_history", "live_slots", "system_pulse", "system_cooldowns", "market_radar"]:
            rtdb.child(path).delete()
            logger.info(f"✅ RTDB path /{path} cleared.")

    # 4. Paper Simulator Forced Overwrite
    logger.info("📝 Overwriting paper_storage.json with $100 balance and 0 positions...")
    paper_data = {
        "positions": [],
        "balance": 100.0,
        "history": []
    }
    with open("paper_storage.json", "w") as f:
        json.dump(paper_data, f, indent=2)
    logger.info("✅ paper_storage.json updated.")

    logger.info("🏁 TOTAL CLEAN SWEEP COMPLETE. Protocol Aligned at $100.")

if __name__ == "__main__":
    asyncio.run(total_clean_sweep())
