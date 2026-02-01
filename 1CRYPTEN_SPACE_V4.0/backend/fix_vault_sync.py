
import asyncio
import logging
from services.firebase_service import firebase_service
from services.vault_service import vault_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VaultRepair")

async def repair_vault():
    print("🔧 Starting Vault Repair & Sync...")
    
    # 1. Initialize Firebase
    await firebase_service.initialize()
    
    # 2. Force Sync with History
    print("🔄 Running sync_vault_with_history()...")
    await vault_service.sync_vault_with_history()
    
    # 3. Check result
    status = await vault_service.get_cycle_status()
    print(f"✅ Repair Complete. New Status:")
    print(f"   - Cycle: #{status.get('cycle_number')}")
    print(f"   - Wins: {status.get('sniper_wins')}/20")
    print(f"   - Profit: ${status.get('cycle_profit'):.2f}")
    print(f"   - Total Trades: {status.get('total_trades_cycle')}")

if __name__ == "__main__":
    asyncio.run(repair_vault())
