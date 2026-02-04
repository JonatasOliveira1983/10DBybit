import firebase_admin
from firebase_admin import credentials, firestore, db
import os
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ScorchedEarth")

def scorch_earth():
    logger.info("🔥 Starting Scorched Earth Reset V3.0...")
    
    # 1. Initialize Firebase
    cred_path = "serviceAccountKey.json"
    if not os.path.exists(cred_path):
        logger.error("❌ serviceAccountKey.json not found!")
        return
    
    # Load config for RTDB URL
    db_url = None
    if os.path.exists("config.py"):
        try:
            import sys
            sys.path.append(os.getcwd())
            from config import settings
            db_url = settings.FIREBASE_DATABASE_URL
        except Exception as e:
            logger.warning(f"Could not load config.py: {e}")

    cred = credentials.Certificate(cred_path)
    try:
        firebase_admin.get_app()
    except ValueError:
        firebase_admin.initialize_app(cred, {'databaseURL': db_url})
    
    fs = firestore.client()
    
    # --- FIRESTORE RESET ---
    collections_to_wipe = [
        "trade_history",
        "vault_history",
        "system_logs",
        "journey_signals",
        "banca_history"
    ]
    
    for coll in collections_to_wipe:
        logger.info(f"Deleting collection: {coll}")
        docs = fs.collection(coll).stream()
        count = 0
        for doc in docs:
            doc.reference.delete()
            count += 1
        logger.info(f"Done. Deleted {count} documents from {coll}.")

    # Reset Banca Status
    logger.info("Resetting banca_status/status...")
    fs.collection("banca_status").document("status").set({
        "id": "status",
        "saldo_total": 0,
        "risco_real_percent": 0,
        "slots_disponiveis": 10
    })

    # Reset Slots
    logger.info("Resetting slots_ativos (1-10)...")
    for i in range(1, 11):
        fs.collection("slots_ativos").document(str(i)).set({
            "id": i,
            "symbol": None,
            "side": None,
            "entry_price": 0,
            "current_stop": 0,
            "status_risco": "LIVRE",
            "pnl_percent": 0
        })

    # Reset Vault Management
    logger.info("Resetting vault_management/current_cycle...")
    fs.collection("vault_management").document("current_cycle").set({
        "sniper_wins": 0,
        "cycle_number": 1,
        "cycle_profit": 0.0,
        "cycle_losses": 0.0,
        "surf_profit": 0.0,
        "started_at": firestore.SERVER_TIMESTAMP,
        "in_admiral_rest": False,
        "rest_until": None,
        "vault_total": 0.0,
        "cautious_mode": False,
        "min_score_threshold": 75,
        "total_trades_cycle": 0,
        "accumulated_vault": 0.0
    })
    
    # Clear Vault Withdrawals
    logger.info("Clearing vault_management/withdrawals/history...")
    withdrawals = fs.collection("vault_management").document("withdrawals").collection("history").stream()
    for w in withdrawals:
        w.reference.delete()

    # --- RTDB RESET ---
    if db_url:
        logger.info("Clearing RTDB nodes...")
        rtdb = db.reference("/")
        nodes_to_clear = [
            "chat_history",
            "system_pulse",
            "live_slots",
            "market_radar",
            "btc_command_center",
            "ws_command_tower",
            "system_cooldowns"
        ]
        for node in nodes_to_clear:
            rtdb.child(node).delete()
            logger.info(f"Node cleared: {node}")
    
    # --- LOCAL RESET ---
    logger.info("Clearing paper_storage.json...")
    with open("paper_storage.json", "w") as f:
        json.dump({}, f)
    
    logger.info("✨ SCORCHED EARTH COMPLETE. SYSTEM RESET TO V7.0 CLEAN STATE.")

if __name__ == "__main__":
    scorch_earth()
