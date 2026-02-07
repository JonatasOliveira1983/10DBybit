import asyncio
import firebase_admin
from firebase_admin import credentials, firestore, db
import os
import logging
import io
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ForceClearAll")

# ============================================
# V10.7: CONFIGURAÇÃO DA BANCA INICIAL
# ============================================
INITIAL_BALANCE = 20.0  # Banca inicial em USD
MARGIN_PER_SLOT = 0.10  # 10% por slot = $2.00

# RTDB URL - Europe West 1
RTDB_URL = "https://projeto-teste-firestore-3b00e-default-rtdb.europe-west1.firebasedatabase.app/"

async def main():
    print("=" * 60)
    print("🧹 LIMPEZA COMPLETA DO SISTEMA V10.7 (FIRESTORE + RTDB)")
    print("=" * 60)
    print(f"   Banca Inicial: ${INITIAL_BALANCE:.2f}")
    print(f"   Margem por Slot: {MARGIN_PER_SLOT*100}% = ${INITIAL_BALANCE * MARGIN_PER_SLOT:.2f}")
    print("=" * 60)
    
    cred_path = "serviceAccountKey.json"
    if not os.path.exists(cred_path):
        print("ERROR: serviceAccountKey.json not found")
        return
    
    cred = credentials.Certificate(cred_path)
    try:
        firebase_admin.get_app()
    except ValueError:
        firebase_admin.initialize_app(cred, {'databaseURL': RTDB_URL})
    
    fs = firestore.client()
    rtdb = db.reference("/")
    
    # ============================================
    # PARTE 1: FIRESTORE
    # ============================================
    print("\n" + "=" * 40)
    print("📦 FIRESTORE")
    print("=" * 40)
    
    # [1] Resetar SLOTS no Firestore
    print("\n[1/6] Resetando slots (Firestore)...")
    slot_data_template = {
        "id": 0,
        "symbol": None,
        "side": None,
        "entry_price": 0,
        "current_stop": 0,
        "target_price": None,
        "status_risco": "LIVRE",
        "pnl_percent": 0,
        "slot_type": "SNIPER",
        "timestamp_last_update": 0,
        "visual_status": "IDLE",
        "pensamento": "",
        "qty": 0,
        "entry_margin": 0,
        "current_price": 0,
        "last_guardian_check": 0,
        "status": "IDLE",
        "pnl": 0,
        "liq_price": 0
    }
    
    for i in range(1, 3):
        slot_data = {**slot_data_template, "id": i}
        fs.collection("slots_ativos").document(str(i)).set(slot_data)
        print(f"  ✅ Slot {i} -> LIVRE")
    
    # [2] Resetar Vault/Cycle
    print("\n[2/6] Resetando Vault e Ciclo (Firestore)...")
    vault_data = {
        "cycle_number": 1,
        "cycle_profit": 0.0,
        "cycle_losses": 0.0,
        "cycle_gains_count": 0,
        "cycle_losses_count": 0,
        "sniper_wins": 0,
        "surf_profit": 0.0,
        "vault_total": 0.0,
        "accumulated_vault": 0.0,
        "total_trades_cycle": 0,
        "started_at": firestore.SERVER_TIMESTAMP,
        "in_admiral_rest": False,
        "cautious_mode": False,
        "min_score_threshold": 90,
        "sniper_mode_active": True,
        "used_symbols_in_cycle": [],
        "cycle_bankroll": INITIAL_BALANCE
    }
    fs.collection("vault_management").document("current_cycle").set(vault_data)
    print("  ✅ Vault resetado (Ciclo 1, 0/10 trades)")
    
    # [3] Resetar Banca
    print("\n[3/6] Configurando Banca (Firestore)...")
    banca_data = {
        "id": "status",
        "saldo_total": INITIAL_BALANCE,
        "risco_real_percent": 0.0,
        "slots_disponiveis": 2,
        "lucro_total_acumulado": 0.0,
        "lucro_ciclo": 0.0,
        "vault_total": 0.0,
        "status": "ONLINE",
        "total_trades_cycle": 0,
        "sniper_wins": 0
    }
    fs.collection("banca_status").document("status").set(banca_data)
    print(f"  ✅ Banca: ${INITIAL_BALANCE:.2f}")
    
    # [4] Limpar Sinais
    print("\n[4/6] Limpando sinais do Radar (Firestore)...")
    signals_ref = fs.collection("journey_signals")
    signals = signals_ref.stream()
    deleted_signals = 0
    for doc in signals:
        doc.reference.delete()
        deleted_signals += 1
    print(f"  ✅ {deleted_signals} sinais removidos")
    
    # [5] Limpar Histórico de Trades
    print("\n[5/6] Limpando histórico de trades (Firestore)...")
    history_ref = fs.collection("trade_history")
    trades = history_ref.stream()
    deleted_trades = 0
    for doc in trades:
        doc.reference.delete()
        deleted_trades += 1
    print(f"  ✅ {deleted_trades} trades removidos")
    
    # ============================================
    # PARTE 2: REALTIME DATABASE
    # ============================================
    print("\n" + "=" * 40)
    print("🔥 REALTIME DATABASE")
    print("=" * 40)
    
    # [6] Sincronizar RTDB
    print("\n[6/6] Sincronizando Realtime Database...")
    
    # banca_status no RTDB
    rtdb_banca = {
        "saldo_total": INITIAL_BALANCE,
        "risco_real_percent": 0.0,
        "slots_disponiveis": 2,
        "lucro_total_acumulado": 0.0,
        "lucro_ciclo": 0.0,
        "vault_total": 0.0,
        "status": "ONLINE",
        "total_trades_cycle": 0,
        "sniper_wins": 0,
        "cycle_number": 1,
        "cycle_bankroll": INITIAL_BALANCE
    }
    rtdb.child("banca_status").set(rtdb_banca)
    print("  ✅ RTDB: banca_status")
    
    # slots no RTDB
    rtdb_slots = {}
    for i in range(1, 3):
        rtdb_slots[str(i)] = {
            "id": i,
            "symbol": "",
            "side": "",
            "entry_price": 0,
            "current_stop": 0,
            "target_price": 0,
            "status_risco": "LIVRE",
            "pnl_percent": 0,
            "slot_type": "SNIPER",
            "visual_status": "IDLE",
            "qty": 0,
            "entry_margin": 0,
            "current_price": 0,
            "pnl": 0
        }
    rtdb.child("slots").set(rtdb_slots)
    rtdb.child("live_slots").set(rtdb_slots)
    print("  ✅ RTDB: slots + live_slots")
    
    # system_state no RTDB
    rtdb.child("system_state").set({
        "current": "SCANNING",
        "slots_occupied": 0,
        "message": "Sistema limpo e pronto",
        "updated_at": int(time.time() * 1000)
    })
    print("  ✅ RTDB: system_state")
    
    # system_pulse no RTDB
    rtdb.child("system_pulse").set({
        "timestamp": int(time.time() * 1000),
        "status": "ONLINE",
        "last_heartbeat": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    })
    print("  ✅ RTDB: system_pulse")
    
    # btc_command_center no RTDB
    rtdb.child("btc_command_center").set({
        "btc_drag_mode": False,
        "btc_cvd": 0,
        "exhaustion": 0,
        "timestamp": int(time.time() * 1000)
    })
    print("  ✅ RTDB: btc_command_center")
    
    # ws_command_tower no RTDB
    rtdb.child("ws_command_tower").set({
        "latency_ms": 0,
        "status": "ONLINE",
        "timestamp": int(time.time() * 1000)
    })
    print("  ✅ RTDB: ws_command_tower")
    
    # Limpar cooldowns
    rtdb.child("system_cooldowns").set({})
    print("  ✅ RTDB: system_cooldowns (limpo)")
    
    # Limpar market_radar
    rtdb.child("market_radar").set({})
    print("  ✅ RTDB: market_radar (limpo)")
    
    # Limpar chat_history
    rtdb.child("chat_history").set({})
    print("  ✅ RTDB: chat_history (limpo)")
    
    # ============================================
    # PARTE 3: LOCAL
    # ============================================
    print("\n" + "=" * 40)
    print("💾 LOCAL")
    print("=" * 40)
    
    import json
    with open("paper_storage.json", "w") as f:
        json.dump({
            "positions": [], 
            "balance": INITIAL_BALANCE, 
            "history": []
        }, f, indent=2)
    print(f"  ✅ paper_storage.json (balance: ${INITIAL_BALANCE:.2f})")
    
    # ============================================
    # RESUMO FINAL
    # ============================================
    print("\n" + "=" * 60)
    print("🎉 SISTEMA LIMPO E SINCRONIZADO!")
    print("=" * 60)
    print(f"  💰 Banca: ${INITIAL_BALANCE:.2f}")
    print(f"  📊 Slots: 2 disponíveis (10% = ${INITIAL_BALANCE * MARGIN_PER_SLOT:.2f}/trade)")
    print(f"  🎯 Sinais: {deleted_signals} removidos")
    print(f"  📜 Histórico: {deleted_trades} trades removidos")
    print(f"  🔄 Ciclo: 1 (0/10 trades)")
    print(f"  ☁️ Firestore: ✅ Sincronizado")
    print(f"  🔥 RTDB: ✅ Sincronizado")
    print("=" * 60)
    print("\n⚠️  REINICIE O BACKEND para aplicar as mudanças!")

if __name__ == "__main__":
    asyncio.run(main())