import firebase_admin
from firebase_admin import credentials, firestore
import os

def check_firestore():
    cred_path = "serviceAccountKey.json"
    if not os.path.exists(cred_path): return
    try:
        firebase_admin.get_app()
    except ValueError:
        firebase_admin.initialize_app(credentials.Certificate(cred_path))

    fs = firestore.client()
    print("📋 CURRENT SLOTS IN FIRESTORE:")
    docs = fs.collection("slots_ativos").stream()
    for doc in docs:
        d = doc.to_dict()
        print(f"Slot {d.get('id')}: {d.get('symbol')} ({d.get('slot_type')})")

if __name__ == "__main__":
    check_firestore()
