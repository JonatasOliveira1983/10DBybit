import asyncio
import logging
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ForceReload")

async def main():
    print("RECARREGANDO SERVIÇO BYBIT COM STATE LIMPO")
    
    # Limpar paper_storage
    import json
    import os
    storage_file = "paper_storage.json"
    
    with open(storage_file, "w") as f:
        json.dump({"positions": [], "balance": 0.0, "history": []}, f)
    
    print(f"{storage_file} limpo")
    print("Backend deve ser reiniciado")

if __name__ == "__main__":
    asyncio.run(main())