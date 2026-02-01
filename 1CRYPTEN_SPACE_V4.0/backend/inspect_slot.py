
import firebase_admin
from firebase_admin import credentials, firestore
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("InspectSlot")

# Initialize Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

def inspect_aave():
    logger.info("🔎 Looking for AAVEUSDT slot...")
    
    slots_ref = db.collection("slots")
    docs = slots_ref.stream()
    
    found = False
    for doc in docs:
        data = doc.to_dict()
        if "AAVE" in data.get("symbol", ""):
            found = True
            print("\n" + "="*40)
            print(f"📌 SLOT {data.get('id')} - {data.get('symbol')}")
            print("="*40)
            print(f"   Side:          {data.get('side')}")
            print(f"   Entry Price:   {data.get('entry_price')}")
            print(f"   Current Price: {data.get('mark_price', 'N/A')}")
            print(f"   Stop Loss:     {data.get('current_stop')}")
            print(f"   ROI:           {data.get('pnl_percent')}%")
            print(f"   Slot Type:     {data.get('slot_type')}")
            print(f"   Status:        {data.get('status')}")
            print("="*40 + "\n")
            
            # Check logic
            entry = float(data.get('entry_price', 0))
            stop = float(data.get('current_stop', 0))
            roi = float(data.get('pnl_percent', 0))
            side = data.get('side', '').lower()
            
            if stop > 0:
                print(f"🔍 ANALYSIS:")
                if side == 'sell': # Short
                    # Stop should be ABOVE entry. Price triggers if ABOVE stop.
                    # Wait, if price is ABOVE stop in Short, it's a loss closure.
                    # Wait, user said "price went up (bad for short) and is above stop loss".
                    # If Price > Stop Loss (in Short), it SHOULD CLOSE.
                    pass
            
    if not found:
        print("❌ AAVEUSDT slot not found!")

if __name__ == "__main__":
    inspect_aave()
