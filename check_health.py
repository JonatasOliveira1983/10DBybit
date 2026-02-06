import asyncio
import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.join(os.getcwd(), "1CRYPTEN_SPACE_V4.0", "backend"))

from services.firebase_service import firebase_service
from services.bankroll import bankroll_manager
from services.bybit_ws import bybit_ws_service

async def main():
    print("=" * 50)
    print("V10.5 SYSTEM HEALTH CHECK")
    print("=" * 50)
    
    cred_path = os.path.join(os.getcwd(), "1CRYPTEN_SPACE_V4.0", "backend", "serviceAccountKey.json")
    if not os.path.exists(cred_path):
        # Fallback to current dir if already in backend
        cred_path = "serviceAccountKey.json"
        
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cred_path
    await firebase_service.initialize()
    
    # 1. Check Active Slots
    print("\n[SLOTS STATUS]")
    slots = await firebase_service.get_active_slots()
    empty_slots = []
    for s in slots:
        status = s.get("status_risco", "N/A")
        symbol = s.get("symbol") or "EMPTY"
        print(f"  Slot {s['id']}: {symbol} | Status: {status}")
        if not s.get("symbol"):
            empty_slots.append(s['id'])
            
    # 2. Check Recent Signals
    print("\n[RECENT SIGNALS (Last 5)]")
    sigs = await firebase_service.get_recent_signals(limit=5)
    if not sigs:
        print("  No recent signals found in Firestore.")
    for sig in sigs:
        print(f"  {sig.get('symbol')} | Score: {sig.get('score')} | reasoning: {sig.get('reasoning')[:60]}...")

    # 3. Check Monitoring Coverage
    # Note: This checks the in-memory state of the RUNNING process (difficult from a separate script)
    # But we can check if the Bybit WS is likely working if we see signals above.
    
    print("\n" + "=" * 50)
    print("END OF HEALTH CHECK")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())
