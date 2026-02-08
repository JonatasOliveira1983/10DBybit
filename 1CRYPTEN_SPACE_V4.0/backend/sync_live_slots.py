"""
Sincroniza live_slots do RTDB com os dados atuais do Firestore.
"""
import firebase_admin
from firebase_admin import credentials, db, firestore
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

RTDB_URL = "https://projeto-teste-firestore-3b00e-default-rtdb.europe-west1.firebasedatabase.app"

cred = credentials.Certificate("serviceAccountKey.json")
try:
    firebase_admin.get_app()
except ValueError:
    firebase_admin.initialize_app(cred, {'databaseURL': RTDB_URL})

print("=" * 50)
print("SINCRONIZANDO LIVE_SLOTS")
print("=" * 50)

# Get Firestore slots
fs = firestore.client()
rtdb = db.reference()

slots_data = {}
for doc in fs.collection('slots_ativos').stream():
    slot_id = int(doc.id)
    data = doc.to_dict()
    slots_data[slot_id] = data
    symbol = data.get('symbol', 'EMPTY')
    print(f"  Slot {slot_id}: {symbol}")

# Update both 'slots' and 'live_slots' in RTDB
print("\nAtualizando RTDB...")

rtdb.child("slots").set(slots_data)
print("  -> slots: OK")

rtdb.child("live_slots").set(slots_data)
print("  -> live_slots: OK")

print("\n" + "=" * 50)
print("SINCRONIZACAO COMPLETA!")
print("=" * 50)
