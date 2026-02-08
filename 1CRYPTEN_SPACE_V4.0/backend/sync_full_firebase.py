"""
SINCRONIZACAO COMPLETA DO FIREBASE - LOCAL -> PRODUCAO
Sincroniza todos os nodes RTDB e collections Firestore
"""
import firebase_admin
from firebase_admin import credentials, db, firestore
import sys
import io
import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

RTDB_URL = "https://projeto-teste-firestore-3b00e-default-rtdb.europe-west1.firebasedatabase.app"

cred = credentials.Certificate("serviceAccountKey.json")
try:
    firebase_admin.get_app()
except ValueError:
    firebase_admin.initialize_app(cred, {'databaseURL': RTDB_URL})

print("=" * 60)
print("SINCRONIZACAO COMPLETA FIREBASE (LOCAL -> PRODUCAO)")
print("=" * 60)

fs = firestore.client()
rtdb = db.reference()

# === 1. SLOTS ===
print("\n[1/6] SINCRONIZANDO SLOTS...")
slots_data = {}
for doc in fs.collection('slots_ativos').stream():
    slot_id = int(doc.id)
    data = doc.to_dict()
    slots_data[slot_id] = data
    symbol = data.get('symbol', 'EMPTY')
    print(f"  Slot {slot_id}: {symbol}")

rtdb.child("slots").set(slots_data)
rtdb.child("live_slots").set(slots_data)
print("  -> RTDB slots + live_slots: OK")

# === 2. BANCA STATUS ===
print("\n[2/6] SINCRONIZANDO BANCA...")
banca_data = {
    "id": "status",
    "saldo_total": 20.0,
    "saldo_real_bybit": 20.0,
    "lucro_ciclo": 0.0,
    "lucro_total_acumulado": 0.0,
    "risco_real_percent": 0.2,
    "slots_disponiveis": 0,  # 2 ocupados = 0 disponiveis
    "vault_total": 0.0
}
rtdb.child("banca_status").set(banca_data)
print(f"  Banca: ${banca_data['saldo_total']}")
print("  -> RTDB banca_status: OK")

# === 3. SYSTEM STATE ===
print("\n[3/6] SINCRONIZANDO SYSTEM STATE...")
system_state = {
    "current": "MONITORING",
    "message": "Monitorando 2/2 posicoes",
    "slots_occupied": 2,
    "updated_at": datetime.datetime.now().timestamp() * 1000
}
rtdb.child("system_state").set(system_state)
print(f"  State: {system_state['current']}")
print("  -> RTDB system_state: OK")

# === 4. SYSTEM PULSE ===
print("\n[4/6] SINCRONIZANDO SYSTEM PULSE...")
pulse = {
    "btc_variation": 0.0,
    "last_update": datetime.datetime.now().isoformat(),
    "status": "ACTIVE",
    "version": "V11.0"
}
rtdb.child("system_pulse").set(pulse)
print("  -> RTDB system_pulse: OK")

# === 5. BTC COMMAND CENTER ===
print("\n[5/6] SINCRONIZANDO BTC COMMAND CENTER...")
btc_center = {
    "btc_1h_change": 0.0,
    "drag_mode": "STANDBY",
    "exhaustion_bar": 0,
    "updated_at": datetime.datetime.now().isoformat()
}
rtdb.child("btc_command_center").set(btc_center)
print(f"  Drag Mode: {btc_center['drag_mode']}")
print("  -> RTDB btc_command_center: OK")

# === 6. WS COMMAND TOWER ===
print("\n[6/6] SINCRONIZANDO WS COMMAND TOWER...")
ws_tower = {
    "connected": True,
    "symbols_monitored": 88,
    "last_ping": datetime.datetime.now().isoformat()
}
rtdb.child("ws_command_tower").set(ws_tower)
print(f"  Symbols: {ws_tower['symbols_monitored']}")
print("  -> RTDB ws_command_tower: OK")

# === LIMPAR DADOS ANTIGOS ===
print("\n[LIMPEZA] Removendo dados antigos...")
rtdb.child("system_cooldowns").set({})
rtdb.child("market_radar").set({})
rtdb.child("chat_history").set({})
print("  -> cooldowns, radar, chat: LIMPO")

print("\n" + "=" * 60)
print("SINCRONIZACAO COMPLETA!")
print("=" * 60)
print(f"  Slots: {len(slots_data)} ativos")
print(f"  Banca: $20.00")
print(f"  System: MONITORING")
print("=" * 60)
