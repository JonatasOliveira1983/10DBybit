import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "1CRYPTEN_SPACE_V4.0", "backend"))

async def verify_50x_filter():
    from services.bybit_rest import bybit_rest_service
    from config import settings
    
    print("Initializing Bybit service...")
    await bybit_rest_service.initialize()
    
    print("Fetching Elite 50x pairs...")
    pairs = await bybit_rest_service.get_elite_50x_pairs()
    
    print(f"Found {len(pairs)} pairs.")
    
    # Check if BTC or ETH is present
    majors = ["BTCUSDT.P", "ETHUSDT.P", "SOLUSDT.P"]
    found_majors = [p for p in pairs if p in majors]
    
    if found_majors:
        print(f"FAIL: Found majors in 50x list: {found_majors}")
    else:
        print("SUCCESS: No majors found in 50x list.")
        
    # Check a few samples if they are actually 50x
    if pairs:
        print(f"Sample pairs: {pairs[:5]}")
    else:
        print("❌ FAIL: No pairs found at all.")

if __name__ == "__main__":
    asyncio.run(verify_50x_filter())
