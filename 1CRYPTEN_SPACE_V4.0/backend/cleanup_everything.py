import asyncio
import firebase_admin
from firebase_admin import credentials, firestore
import logging
import os
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Cleanup")

async def cleanup():
    # Load credentials
    cred_path = "serviceAccountKey.json"
    if not os.path.exists(cred_path):
        logger.error("serviceAccountKey.json not found!")
        return

    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        
        db = firestore.client()
        
        # 1. Clear Slots (slots_ativos)
        logger.info("🧹 Resetting slots_ativos...")
        slots_ref = db.collection("slots_ativos")
        for i in range(1, 11):
            slots_ref.document(str(i)).set({
                "id": i,
                "symbol": None,
                "side": None,
                "entry_price": 0,
                "current_stop": 0,
                "status_risco": "LIVRE",
                "pnl_percent": 0,
                "pnl_usd": 0,
                "slot_type": None,
                "pensamento": "🔄 Reset Total para V6.0"
            })
        
        # 2. Delete Signals (journey_signals)
        logger.info("🧹 Deleting journey_signals...")
        signals_ref = db.collection("journey_signals")
        signals = signals_ref.stream()
        count = 0
        for sig in signals:
            sig.reference.delete()
            count += 1
        logger.info(f"Deleted {count} signals.")
        
        # 3. Delete Trade History (trade_history)
        logger.info("🧹 Deleting trade_history...")
        history_ref = db.collection("trade_history")
        history = history_ref.stream()
        count = 0
        for h in history:
            h.reference.delete()
            count += 1
        logger.info(f"Deleted {count} history entries.")

        # 4. Optional: Clear System Logs (system_logs)
        logger.info("🧹 Deleting system_logs...")
        logs_ref = db.collection("system_logs")
        logs = logs_ref.stream()
        count = 0
        for l in logs:
            l.reference.delete()
            count += 1
        logger.info(f"Deleted {count} logs.")

        logger.info("✅ Cleanup Complete!")

    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

if __name__ == "__main__":
    asyncio.run(cleanup())
