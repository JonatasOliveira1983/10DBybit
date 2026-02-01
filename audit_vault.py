import asyncio
import os
import sys

# Add path for service imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "1CRYPTEN_SPACE_V4.0/backend")))

from services.firebase_service import firebase_service
from services.vault_service import vault_service

async def audit():
    await firebase_service.initialize()
    
    print("--- VAULT STATUS ---")
    status = await vault_service.get_cycle_status()
    for k, v in status.items():
        print(f"{k}: {v}")
    
    print("\n--- TRADE HISTORY (Last 10) ---")
    trades = await firebase_service.get_trade_history(limit=10)
    for t in trades:
        print(f"[{t.get('timestamp')}] {t.get('symbol')} | {t.get('slot_type')} | Side: {t.get('side')} | PnL: ${t.get('pnl'):.2f} | Reason: {t.get('close_reason')}")

    print("\n--- WITHDRAWAL HISTORY ---")
    withdrawals = await vault_service.get_withdrawal_history()
    for w in withdrawals:
        print(f"[{w.get('timestamp')}] Amount: ${w.get('amount')} | Dest: {w.get('destination')}")

if __name__ == "__main__":
    asyncio.run(audit())
