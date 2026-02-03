import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
from datetime import datetime, timezone

def nuclear_purge():
    print("🚀 NUCLEAR PURGE INITIATED...")
    
    # 1. Credentials
    cred_path = "serviceAccountKey.json"
    if not os.path.exists(cred_path):
        print("❌ Credentials not found")
        return

    # 2. Firebase Initialization
    try:
        firebase_admin.get_app()
    except ValueError:
        firebase_admin.initialize_app(credentials.Certificate(cred_path))

    fs = firestore.client()

    print("🗑️ Force cleaning SLOTS (1-10)...")
    batch = fs.batch()
    for i in range(1, 11):
        slot_type = "SURF" if i <= 5 else "SNIPER"
        doc_ref = fs.collection("slots_ativos").document(str(i))
        batch.set(doc_ref, {
            "id": i,
            "symbol": None,
            "side": None,
            "entry_price": 0,
            "current_stop": 0,
            "status_risco": "LIVRE",
            "pnl_percent": 0,
            "pnl_usd": 0,
            "slot_type": slot_type,
            "pensamento": "☢️ NUCLEAR RESET V6.0",
            "updated_at": datetime.now(timezone.utc).isoformat()
        })
    batch.commit()
    print("✅ SLOTS PURGED.")

    print("🗑️ Cleaning Core Data (Banca/Vault)...")
    fs.collection("banca_status").document("status").set({
        "saldo_total": 100.0,
        "risco_real_percent": 0.0,
        "lucro_ciclo": 0.0,
        "vault_total": 0.0,
        "updated_at": datetime.now(timezone.utc).isoformat()
    })
    
    fs.collection("vault_management").document("current_cycle").set({
        "cycle_number": 1,
        "cycle_profit": 0.0,
        "started_at": datetime.now(timezone.utc).isoformat()
    })
    print("✅ CORE DATA PURGED.")

    print("📂 Cleaning local paper_storage.json...")
    with open("paper_storage.json", "w") as f:
        json.dump({"positions": [], "balance": 100.0, "history": []}, f, indent=2)
    print("✅ LOCAL STATE PURGED.")
    
    print("🏁 NUCLEAR PURGE COMPLETE.")

if __name__ == "__main__":
    nuclear_purge()
