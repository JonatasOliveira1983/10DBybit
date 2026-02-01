import asyncio
import os
import sys

# Add the current directory to sys.path to import services
sys.path.append(os.getcwd())

from services.firebase_service import firebase_service

async def patch_missing_trade():
    print("🚀 Initializing Firebase for patch...")
    await firebase_service.initialize()
    if not firebase_service.is_active:
        print("❌ Firebase service NOT active. Check credentials.")
        return

    # Data from paper_storage.json (already verified)
    trade_data = {
        "symbol": "JASMYUSDT.P",
        "side": "Sell",
        "entry_price": 0.005806,
        "exit_price": 0.005687,
        "qty": 43059.0,
        "pnl": 4.8301691604,
        "leverage": 50.0,
        "slot_id": 10,
        "slot_type": "SURF",
        "close_reason": "SNIPER_OVERDRIVE_PROFIT (102.5%)",
        "status": "COMPLETED"
    }

    print(f"📦 Patching trade for {trade_data['symbol']}...")
    try:
        await firebase_service.log_trade(trade_data)
        print("✅ Trade successfully logged to Firebase history!")
        
        # Also log an event for the user
        await firebase_service.log_event("System", f"Trade History Patched: {trade_data['symbol']} (+${trade_data['pnl']:.2f})", "SUCCESS")
    except Exception as e:
        print(f"❌ Error patching trade: {e}")

if __name__ == "__main__":
    asyncio.run(patch_missing_trade())
