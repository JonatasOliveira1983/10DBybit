import asyncio
import logging
from services.firebase_service import firebase_service
from services.bybit_rest import bybit_rest_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FixSL")

async def fix_xaut_sl():
    await bybit_rest_service.initialize()
    
    # 1. Fetch Slots
    slots = await firebase_service.get_active_slots()
    # Find active slot (XAUT or whatever is there)
    target_slot = None
    for s in slots:
        if s.get("symbol") and "XAUT" in s.get("symbol"):
            target_slot = s
            break
            
    if not target_slot:
        logger.warning("No active XAUT slot found.")
        # Fallback: check ANY active slot
        active = [s for s in slots if s.get("symbol")]
        if active:
            target_slot = active[0]
            logger.info(f"Found alternative active slot: {target_slot['symbol']}")
        else:
            logger.error("No active slots found at all.")
            return

    symbol = target_slot["symbol"]
    entry = float(target_slot["entry_price"])
    current_sl = float(target_slot["current_stop"])
    side = target_slot["side"]
    slot_id = target_slot["id"]
    
    logger.info(f"Current State: {symbol} | Side: {side} | Entry: {entry} | SL: {current_sl}")
    
    # 2. Calculate Correct 1% SL
    sl_percent = 0.01
    if side.upper() == "BUY":
        new_sl = entry * (1 - sl_percent)
    else: # SHORT
        new_sl = entry * (1 + sl_percent)
        
    # Rounding
    new_sl = await bybit_rest_service.round_price(symbol, new_sl)
    
    logger.info(f"Target 1% SL: {new_sl}")
    
    if abs(new_sl - current_sl) < (entry * 0.001):
        logger.info("SL already close to target. No update needed.")
        # return

    # 3. Apply Update
    logger.info(f"Updating SL for {symbol} to {new_sl}...")
    
    # Update Bybit (Real or Paper)
    res = await bybit_rest_service.set_trading_stop(
        category="linear",
        symbol=symbol,
        stopLoss=str(new_sl)
    )
    logger.info(f"Bybit Response: {res}")
    
    # Update Firebase
    await firebase_service.update_slot(slot_id, {
        "current_stop": new_sl,
        "pensamento": "🔧 SL Corrigido manualmente para 1% (Fix Script)"
    })
    logger.info("Firebase updated.")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(fix_xaut_sl())
