
import firebase_admin
from firebase_admin import credentials, firestore
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PatchSlots")

# Initialize Firebase
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

def patch_slots():
    logger.info("🔎 Scanning active slots for missing slot_type...")
    
    slots_ref = db.collection("slots")
    docs = slots_ref.stream()
    
    count = 0
    updated = 0
    
    for doc in docs:
        count += 1
        data = doc.to_dict()
        slot_id = data.get("id")
        current_type = data.get("slot_type")
        
        if current_type is None:
            # Determine type based on ID
            # 1-5 = SNIPER, 6-10 = SURF
            new_type = "SNIPER" if slot_id <= 5 else "SURF"
            
            logger.info(f"🔧 Patching Slot {slot_id} ({data.get('symbol')}): None -> {new_type}")
            
            slots_ref.document(doc.id).update({"slot_type": new_type})
            updated += 1
        else:
            logger.info(f"✅ Slot {slot_id} ({data.get('symbol')}) already has type: {current_type}")

    logger.info(f"✨ Done. Scanned {count} slots. Patched {updated} slots.")

if __name__ == "__main__":
    patch_slots()
