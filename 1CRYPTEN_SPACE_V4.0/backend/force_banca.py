import asyncio
from services.firebase_service import firebase_service

async def force_update():
    await firebase_service.initialize()
    await firebase_service.update_banca_status({
        "id": "status",
        "saldo_total": 100.0,
        "risco_real_percent": 0.0,
        "slots_disponiveis": 10
    })
    print("Force update complete: $100.0")

if __name__ == "__main__":
    asyncio.run(force_update())
