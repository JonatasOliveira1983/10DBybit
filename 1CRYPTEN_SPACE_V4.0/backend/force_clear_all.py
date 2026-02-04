import asyncio
import firebase_admin
from firebase_admin import credentials, firestore, db
import os
import logging
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ForceClearAll")

async def main():
    print("=" * 50)
    print("LIMPANDO TODOS OS SLOTS E RESETANDO SISTEMA")
    print("=" * 50)
    
    cred_path = "serviceAccountKey.json"
    if not os.path.exists(cred_path):
        print("ERROR: serviceAccountKey.json not found")
        return
    
    cred = credentials.Certificate(cred_path)
    try:
        firebase_admin.get_app()
    except ValueError:
        firebase_admin.initialize_app(cred)
    
    fs = firestore.client()
    
    # Resetar todos os slots para estado IDLE
    print("\n[1/3] Resetando slots (1-10)...")
    for i in range(1, 11):
        fs.collection("slots_ativos").document(str(i)).set({
            "id": i,
            "symbol": None,
            "side": None,
            "entry_price": 0,
            "current_stop": 0,
            "target_price": None,
            "status_risco": "IDLE",
            "pnl_percent": 0,
            "slot_type": "SNIPER" if i <= 5 else "SURF",
            "timestamp_last_update": 0,
            "visual_status": "IDLE",
            "pensamento": "",
            "qty": 0,
            "entry_margin": 0,
            "current_price": 0,
            "last_guardian_check": 0
        })
        print(f"  Slot {i} -> IDLE")
    
    # Resetar Vault para sniper_mode=False
    print("\n[2/3] Bloqueando Capitão...")
    fs.collection("vault_management").document("current_cycle").set({
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
        "sniper_mode_active": False
    })
    print("  Capitão BLOQUEADO")
    
    # Resetar Banca
    print("\n[3/3] Resetando Banca...")
    fs.collection("banca_status").document("status").set({
        "id": "status",
        "saldo_total": 0.0,
        "risco_real_percent": 0.0,
        "slots_disponiveis": 1,
        "lucro_total_acumulado": 0.0,
        "lucro_ciclo": 0.0,
        "vault_total": 0.0,
        "status": "ONLINE_CLEAN"
    })
    print("  Banca resetada (slots_disponiveis: 1)")
    
    # Limpar paper_storage
    print("\n[4/4] Limpando paper_storage...")
    import json
    with open("paper_storage.json", "w") as f:
        json.dump({"positions": [], "balance": 0.0, "history": []}, f)
    print("  paper_storage.json limpo")
    
    print("\n" + "=" * 50)
    print("SISTEMA LIMPO E RESETADO")
    print("=" * 50)
    print("Slots: Todos IDLE")
    print("Capitão: BLOQUEADO (sniper_mode_active=false)")
    print("Banca: Slots disponiveis = 1")
    print("Backend deve ser reiniciado")

if __name__ == "__main__":
    asyncio.run(main())