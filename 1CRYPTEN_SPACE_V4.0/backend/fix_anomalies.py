import asyncio
import logging
import sys
import os

# Add the current directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.firebase_service import firebase_service
from services.bybit_rest import bybit_rest_service
from services.execution_protocol import execution_protocol

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AnomalyFixer")

async def fix_slots():
    logger.info("Starting Anomaly Fixer...")
    await firebase_service.initialize()
    await bybit_rest_service.initialize()
    
    slots = await firebase_service.get_active_slots()
    
    for slot in slots:
        slot_id = slot.get("id")
        symbol = slot.get("symbol")
        pnl_pct = slot.get("pnl_percent", 0)
        
        if not symbol: continue
        
        # Detect anomaly (ROI > 500% or < -500%)
        if abs(pnl_pct) > 500:
            logger.warning(f"🚨 Anomaly detected in Slot {slot_id} ({symbol}): ROI = {pnl_pct:.2f}%")
            
            # Reset only the PnL and Price - the Guardian will re-update them correctly on next loop
            # with the new ROI capping and naming checks.
            logger.info(f"Refetching real price for {symbol}...")
            ticker = await bybit_rest_service.get_tickers(symbol=symbol)
            last_price = float(ticker.get("result", {}).get("list", [{}])[0].get("lastPrice", 0))
            
            if last_price > 0:
                entry = slot.get("entry_price", 0)
                side = slot.get("side", "Buy")
                
                # Re-calculate with local logic to see if it's still an anomaly
                new_roi = execution_protocol.calculate_roi(entry, last_price, side)
                
                logger.info(f"Corrected ROI for {symbol}: {new_roi:.2f}% (Price: {last_price})")
                
                await firebase_service.update_slot(slot_id, {
                    "pnl_percent": new_roi,
                    "current_price": last_price,
                    "pensamento": "🛡️ Anomaly Fixer: ROI corrigido e normalizado."
                })
            else:
                logger.error(f"Could not fetch price for {symbol}. Clearing slot to be safe.")
                # If we can't find the price, the naming is likely very broken.
                # In paper mode, we might want to just close it.
                if bybit_rest_service.execution_mode == "PAPER":
                     await firebase_service.hard_reset_slot(slot_id, "ANOMALY_CLEANUP", 0)

    logger.info("Anomaly Fixer complete.")

if __name__ == "__main__":
    asyncio.run(fix_slots())
