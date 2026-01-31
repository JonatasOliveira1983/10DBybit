import asyncio
import logging
from services.vault_service import vault_service
from services.firebase_service import firebase_service

logging.basicConfig(level=logging.INFO)

async def main():
    print("🚀 Initializing Firebase...")
    await firebase_service.initialize()
    
    print("🔄 Starting Vault Sync...")
    await vault_service.sync_vault_with_history()
    print("✅ Sync Process Finished.")

if __name__ == "__main__":
    asyncio.run(main())
