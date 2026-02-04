import asyncio
import firebase_admin
from firebase_admin import credentials, firestore, db
import os
import logging
import io
import sys
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ForceClearSlot1")

async def main():
    print("LIMPANDO FORÇADAMENTE SLOT 1")
    
    cred_path = "serviceAccountKey.json"
    if not os.path.exists(cred_path):
        print("ERROR: serviceAccountKey.json not found")
        return
    
    cred = credentials.Certificate(cred_path)
    try:
        firebase_admin.get_app()
    except ValueError:
        firebase_admin.initialize_app(cred)
    
    fs = firestore.client()
    
    # Limpar Slot 1 completamente
    print("Resetando Slot 1 para IDLE...")
    fs.collection("slots_ativos").document("1").set({
        "id": 1,
        "symbol": None,
        "side": None,
        "entry_price": 0,
        "current_stop": 0,
        "target_price": None,
        "status_risco": "IDLE",
        "pnl_percent": 0,
        "slot_type": "SNIPER",
        "timestamp_last_update": 0,
        "visual_status": "IDLE",
        "pensamento": "",
        "qty": 0,
        "entry_margin": 0,
        "current_price": 0,
        "last_guardian_check": 0
    })
    
    # Limpar paper_storage
    print("Limpando paper_storage...")
    with open("paper_storage.json", "w") as f:
        json.dump({"positions": [], "balance": 0.0, "history": []}, f)
    
    print("Slot 1 limpo! Backend deve ser reiniciado.")

if __name__ == "__main__":
    asyncio.run(main())