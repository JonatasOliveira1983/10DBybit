import asyncio
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "1CRYPTEN_SPACE_V4.0/backend")))

from services.firebase_service import firebase_service
from services.vault_service import vault_service

async def run_sync():
    await firebase_service.initialize()
    print("Iniciando sincronização forçada do Vault...")
    await vault_service.sync_vault_with_history()
    print("✅ Vault sincronizado com sucesso.")

if __name__ == "__main__":
    asyncio.run(run_sync())
