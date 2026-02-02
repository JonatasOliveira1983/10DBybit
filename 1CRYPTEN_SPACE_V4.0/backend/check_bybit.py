
import asyncio
from services.bybit_rest import bybit_rest_service

async def check():
    print("📡 Connecting to Bybit...")
    try:
        positions = await bybit_rest_service.get_active_positions()
        active = [p for p in positions if float(p['size']) > 0]
        
        print(f"\n✅ Active Positions ({len(active)}):")
        for p in active:
            print(f"   - {p['symbol']}: {p['side']} {p['size']} | PnL: {p['unrealisedPnl']}")
            
        if not active:
            print("   (No active positions found)")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(check())
