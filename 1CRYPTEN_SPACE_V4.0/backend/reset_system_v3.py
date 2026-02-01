
import asyncio
import firebase_admin
from firebase_admin import credentials, firestore
import os
import shutil
from datetime import datetime, timezone

# CREDENTIALS PATH
CRED_PATH = "serviceAccountKey.json"

async def full_system_reset():
    print("🚀 INITIATING COMPREHENSIVE VAULT SYSTEM RESET (V3)...")

    if not os.path.exists(CRED_PATH):
        print(f"❌ Error: {CRED_PATH} not found.")
        return

    cred = credentials.Certificate(CRED_PATH)
    try:
        firebase_admin.initialize_app(cred)
    except ValueError:
        pass

    db = firestore.client()

    collections_to_clear = [
        "journey_signals",
        "slots_ativos",
        "trade_history",
        "system_logs",
        "banca_history",
        # "vault_management" # Careful about clearing the whole collection blindly
    ]

    for coll_name in collections_to_clear:
        print(f"🔥 Clearing collection: '{coll_name}'...")
        coll_ref = db.collection(coll_name)
        
        docs = coll_ref.limit(500).stream()
        count = 0
        batch = db.batch()
        batch_size = 0
        
        for doc in docs:
            batch.delete(doc.reference)
            batch_size += 1
            count += 1
            if batch_size >= 400:
                batch.commit()
                batch = db.batch()
                batch_size = 0
        
        if batch_size > 0:
            batch.commit()
            
        print(f"✅ Deleted {count} documents from '{coll_name}'.")

    # 1.5 VAULT RESET (Targeted)
    print("🏦 Resetting Vault Cycle...")
    db.collection("vault_management").document("current_cycle").set({
        "sniper_wins": 0,
        "cycle_number": 1,
        "cycle_profit": 0.0,
        "cycle_losses": 0.0,
        "surf_profit": 0.0,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "in_admiral_rest": False,
        "rest_until": None,
        "vault_total": 0.0,
        "cautious_mode": False,
        "min_score_threshold": 75,
        "total_trades_cycle": 0,
        "accumulated_vault": 0.0
    })
    
    # Clear withdrawal history if exists
    print("🏦 Clearing Withdrawal History...")
    w_docs = db.collection("vault_management").document("withdrawals").collection("history").limit(500).stream()
    for doc in w_docs:
        doc.reference.delete()

    # 2. RESET STATUS
    print("🔄 Resetting 'banca_status'...")
    # NOTE: Set initial balance to 0 so it pulls freshly from exchange on restart
    # BUT for visual purposes we can set a placeholder, or just standard start params.
    # The bankroll manager will update it on first run.
    db.collection('banca_status').document('status').set({
        "saldo_total": 0.0, 
        "risco_real_percent": 0.0,
        "slots_disponiveis": 10,
        "status": "RESET",
        "lucro_total_acumulado": 0.0,
        "lucro_ciclo": 0.0,
        "vault_total": 0.0
    })

    # 3. INITIALIZE SLOTS (Ensuring they exist as empty)
    print("📥 Initializing empty slots...")
    for i in range(1, 11):
        slot_type = "SNIPER" if i <= 5 else "SURF"
        db.collection('slots_ativos').document(str(i)).set({
            "id": i,
            "symbol": None,
            "side": None,
            "entry_price": 0,
            "current_stop": 0,
            "status_risco": "LIVRE",
            "pnl_percent": 0,
            "pensamento": "",
            "slot_type": slot_type,
            "entry_margin": 0,
            "visual_status": "SCANNING"
        })

    print("\n✅ SYSTEM RESET & VAULT HARMONIZATION COMPLETE.")
    print("🚀 Ready for fresh start with Protocol Elite V5.2.5")

if __name__ == "__main__":
    asyncio.run(full_system_reset())
