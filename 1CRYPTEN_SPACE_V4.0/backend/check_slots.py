import asyncio
from firebase_admin import credentials, firestore, initialize_app, _apps

def inspect():
    if not _apps:
        cred = credentials.Certificate(r"c:\Users\spcom\Desktop\10D-Bybit1.0\1CRYPTEN_SPACE_V4.0\backend\serviceAccountKey.json")
        initialize_app(cred)
    
    db = firestore.client()
    slots = db.collection("slots_ativos").stream()
    
    print("\n--- Current Slots Status ---")
    for doc in slots:
        data = doc.to_dict()
        sym = data.get("symbol")
        if sym:
            print(f"Slot {data.get('id')}: {sym} | ROI: {data.get('pnl_percent')}% | PnL $: {data.get('pnl_usd', 0)}")
    print("---------------------------\n")

if __name__ == "__main__":
    inspect()
