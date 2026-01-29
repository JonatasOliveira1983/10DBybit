import asyncio
import logging
import sys
import os

# Adjust path to include backend root
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.bybit_ws import bybit_ws_service
from services.bankroll import bankroll_manager
from services.firebase_service import firebase_service
from services.bybit_rest import bybit_rest_service

# Configure logging to stdout
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DebugSignals")

async def main():
    print("--- Starting Signal Generator Diagnosis ---")
    
    # 1. Check Bankroll Status
    print("\n[1] Checking Bankroll Status...")
    try:
        slots = await firebase_service.get_active_slots()
        active_slots = [s for s in slots if s.get("symbol")]
        print(f"   Active Slots: {len(active_slots)} / {len(slots)}")
        
        can_open = await bankroll_manager.can_open_new_slot()
        print(f"   Can Open New Slot? {'YES (ID: ' + str(can_open) + ')' if can_open is not None else 'NO (Blocked)'}")
        
        if can_open is None:
             print("   -> BLOCK REASON: Likely Risk Cap or Progressive Expansion Limit.")
             real_risk = await bankroll_manager.calculate_real_risk()
             print(f"   Real Risk: {real_risk*100:.2f}% (Cap: {bankroll_manager.risk_cap*100:.2f}%)")
    except Exception as e:
        print(f"   ERROR Checking Bankroll: {e}")

    # 2. Check WebSocket Data
    print("\n[2] Checking Bybit WebSocket Data...")
    
    TEST_SYMBOLS = ["BTCUSDT.P", "ETHUSDT.P", "SOLUSDT.P", "XRPUSDT.P", "DOGEUSDT.P", "ADAUSDT.P", "BNBUSDT.P", "TRXUSDT.P", "AVAXUSDT.P", "LINKUSDT.P"]
    try:
        print(f"   Initializing WebSocket connection for {len(TEST_SYMBOLS)} symbols (wait 8s)...")
        await bybit_ws_service.start(TEST_SYMBOLS)
        await asyncio.sleep(8) # Let it warm up
        
        active_symbols = bybit_ws_service.active_symbols
        print(f"   Active Symbols in Memory: {len(active_symbols)}")
        
        if len(active_symbols) == 0:
            print("   -> WARNING: No active symbols found. WS might not be receiving data.")
        
        # 3. Analyze CVD Scores
        print("\n[3] Analyzing Market CVD Scores...")
        high_cvd_count = 0
        elite_count = 0
        
        sorted_symbols = []
        for symbol in active_symbols:
            cvd = bybit_ws_service.get_cvd_score(symbol)
            score = min(99, int(75 + (abs(cvd) / 15000))) if abs(cvd) > 50000 else 0
            sorted_symbols.append((symbol, cvd, score))
        
        # Sort by absolute CVD
        sorted_symbols.sort(key=lambda x: abs(x[1]), reverse=True)
        
        print(f"   Top 10 CVDs found:")
        for s in sorted_symbols[:10]:
            is_elite = s[2] >= 75 # New Threshold
            prefix = "[ELITE]" if is_elite else "[HIGH]" if abs(s[1]) > 30000 else "[LOW]"
            print(f"   {prefix} {s[0]}: CVD=${s[1]:,.0f} | Score={s[2]}")
            
            if abs(s[1]) > 30000:
                high_cvd_count += 1
            if is_elite:
                elite_count += 1
        
        print(f"\n   Summary: {high_cvd_count} symbols > $30k CVD, {elite_count} ELITE signals (Score >= 75).")
        
        if elite_count == 0:
            print("   -> DIAGNOSIS: No signals generated because NO symbol meets the ELITE threshold (CVD > $50k approx).")
            print("   -> RECOMMENDATION: Lower the threshold in signal_generator.py if market is slow.")
            
    except Exception as e:
        print(f"   ERROR Checking WS: {e}")
    finally:
        # Cleanup
        print("\n   Closing connections...")
        # Close WS if needed
        # await bybit_ws_service.close() # Method might not exist or be needed if script ends

if __name__ == "__main__":
    asyncio.run(main())
