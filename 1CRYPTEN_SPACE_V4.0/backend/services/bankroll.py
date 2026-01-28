import logging
from services.firebase_service import firebase_service
from services.bybit_rest import bybit_rest_service
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BankrollManager")

class BankrollManager:
    def __init__(self):
        self.max_slots = settings.MAX_SLOTS
        self.risk_cap = settings.RISK_CAP_PERCENT # 0.20 (20%)
        self.margin_per_slot = 0.01 # 1% per slot (Sniper mode)
        self.initial_slots = settings.INITIAL_SLOTS # 4
        self.last_log_times = {} # Cooldown for logs

    async def sync_slots_with_exchange(self):
        """
        Two-way sync:
        1. Clears slots that have no matching position on Bybit (Stale).
        2. Populates empty slots with active Bybit positions (Recovery).
        """
        logger.info("Starting Slot <-> Exchange Synchronization...")
        try:
            # 1. Fetch Exchange Data
            positions = await asyncio.to_thread(bybit_rest_service.get_active_positions)
            # Map symbol -> position_data
            exchange_map = {p["symbol"]: p for p in positions}
            active_symbols = list(exchange_map.keys())
            logger.info(f"Exchange Positions ({len(active_symbols)}): {active_symbols}")

            # 2. Fetch DB Slots
            slots = await firebase_service.get_active_slots()
            db_symbols = {s["symbol"]: s["id"] for s in slots if s.get("symbol")}

            # 3. Clear Stale Slots (DB has it, Exchange doesn't)
            for slot in slots:
                symbol = slot.get("symbol")
                if symbol and symbol not in exchange_map:
                    logger.warning(f"Sync: Slot {slot['id']} for {symbol} is stale. Fetching result before clearing.")
                    
                    # Try to fetch last closed PnL
                    try:
                        closed_list = await asyncio.to_thread(bybit_rest_service.get_closed_pnl, symbol)
                        if closed_list:
                            last_trade = closed_list[0]
                            await firebase_service.log_trade({
                                "symbol": symbol,
                                "side": last_trade.get("side"),
                                "entry_price": float(last_trade.get("avgEntryPrice", 0)),
                                "exit_price": float(last_trade.get("avgExitPrice", 0)),
                                "pnl": float(last_trade.get("closedPnl", 0)),
                                "leverage": last_trade.get("leverage"),
                                "qty": last_trade.get("qty"),
                                "closed_at": last_trade.get("updatedTime")
                            })
                            logger.info(f"Sync: Logged final trade for {symbol}.")
                    except Exception as e:
                        logger.error(f"Sync: Error logging closed trade for {symbol}: {e}")

                    logger.warning(f"Sync: Clearing stale slot {slot['id']} for {symbol}")
                    await firebase_service.update_slot(slot["id"], {
                        "symbol": None, "entry_price": 0, "current_stop": 0, 
                        "status_risco": "IDLE", "side": None, "pnl_percent": 0
                    })
            
            # 4. Recover Missing Slots (Exchange has it, DB doesn't)
            for symbol, pos in exchange_map.items():
                if symbol not in db_symbols:
                    # Find empty slot
                    empty_slot = next((s for s in slots if not s.get("symbol")), None)
                    if not empty_slot:
                        logger.warning(f"Sync: Could not import {symbol} - No empty slots!")
                        continue
                    
                    # Import Data
                    entry = float(pos.get("avgPrice", 0))
                    side = pos.get("side") # Buy/Sell
                    stop_loss = float(pos.get("stopLoss", 0))
                    
                    logger.info(f"Sync: Recovering {symbol} into Slot {empty_slot['id']}. Entry: {entry}")
                    await firebase_service.update_slot(empty_slot["id"], {
                        "symbol": symbol,
                        "side": side,
                        "entry_price": entry,
                        "current_stop": stop_loss,
                        "status_risco": "RECOVERED",
                        "pnl_percent": 0 # Guardian will update this
                    })
                    # Refresh local list to avoid double assignment if we had multiple
                    slots = await firebase_service.get_active_slots()

            await firebase_service.log_event("Bankroll", f"Sync Complete. Active: {len(active_symbols)}", "SUCCESS")

        except Exception as e:
            logger.error(f"Error during slot sync: {e}")


    async def calculate_real_risk(self):
        """
        Calculates the real risk: Sum of margin for slots where Stop Loss < Entry Price.
        If Stop Loss >= Entry Price, risk is 0 (Risco Zero).
        """

        slots = await firebase_service.get_active_slots()
        real_risk = 0.0
        
        for slot in slots:
            symbol = slot.get("symbol")
            if not symbol:
                continue
                
            entry = slot.get("entry_price")
            stop = slot.get("current_stop")
            side = slot.get("side")

            # In Long: if stop < entry, we still have risk
            # In Short: if stop > entry, we still have risk
            is_risk_free = False
            if side == "Buy":
                if stop and entry and stop >= entry:
                    is_risk_free = True
            elif side == "Sell":
                if stop and entry and stop <= entry:
                    is_risk_free = True
            
            if not is_risk_free:
                real_risk += self.margin_per_slot
        
        return real_risk

    async def can_open_new_slot(self, symbol: str = None):
        """
        Checks if a new slot can be opened based on:
        1. 20% risk cap (Hard Limit)
        2. Progressive Expansion Rules (Captain's Rule):
           - Max 4 initial slots.
           - Open 5th+ ONLY if previous trades are 'Risk Free' (SL >= Entry).
        """
        # 1. Hard Risk Cap Check
        real_risk = await self.calculate_real_risk()
        if (real_risk + self.margin_per_slot) > self.risk_cap:
             logger.warning(f"Risk Cap Reached: {real_risk*100:.1f}% + {self.margin_per_slot*100}% > {self.risk_cap*100}%")
             return None

        slots = await firebase_service.get_active_slots()
        active_slots = [s for s in slots if s.get("symbol")]
        active_count = len(active_slots)
        
        # 2. Progressive Expansion Logic
        if active_count < self.initial_slots:
            # Under initial limit (0-3), allow open if slot available
            pass
        else:
            # Over initial limit, check for 'Risk Free' slots
            # A slot is Risk Free if current_stop matches or exceeds entry (in favor)
            risk_free_count = 0
            for s in active_slots:
                entry = s.get("entry_price", 0)
                stop = s.get("current_stop", 0)
                side = s.get("side")
                if entry > 0:
                    if side == "Buy" and stop >= entry:
                        risk_free_count += 1
                    elif side == "Sell" and stop <= entry:
                        risk_free_count += 1
            
            allowed_slots = self.initial_slots + risk_free_count
            
            if active_count >= allowed_slots:
                import time
                now = time.time()
                last = self.last_log_times.get("progression_cap", 0)
                if now - last > 60:
                    logger.info(f"Progression Cap: Active({active_count}) >= Allowed({allowed_slots}) [Initial {self.initial_slots} + RiskFree {risk_free_count}]")
                    self.last_log_times["progression_cap"] = now
                return None

        # 3. New Duplicate Symbol Guard
        if symbol:
            duplicate = next((s for s in slots if s.get("symbol") == symbol), None)
            if duplicate:
                logger.warning(f"Duplicate Guard: {symbol} is already active in Slot {duplicate['id']}.")
                return None

        # If we get here, find an ID
        available_id = next((s["id"] for s in slots if not s.get("symbol")), None)
        return available_id

    async def update_banca_status(self):
        """Updates the banca_status table in Supabase."""
        try:
            real_risk = await self.calculate_real_risk()
            slots = await firebase_service.get_active_slots()
            available_slots_count = sum(1 for s in slots if s["symbol"] is None)
            
            # Fetch real balance from Bybit - NON-BLOCKING
            total_equity = await asyncio.to_thread(bybit_rest_service.get_wallet_balance)
            
            banca = await firebase_service.get_banca_status()
            if banca:
                await firebase_service.update_banca_status({
                    "id": banca.get("id", "status"),
                    "saldo_total": total_equity,
                    "risco_real_percent": real_risk,
                    "slots_disponiveis": available_slots_count
                })
                
                # Snapshot logging: Log once every 6 hours (approx)
                if not hasattr(self, "_last_snapshot_time"):
                    self._last_snapshot_time = 0
                
                import time
                current_time = time.time()
                if (current_time - self._last_snapshot_time) > (6 * 3600): # 6 hours
                    await firebase_service.log_banca_snapshot({
                         "saldo_total": total_equity,
                         "risco_real_percent": real_risk,
                         "avail_slots": available_slots_count
                    })
                    self._last_snapshot_time = current_time
                    logger.info("Bankroll snapshot logged to history.")

        except Exception as e:
            logger.error(f"Error updating banca status: {e}")

    async def open_position(self, symbol: str, side: str, sl_price: float = 0, tp_price: float = None, pensamento: str = ""):
        """Executes the Sniper entry with 20% risk cap and 5% margin per slot."""
        # Check for duplication and limits
        slot_id = await self.can_open_new_slot(symbol=symbol)
        if not slot_id:
            # We already logged reason in can_open_new_slot
            return None

        # 1. Fetch Current Price
        ticker = await asyncio.to_thread(bybit_rest_service.session.get_tickers, category="linear", symbol=symbol)
        current_price = float(ticker.get("result", {}).get("list", [{}])[0].get("lastPrice", 0))
        
        if current_price == 0:
            logger.error(f"Could not fetch price for {symbol}")
            await firebase_service.log_event("Captain", f"Trade FAILED: Could not fetch price for {symbol}.", "WARNING")
            return None

        # 2. Dynamic Qty calculation (1% margin per slot at LEVERAGE) with exchange precision
        info = await asyncio.to_thread(bybit_rest_service.get_instrument_info, symbol)
        qty_step = float(info.get("lotSizeFilter", {}).get("qtyStep", 0.001))
        
        balance = await asyncio.to_thread(bybit_rest_service.get_wallet_balance)
        if balance < 10:
            logger.warning(f"Balance too low for trading: ${balance}")
            await firebase_service.log_event("Captain", f"Trade REJECTED: Insufficient balance (${balance:.2f}). Min $10 required.", "WARNING")
            return None
            
        margin = balance * self.margin_per_slot # 1% margin
        leverage = settings.LEVERAGE # 50x
        raw_qty = (margin * leverage) / current_price
        
        # Round to qtyStep precision
        import math
        if qty_step > 0:
            precision = max(0, int(-math.log10(qty_step)))
            qty = round(raw_qty, precision)
        else:
            qty = round(raw_qty, 3)

        # Final SL Safety Check (Liquid-Proof enforcement)
        if side == "Buy":
             # Ensure SL is below entry. If not or zero, set to 2% below.
             if sl_price >= current_price or sl_price <= 0:
                 sl_price = current_price * 0.98
        else:
             # Ensure SL is above entry. If not or zero, set to 2% above.
             if sl_price <= current_price or sl_price <= 0:
                 sl_price = current_price * 1.02

        await firebase_service.log_event("Captain", f"SNIPER DEPLOYED: {side} {qty} {symbol} @ {current_price} | HARD STOP: {sl_price}", "SUCCESS")
        logger.info(f"[Safety] Atomic Order for {symbol} triggered with Hard Stop at {sl_price}")

        
        # Place Atomic Order
        try:
            order = await asyncio.wait_for(asyncio.to_thread(bybit_rest_service.place_atomic_order, symbol, side, qty, sl_price, tp_price), timeout=10.0)
        except Exception as e:
            logger.error(f"Timeout/Error placing order for {symbol}: {e}")
            order = None
        
        if order:
            await firebase_service.update_slot(slot_id, {
                "symbol": symbol,
                "side": side,
                "entry_price": current_price,
                "current_stop": sl_price,
                "status_risco": "ATIVO",
                "pnl_percent": 0.0,
                "pensamento": pensamento
            })
            await self.update_banca_status()
            return order
        else:
            await firebase_service.log_event("Captain", f"Trade FAILED: Order placement rejected by Exchange.", "WARNING")
        
        return None


    async def emergency_close_all(self):
        """Panic Button: Closes all open positions immediately."""
        logger.warning("🚨 PANIC BUTTON ACTIVATED: Closing all positions!")
        slots = await firebase_service.get_active_slots()
        
        for slot in slots:
            symbol = slot.get("symbol")
            if symbol:
                side = slot.get("side")
                # We don't know the exact qty from the slot currently (schema limitation), 
                # but we can try to close full position via API if supported or check position
                # For now, we assume we need to fetch position size or close generic.
                # Bybit close_position usually takes qty. 
                # Let's try to fetch position info first or pass a large qty if reduceOnly allows (risky).
                # BETTER APPROACH: Fetch position from Bybit and close it.
                
                try:
                    # Fetch position to get size
                    positions = bybit_rest_service.session.get_positions(category="linear", symbol=symbol)
                    pos_list = positions.get("result", {}).get("list", [])
                    for pos in pos_list:
                        size = float(pos.get("size", 0))
                        if size > 0:
                            bybit_rest_service.close_position(symbol, pos["side"], size)
                except Exception as e:
                    logger.error(f"Error closing {symbol}: {e}")
                
                # Reset Slot in DB
                await firebase_service.update_slot(slot["id"], {
                    "symbol": None, "side": None, "entry_price": 0, "current_stop": 0, 
                    "status_risco": "LIVRE", "pnl_percent": 0
                })
        
        await firebase_service.log_event("Captain", "PANIC BUTTON: All positions closed.", "WARNING")
        await self.update_banca_status()
        return {"status": "success", "message": "All positions closed"}

bankroll_manager = BankrollManager()
import asyncio # Fix missing import in the file context if needed
