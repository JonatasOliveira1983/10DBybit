
import json
import time
from services.firebase_service import firebase_service
import asyncio
from firebase_admin import credentials, firestore, initialize_app, _apps

PAPER_FILE = "paper_storage.json"

STATE = {
  "positions": [
    {
      "symbol": "DOGEUSDT",
      "side": "Buy", 
      "size": "500", # Approx $50
      "avgPrice": "0.103700",
      "leverage": "50",
      "stopLoss": "0.105774", # Stop moved up (Trailing)
      "takeProfit": "",
      "createdTime": str(int(time.time() * 1000))
    },
    {
      "symbol": "AAVEUSDT",
      "side": "Sell",
      "size": "0.4", # Approx $50
      "avgPrice": "123.65",
      "leverage": "50",
      "stopLoss": "121.18", # Profit Lock 
      "takeProfit": "",
      "createdTime": str(int(time.time() * 1000))
    }
  ],
  "balance": 100.0,
  "history": []
}

async def restore():
    print("🚑 RESTORING STATE TO PAPER STORAGE...")
    
    # 1. Write JSON
    with open(PAPER_FILE, 'w') as f:
        json.dump(STATE, f, indent=2)
    print("✅ paper_storage.json created.")
    
    # 2. Sync Firebase Matches
    if not _apps:
        cred = credentials.Certificate("serviceAccountKey.json")
        initialize_app(cred)
    db = firestore.client()
    
    # Clean slots 1 & 2
    db.collection("slots").document("1").set({
        "id": 1,
        "symbol": "DOGEUSDT",
        "side": "Buy",
        "size": 500.0,
        "entry_price": 0.103700,
        "current_stop": 0.105774,
        "pnl_percent": -23.0, # Visual Estimate
        "status": "OPEN",
        "slot_type": "SURF",
        "timestamp": int(time.time() * 1000)
    })
    
    db.collection("slots").document("2").set({
        "id": 2,
        "symbol": "AAVEUSDT",
        "side": "Sell",
        "size": 0.4,
        "entry_price": 123.65,
        "current_stop": 121.18,
        "pnl_percent": -25.0, 
        "status": "OPEN",
        "slot_type": "SNIPER",
        "timestamp": int(time.time() * 1000)
    })
    
    print("✅ Firebase Slots 1 & 2 Restored.")
    print(">>> PLEASE RESTART THE BACKEND NOW TO LOAD THE RESTORED STATE <<<")

if __name__ == "__main__":
    asyncio.run(restore())
