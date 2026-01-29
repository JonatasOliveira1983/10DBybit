
import asyncio
import os
import sys

# Add the current directory to path so we can import services
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '1CRYPTEN_SPACE_V4.0/backend')))

from services.firebase_service import firebase_service
from config import settings

async def reset_system():
    print("🚀 Iniciando Reset Total do Sistema...")
    
    # 1. Initialize Firebase
    await firebase_service.initialize()
    if not firebase_service.is_active:
        print("❌ Falha ao conectar ao Firebase. Abortando.")
        return

    db = firebase_service.db
    rtdb = firebase_service.rtdb

    # 2. Clear journey_signals
    print("📡 Limpando Sinais do Radar (Batch Mode)...")
    signals_ref = db.collection("journey_signals")
    while True:
        docs = list(signals_ref.limit(500).stream())
        if not docs: break
        batch = db.batch()
        for doc in docs: batch.delete(doc.reference)
        batch.commit()
    print("✅ Sinais removidos.")

    # 3. Reset Slots
    print("🎰 Resetando Slots de Trading...")
    batch = db.batch()
    for i in range(1, 11):
        slot_ref = db.collection("slots_ativos").document(str(i))
        batch.set(slot_ref, {
            "id": i,
            "symbol": None,
            "side": None,
            "entry_price": 0,
            "current_stop": 0,
            "target_price": 0,
            "slot_type": "SNIPER" if i <= 5 else "SURF",
            "status_risco": "LIVRE",
            "pnl_percent": 0,
            "pensamento": "Sistema reiniciado. Aguardando novos sinais..."
        })
    batch.commit()
    print("✅ 10 slots resetados.")

    # 4. Reset Banca Status
    print("💰 Restaurando Saldo da Banca...")
    await firebase_service.update_banca_status({
        "id": "status",
        "saldo_total": 100.0,
        "risco_real_percent": 0,
        "slots_disponiveis": 10
    })
    print("✅ Saldo resetado para $100.00.")

    # 5. Clear History
    print("📜 Limpando Históricos (Batch Mode)...")
    collections = ["trade_history", "banca_history", "system_logs"]
    for coll in collections:
        coll_ref = db.collection(coll)
        while True:
            docs = list(coll_ref.limit(500).stream())
            if not docs: break
            batch = db.batch()
            for doc in docs: batch.delete(doc.reference)
            batch.commit()
    print("✅ Históricos e logs limpos.")

    # 6. Reset Vault (Realtime DB if used, or local state)
    print("🏦 Resetando Vault Service...")
    # Clean vault state in RTDB
    if rtdb:
        rtdb.child("vault_status").set({
            "cycle_number": 1,
            "sniper_wins": 0,
            "vault_total": 0,
            "in_admiral_rest": False,
            "cautious_mode": False
        })
        rtdb.child("market_radar").delete()
        rtdb.child("chat_history").delete()
        print("✅ Dados do RTDB limpos.")

    # 7. Final Log
    await firebase_service.log_event("System", "RESET TOTAL EXECUTADO: Sistema pronto para nova operação V4.2.3", "SUCCESS")
    print("\n✨ RESET CONCLUÍDO COM SUCESSO! O cockpit está limpo.")

if __name__ == "__main__":
    asyncio.run(reset_system())
