
import asyncio
import logging
from services.firebase_service import firebase_service

logging.basicConfig(level=logging.INFO)

async def view_history():
    await firebase_service.initialize()
    
    print("🔍 Fetching ALL trade_history documents...")
    docs = firebase_service.db.collection("trade_history").stream()
    
    count = 0
    for doc in docs:
        count += 1
        data = doc.to_dict()
        print(f"📄 Doc ID: {doc.id}")
        print(f"   Symbol: {data.get('symbol')}")
        print(f"   Slot Type: {data.get('slot_type')}")
        print(f"   PnL: {data.get('pnl')}")
        print(f"   Timestamp: {data.get('timestamp')}")
        print("-" * 30)
        
    print(f"Total documents found: {count}")

if __name__ == "__main__":
    asyncio.run(view_history())
