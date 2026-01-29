import asyncio
from services.firebase_service import firebase_service
from services.bybit_rest import bybit_rest_service

async def force_trade():
    await firebase_service.initialize()
    
    symbol = "BTCUSDT.P"
    entry = 98000.0
    side = "Buy"
    stop = 95000.0
    
    print(f"Forcing ELITE position for {symbol}...")
    
    # 1. Update Firebase Slot 1
    await firebase_service.update_slot(1, {
        "symbol": symbol,
        "entry_price": entry,
        "side": side,
        "current_stop": stop,
        "status_risco": "ELITE_TEST",
        "pnl_percent": 0.5
    })
    
    # 2. Update Banca Status
    await firebase_service.update_banca_status({
        "saldo_total": 100.0,
        "risco_real_percent": 0.05,
        "slots_disponiveis": 3
    })
    
    print(f"✅ Success. Browse to Banca page to view {symbol} chart.")

if __name__ == "__main__":
    asyncio.run(force_trade())
