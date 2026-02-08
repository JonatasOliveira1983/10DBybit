import firebase_admin
from firebase_admin import credentials, db, firestore
import os
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Initialize Firebase with CORRECT RTDB URL (europe-west1)
cred_path = "serviceAccountKey.json"
cred = credentials.Certificate(cred_path)

RTDB_URL = "https://projeto-teste-firestore-3b00e-default-rtdb.europe-west1.firebasedatabase.app"

try:
    firebase_admin.get_app()
except ValueError:
    firebase_admin.initialize_app(cred, {'databaseURL': RTDB_URL})

print("=" * 50)
print("VERIFICACAO DE SINCRONIZACAO FIREBASE")
print("=" * 50)

# Check RTDB
print("\n[REALTIME DATABASE]")
print("-" * 30)

try:
    slots_rtdb = db.reference('slots').get()
    print(f"slots: {slots_rtdb}")
except Exception as e:
    print(f"slots: ERROR - {e}")

try:
    live_slots = db.reference('live_slots').get()
    print(f"live_slots: {live_slots}")
except Exception as e:
    print(f"live_slots: ERROR - {e}")

try:
    banca = db.reference('banca_status').get()
    print(f"banca_status: {banca}")
except Exception as e:
    print(f"banca_status: ERROR - {e}")

try:
    system_state = db.reference('system_state').get()
    print(f"system_state: {system_state}")
except Exception as e:
    print(f"system_state: ERROR - {e}")

# Check Firestore
print("\n[FIRESTORE]")
print("-" * 30)

fs = firestore.client()

print("\nslots_ativos:")
for doc in fs.collection('slots_ativos').stream():
    data = doc.to_dict()
    symbol = data.get('symbol', 'EMPTY')
    entry = data.get('entry_price', 0)
    side = data.get('side', 'N/A')
    print(f"  {doc.id}: {symbol} | Side: {side} | Entry: {entry}")

print("\nvault_management/current_cycle:")
cycle_doc = fs.collection('vault_management').document('current_cycle').get()
if cycle_doc.exists:
    c = cycle_doc.to_dict()
    print(f"  cycle_number: {c.get('cycle_number')}")
    print(f"  used_symbols: {c.get('used_symbols_in_cycle', [])}")
    print(f"  mega_cycle_wins: {c.get('mega_cycle_wins', 0)}")

print("\n" + "=" * 50)
print("VERIFICACAO COMPLETA")
print("=" * 50)
