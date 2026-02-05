import asyncio
import logging
import sys
import os

# Ensure current dir is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.vault_service import vault_service
from services.firebase_service import firebase_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FixCycleSync")

async def main():
    print("🚀 Initializing Sync Script...", flush=True)
    try:
        await firebase_service.initialize()
        print("✅ Firebase Connected", flush=True)
        
        print("🔄 Running sync_vault_with_history...", flush=True)
        await vault_service.sync_vault_with_history()
        
        current = await vault_service.get_cycle_status()
        print("\n📊 Current Cycle Status:", flush=True)
        print(f"Cycle Number: {current.get('cycle_number')}", flush=True)
        print(f"Trades Count: {current.get('total_trades_cycle')}", flush=True)
        print(f"Used Symbols: {current.get('used_symbols_in_cycle')}", flush=True)
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
