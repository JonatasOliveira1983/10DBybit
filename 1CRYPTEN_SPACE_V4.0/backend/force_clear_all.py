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
# V10.6.6: CONFIGURAÇÃO DA BANCA INICIAL
# ============================================
INITIAL_BALANCE = 20.0  # Banca inicial em USD
MARGIN_PER_SLOT = 0.10  # 10% por slot = $2.00

async def main():
    print("=" * 60)
    print("🧹 LIMPEZA COMPLETA DO SISTEMA V10.6.6")
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
        firebase_admin.initialize_app(cred)
    
    fs = firestore.client()
    
    # [1/6] Resetar SLOTS
    print("\n[1/6] Resetando slots (1-2)...")
    for i in range(1, 3):
        fs.collection("slots_ativos").document(str(i)).set({
            "id": i,
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
            "status": "IDLE"
        })
        print(f"  ✅ Slot {i} -> LIVRE")
    
    # [2/6] Resetar Vault/Cycle
    print("\n[2/6] Resetando Vault e Ciclo...")
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
        "sniper_mode_active": True,
        "used_symbols_in_cycle": [],
        "cycle_bankroll": INITIAL_BALANCE
    })
    print("  ✅ Vault resetado (Ciclo 1, 0 trades)")
    
    # [3/6] Resetar Banca com $20
    print("\n[3/6] Configurando Banca...")
    fs.collection("banca_status").document("status").set({
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
    })
    print(f"  ✅ Banca: ${INITIAL_BALANCE:.2f} (2 slots disponíveis)")
    
    # [4/6] Limpar Sinais (journey_signals)
    print("\n[4/6] Limpando sinais do Radar...")
    signals_ref = fs.collection("journey_signals")
    signals = signals_ref.stream()
    deleted_signals = 0
    for doc in signals:
        doc.reference.delete()
        deleted_signals += 1
    print(f"  ✅ {deleted_signals} sinais removidos")
    
    # [5/6] Limpar Histórico de Trades
    print("\n[5/6] Limpando histórico de trades...")
    history_ref = fs.collection("trade_history")
    trades = history_ref.stream()
    deleted_trades = 0
    for doc in trades:
        doc.reference.delete()
        deleted_trades += 1
    print(f"  ✅ {deleted_trades} trades removidos do histórico")
    
    # [6/6] Limpar paper_storage local
    print("\n[6/6] Limpando paper_storage.json...")
    import json
    with open("paper_storage.json", "w") as f:
        json.dump({
            "positions": [], 
            "balance": INITIAL_BALANCE, 
            "history": []
        }, f, indent=2)
    print(f"  ✅ paper_storage.json resetado (balance: ${INITIAL_BALANCE:.2f})")
    
    print("\n" + "=" * 60)
    print("🎉 SISTEMA LIMPO E PRONTO!")
    print("=" * 60)
    print(f"  💰 Banca: ${INITIAL_BALANCE:.2f}")
    print(f"  📊 Slots: 2 disponíveis (10% cada = ${INITIAL_BALANCE * MARGIN_PER_SLOT:.2f}/trade)")
    print(f"  🎯 Sinais: {deleted_signals} removidos")
    print(f"  📜 Histórico: {deleted_trades} trades removidos")
    print(f"  🔄 Ciclo: 1 (0/10 trades)")
    print("=" * 60)
    print("\n⚠️  REINICIE O BACKEND para aplicar as mudanças!")

if __name__ == "__main__":
    asyncio.run(main())