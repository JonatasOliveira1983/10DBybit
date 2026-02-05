"""
V10.4 Script: Initialize Slot 2 for Dual Sniper System
"""
import asyncio
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase
cred = credentials.Certificate("serviceAccountKey.json")
try:
    firebase_admin.get_app()
except:
    firebase_admin.initialize_app(cred)

db = firestore.client()

def create_slot_2():
    """Creates Slot 2 in Firebase if it doesn't exist."""
    slot_ref = db.collection("slots_ativos").document("2")
    slot_doc = slot_ref.get()
    
    if slot_doc.exists:
        print(f"Slot 2 already exists: {slot_doc.to_dict()}")
        # Clear it if it has stale data
        current = slot_doc.to_dict()
        if current.get("symbol"):
            print(f"Clearing stale data from Slot 2...")
            slot_ref.set({
                "id": 2,
                "symbol": None,
                "side": None,
                "entry_price": 0,
                "current_stop": 0,
                "status_risco": "LIVRE",
                "pnl_percent": 0
            })
            print("Slot 2 cleared!")
    else:
        print("Creating Slot 2...")
        slot_ref.set({
            "id": 2,
            "symbol": None,
            "side": None,
            "entry_price": 0,
            "current_stop": 0,
            "status_risco": "LIVRE",
            "pnl_percent": 0
        })
        print("Slot 2 created successfully!")
    
    # Verify
    print("\nAll slots in Firebase:")
    slots = db.collection("slots_ativos").order_by("id").stream()
    for s in slots:
        data = s.to_dict()
        print(f"  Slot {data.get('id')}: {data.get('symbol') or 'EMPTY'}")

if __name__ == "__main__":
    create_slot_2()
