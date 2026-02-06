import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
from datetime import datetime

def main():
    cred_path = os.path.join(os.path.dirname(__file__), "serviceAccountKey.json")
    if not firebase_admin._apps:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
    
    db = firestore.client()
    
    print("\n--- Firestore: vault_management/current_cycle ---")
    cycle = db.collection("vault_management").document("current_cycle").get().to_dict()
    print(json.dumps(cycle, indent=2, default=str))
    
    print("\n--- Firestore: slots_ativos ---")
    slots = list(db.collection("slots_ativos").stream())
    slots_data = [s.to_dict() for s in slots]
    print(json.dumps(slots_data, indent=2, default=str))

if __name__ == "__main__":
    main()
