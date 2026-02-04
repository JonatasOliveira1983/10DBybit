import firebase_admin
from firebase_admin import credentials, firestore, db
import os
import json
import logging
import asyncio

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ScorchedEarthV8")

def scorch_earth_v8():
    logger.info("🔥 Starting SCORCHED EARTH V8 - Protocolo de Purificação Sniper Evolution...")
    
    # 1. Initialize Firebase
    cred_path = "serviceAccountKey.json"
    if not os.path.exists(cred_path):
        logger.error("❌ serviceAccountKey.json not found! Execute a partir da pasta /backend.")
        return
    
    # Try to load config for RTDB URL
    db_url = None
    try:
        import sys
        sys.path.append(os.getcwd())
        from config import settings
        db_url = settings.FIREBASE_DATABASE_URL
    except Exception as e:
        logger.warning(f"Could not load config.py or settings: {e}")

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
        "banca_history",
        "banca_snapshots"
    ]
    
    for coll in collections_to_wipe:
        logger.info(f"Purging collection: {coll}")
        docs = fs.collection(coll).stream()
        count = 0
        for doc in docs:
            doc.reference.delete()
            count += 1
        logger.info(f"Done. Deleted {count} documents from {coll}.")

    # Reset Banca Status (V8.0)
    logger.info("Resetting banca_status/status...")
    fs.collection("banca_status").document("status").set({
        "id": "status",
        "saldo_total": 0.0,
        "risco_real_percent": 0.0,
        "slots_disponiveis": 1,
        "lucro_total_acumulado": 0.0,
        "lucro_ciclo": 0.0,
        "vault_total": 0.0,
        "status": "ONLINE_CLEAN_V8"
    })

    # Reset Slots (V8.0: ONLY SLOT 1)
    logger.info("Resetting slots_ativos (Only Slot 1)...")
    # Delete all and recreate only 1
    docs = fs.collection("slots_ativos").stream()
    for d in docs: d.reference.delete()
    
    fs.collection("slots_ativos").document("1").set({
        "id": 1,
        "symbol": None,
        "side": None,
        "entry_price": 0,
        "current_stop": 0,
        "status_risco": "IDLE",
        "pnl_percent": 0,
        "slot_type": "SNIPER",
        "timestamp_last_update": 0
    })

    # Reset Vault Management (Cycle #1)
    logger.info("Resetting vault_management/current_cycle...")
    fs.collection("vault_management").document("current_cycle").set({
        "cycle_number": 1,
        "cycle_profit": 0.0,
        "cycle_losses": 0.0,
        "cycle_gains_count": 0,
        "cycle_losses_count": 0,
        "sniper_wins": 0,
        "vault_total": 0.0,
        "accumulated_vault": 0.0,
        "total_trades_cycle": 0,
        "started_at": firestore.SERVER_TIMESTAMP,
        "in_admiral_rest": False,
        "cautious_mode": False,
        "min_score_threshold": 90,
        "sniper_mode_active": False 
    })
    
    # --- RTDB RESET ---
    if db_url:
        logger.info("Clearing Realtime Database nodes...")
        rtdb = db.reference("/")
        nodes_to_clear = [
            "chat_history",
            "system_pulse",
            "live_slots",
            "market_radar",
            "btc_command_center",
            "ws_command_tower",
            "active_instruments"
        ]
        for node in nodes_to_clear:
            rtdb.child(node).delete()
            logger.info(f"Node cleared: {node}")
    
    # --- LOCAL RESET ---
    logger.info("Clearing paper_storage.json...")
    with open("paper_storage.json", "w") as f:
        json.dump({}, f)
    
    logger.info("✨ SCORCHED EARTH V8 COMPLETE. SYSTEM READY FOR SINGLE SNIPER DEPLOYMENT.")

if __name__ == "__main__":
    scorch_earth_v8()
