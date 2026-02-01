import asyncio
import os
import sys

sys.path.append(os.getcwd())

from services.firebase_service import firebase_service

async def check_patch():
    await firebase_service.initialize()
    if not firebase_service.is_active:
        print("Firebase Offline")
        return

    trades = await firebase_service.get_trade_history(limit=5)
    print("--- LAST 5 TRADES ---")
    for t in trades:
        print(f"{t.get('timestamp')} | {t.get('symbol')} | {t.get('pnl')}")
    
    jasmy_patch = any(t.get('symbol') == 'JASMYUSDT.P' and t.get('pnl') > 4.8 for t in trades)
    if jasmy_patch:
        print("✅ JASMY PATCH DETECTED!")
    else:
        print("❌ JASMY PATCH NOT FOUND.")

if __name__ == "__main__":
    asyncio.run(check_patch())
