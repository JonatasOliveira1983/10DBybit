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

async def nuke_system():
    print("☢️ INITIATING SYSTEM RESET (NUCLEAR OPTION)...")

    # 1. DELETE ALL SIGNALS
    print("🔥 Incinerating 'journey_signals'...")
    signals_ref = db.collection('journey_signals')
    docs = signals_ref.limit(100).stream() # Delete in batches
    count = 0
    for doc in docs:
        doc.reference.delete()
        count += 1
    print(f"✅ Vaporized {count} signals.")

    # 2. DELETE ALL ACTIVE SLOTS
    print("🔥 Incinerating 'slots_ativos'...")
    slots_ref = db.collection('slots_ativos')
    docs = slots_ref.stream()
    count = 0
    for doc in docs:
        doc.reference.delete()
        count += 1
    print(f"✅ Vaporized {count} active slots.")

    # 3. RESET STATUS
    print("🔄 Resetting 'banca_status'...")
    db.collection('banca_status').document('status').set({
        "saldo_total": 0,
        "risco_real_percent": 0,
        "slots_disponiveis": 10,
        "last_reset": firestore.SERVER_TIMESTAMP
    })
    
    print("✅ SYSTEM RESET COMPLETE. READY FOR REBOOT.")

if __name__ == "__main__":
    asyncio.run(nuke_system())
