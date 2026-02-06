
import firebase_admin
from firebase_admin import credentials, firestore
import json
import os
import time
from datetime import datetime

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        return super().default(obj)

cred_path = "serviceAccountKey.json"
if os.path.exists(cred_path):
    cred = credentials.Certificate(cred_path)
    try:
        firebase_admin.get_app()
    except ValueError:
        firebase_admin.initialize_app(cred)
else:
    print("Error: credentials not found.")
    exit(1)

db = firestore.client()

def check_cycle_and_history():
    print("\n--- Current Cycle ---")
    cycle = db.collection("vault_management").document("current_cycle").get()
    if cycle.exists:
        print(json.dumps(cycle.to_dict(), indent=2, cls=DateTimeEncoder))
    else:
        print("Current cycle document missing.")

    print("\n--- Trade History (Last 5) ---")
    trades = db.collection("trade_history").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(5).stream()
    trade_list = [t.to_dict() for t in trades]
    if trade_list:
        for t in trade_list:
            print(f"Time: {t.get('timestamp')} | Symbol: {t.get('symbol')} | PnL: {t.get('pnl')}")
    else:
        print("No trade history found.")

if __name__ == "__main__":
    check_cycle_and_history()
