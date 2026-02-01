import asyncio
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "1CRYPTEN_SPACE_V4.0/backend")))

from services.firebase_service import firebase_service

async def audit_surf():
    await firebase_service.initialize()
    
    print("--- SEARCHING FOR SURF TRADES ---")
    query = firebase_service.db.collection("trade_history").where("slot_type", "==", "SURF").stream()
    surf_trades = [d.to_dict() for d in query]
    
    if not surf_trades:
        print("No SURF trades found in history.")
    for t in surf_trades:
        print(f"[{t.get('timestamp')}] {t.get('symbol')} | PnL: ${t.get('pnl'):.2f} | Reason: {t.get('close_reason')}")

if __name__ == "__main__":
    asyncio.run(audit_surf())
