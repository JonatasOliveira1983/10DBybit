import firebase_admin
from firebase_admin import credentials, firestore, db
import os
import json
import logging
import asyncio

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ScorchedEarthV7")

def scorch_earth_v7():
    logger.info("🔥 Starting SCORCHED EARTH V7 - Protocolo de Purifica\u00e7\u00e3o Total...")
    
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
        api_key = settings.BYBIT_API_KEY
        api_secret = settings.BYBIT_API_SECRET
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

    # Reset Banca Status (V7.0 Fields)
    logger.info("Resetting banca_status/status...")
    fs.collection("banca_status").document("status").set({
        "id": "status",
        "saldo_total": 0.0,
        "risco_real_percent": 0.0,
        "slots_disponiveis": 10,
        "lucro_total_acumulado": 0.0,
        "lucro_ciclo": 0.0,
        "vault_total": 0.0,
        "status": "ONLINE_CLEAN"
    })

    # Reset Slots (V7.0 Sniper Logic)
    logger.info("Resetting slots_ativos (1-10)...")
    for i in range(1, 11):
        fs.collection("slots_ativos").document(str(i)).set({
            "id": i,
            "symbol": None,
            "side": None,
            "entry_price": 0,
            "current_stop": 0,
            "status_risco": "IDLE",
            "pnl_percent": 0,
            "slot_type": "SNIPER" if i <= 5 else "SURF",
            "timestamp_last_update": 0
        })

    # Reset Vault Management (Cycle #1)
    logger.info("Resetting vault_management/current_cycle...")
    fs.collection("vault_management").document("current_cycle").set({
        "cycle_number": 1,
        "cycle_profit": 0.0,
        "cycle_losses": 0.0,
        "cycle_gains_count": 0,    # [V8.0]
        "cycle_losses_count": 0,   # [V8.0]
        "sniper_wins": 0,          # Legacy compatibility
        "surf_profit": 0.0,
        "vault_total": 0.0,
        "accumulated_vault": 0.0,
        "total_trades_cycle": 0,
        "started_at": firestore.SERVER_TIMESTAMP,
        "in_admiral_rest": False,
        "cautious_mode": False,
        "min_score_threshold": 90,  # [V8.0] Strict Sniper Score
        "sniper_mode_active": False # [V8.0] Start paused for safety after reset
    })
    
    # Clear Vault Withdrawals
    logger.info("Clearing vault withdrawal history...")
    withdrawals = fs.collection("vault_management").document("withdrawals").collection("history").stream()
    for w in withdrawals:
        w.reference.delete()

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
            "system_cooldowns",
            "active_instruments"
        ]
        for node in nodes_to_clear:
            rtdb.child(node).delete()
            logger.info(f"Node cleared: {node}")
    
    # --- LOCAL RESET ---
    logger.info("Clearing paper_storage.json...")
    with open("paper_storage.json", "w") as f:
        json.dump({}, f)
    
    # --- BYBIT RESET ---
    logger.info("Protocolo de Reset Bybit (Opcional)...")
    try:
        from pybit.unified_trading import HTTP
        if api_key and api_secret:
            session = HTTP(
                testnet=False,
                api_key=api_key,
                api_secret=api_secret
            )
            logger.info("Bybit Session Initialized. Closing all positions and orders...")
            
            # Cancel all orders
            session.cancel_all_orders(category="linear", settleCoin="USDT")
            logger.info("✅ All USDT pending orders canceled on Bybit.")
            
            # Close positions (Optional: User should handle this manually unless Panic mode is desired)
            logger.info("⚠️ Note: Positions were not closed automatically. Use Panic Button in UI if needed.")
        else:
            logger.warning("Bybit API Keys not found in settings. Skipping Bybit cancelation.")
    except Exception as e:
        logger.error(f"Error during Bybit reset: {e}")

    logger.info("✨ SCORCHED EARTH V7 COMPLETE. SYSTEM READY FOR 50X SNIPER DEPLOYMENT.")

if __name__ == "__main__":
    scorch_earth_v7()
