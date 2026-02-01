
import asyncio
import os
import sys

# Add backend to path
backend_path = os.path.join(os.getcwd(), '1CRYPTEN_SPACE_V4.0', 'backend')
sys.path.append(backend_path)
os.chdir(backend_path)

from services.firebase_service import firebase_service
from services.bankroll import bankroll_manager

async def force_sync():
    print("🚀 Forcando Sincronizacao de Margem e PnL...")
    await firebase_service.initialize()
    
    # Executa a sincronização real (que agora tem cooldown de apenas 10s)
    await bankroll_manager.sync_slots_with_exchange() # Primeiro ciclo: Re-adoção se necessário
    await asyncio.sleep(0.5)
    await bankroll_manager.sync_slots_with_exchange() # Segundo ciclo: Atualização de margem real
    
    # Verifica os resultados
    slots = await firebase_service.get_active_slots()
    print("\n--- STATUS APOS SINCRONIZACAO ---")
    for s in slots:
        if s.get("symbol"):
            margin = s.get("entry_margin", 0)
            roi = s.get("pnl_percent", 0)
            profit = (margin * (roi / 100))
            print(f"✅ {s.get('symbol')}: Margin=${margin:.2f} | ROI={roi:.1f}% | Profit=${profit:.2f}")

if __name__ == "__main__":
    asyncio.run(force_sync())
