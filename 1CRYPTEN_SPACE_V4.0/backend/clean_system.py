import asyncio
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize (Standalone)
cred = credentials.Certificate("serviceAccountKey.json")
try:
    firebase_admin.get_app()
except ValueError:
    firebase_admin.initialize_app(cred)

db = firestore.client()

async def delete_collection(coll_ref, batch_size=50):
    docs = coll_ref.limit(batch_size).stream()
    deleted = 0

    for doc in docs:
        print(f'Deleting doc {doc.id} => {doc.to_dict()}')
        doc.reference.delete()
        deleted += 1

    if deleted >= batch_size:
        return await delete_collection(coll_ref, batch_size)

def clean_system():
    print("🧹 Cleaning System Data...")
    
    # 1. Clean Slots
    print("   └─ Cleaning 'slots_ativos'...")
    slots_ref = db.collection('slots_ativos')
    docs = slots_ref.stream()
    for doc in docs:
        doc.reference.delete()
    print("      ✅ Slots cleared.")

    # 2. Clean Signals
    print("   └─ Cleaning 'journey_signals'...")
    signals_ref = db.collection('journey_signals')
    docs = signals_ref.stream()
    for doc in docs:
        doc.reference.delete()
    print("      ✅ Signals cleared.")
    
    # 3. Clean Logs (Optional but good for fresh start)
    # print("   └─ Cleaning 'system_logs'...")
    # logs_ref = db.collection('system_logs')
    # docs = logs_ref.stream()
    # for doc in docs:
    #     doc.reference.delete()
    
    print("✨ System Cleaned Successfully.")

if __name__ == "__main__":
    clean_system()
