import asyncio
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize (Standalone)
cred = credentials.Certificate("serviceAccountKey.json")
try:
    firebase_admin.initialize_app(cred)
except ValueError:
    pass

db = firestore.client()

def clean_slots():
    print("🧹 Cleaning 'slots_ativos' collection...")
    slots_ref = db.collection('slots_ativos')
    docs = slots_ref.stream()
    count = 0
    for doc in docs:
        doc.reference.delete()
        count += 1
    print(f"✅ Deleted {count} active slots.")

if __name__ == "__main__":
    clean_slots()
