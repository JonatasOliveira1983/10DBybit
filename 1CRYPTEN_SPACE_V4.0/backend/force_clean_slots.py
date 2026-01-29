
import asyncio
import os
import sys

# Add the current directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '1CRYPTEN_SPACE_V4.0/backend')))

from services.firebase_service import firebase_service

async def force_clean():
    await firebase_service.initialize()
    db = firebase_service.db
    
    print("🔎 Verificando slots atuais...")
    slots_ref = db.collection("slots_ativos")
    docs = slots_ref.stream()
    for doc in docs:
        d = doc.to_dict()
        print(f"Slot {doc.id}: {d.get('symbol')} ({d.get('status_risco')})")

    print("\n🧹 Forçando limpeza total...")
    for i in range(1, 11):
        doc_id = str(i)
        await asyncio.to_thread(db.collection("slots_ativos").document(doc_id).delete)
        # Re-initialize clean
        await asyncio.to_thread(db.collection("slots_ativos").document(doc_id).set, {
            "id": i,
            "symbol": None,
            "side": None,
            "entry_price": 0,
            "current_stop": 0,
            "status_risco": "LIVRE",
            "pnl_percent": 0,
            "pensamento": "Sistema reiniciado com força bruta."
        })
    print("✅ Slots resetados.")

if __name__ == "__main__":
    asyncio.run(force_clean())
