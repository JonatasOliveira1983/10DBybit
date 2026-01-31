import logging
import asyncio
import time
from services.firebase_service import firebase_service
from services.bybit_rest import bybit_rest_service
from services.vault_service import vault_service
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BankrollManager")

def get_slot_type(slot_id: int) -> str:
    """Returns SNIPER for slots 1-5, SURF for slots 6-10."""
    return "SNIPER" if slot_id <= 5 else "SURF"

class BankrollManager:
    def __init__(self):
        self.max_slots = settings.MAX_SLOTS
        self.risk_cap = settings.RISK_CAP_PERCENT # 0.20 (20%)
        self.margin_per_slot = 0.05 # 5% per slot (Sniper mode: 4 slots = 20%)
        self.initial_slots = settings.INITIAL_SLOTS # 4
        self.last_log_times = {} # Cooldown for logs
        # V4.2: Sniper TP = +2% price = 100% ROI @ 50x
        self.sniper_tp_percent = 0.02  # 2% price movement
        self.execution_lock = asyncio.Lock() # Iron Lock Atomic Protector
        self.pending_slots = set() # V4.9.4.2: Local memory lock to prevent duplicate assignments

    async def sync_slots_with_exchange(self):
        """
        Two-way sync:
        1. Clears slots that have no matching position on Bybit (Stale).
        2. Populates empty slots with active Bybit positions (Recovery).
        """
    async def sync_slots_with_exchange(self):
        """
        V4.9.4.3: Persistence Shield 2.0 - FIREBASE IS TRUTH.
        In PAPER mode, if a slot has a symbol, we ensure it exists in memory.
        We only clear slots if we explicitly receive a closure command or a CLEAR signal.
        """
        logger.info("Starting Slot <-> Exchange Synchronization...")
        try:
            # 1. Fetch Exchange Data
            positions = await bybit_rest_service.get_active_positions()
            # Map normalized symbols for comparison (with null-safety)
            exchange_map = {}
            for p in positions:
                sym = p.get("symbol")
                if sym:
                    exchange_map[bybit_rest_service._strip_p(sym).upper()] = p
            active_symbols = list(exchange_map.keys())
            logger.info(f"Exchange Positions ({len(active_symbols)}): {active_symbols}")

            # 2. Fetch DB Slots
            slots = await firebase_service.get_active_slots()
            
            # 3. Persistence Logic for PAPER MODE
            for slot in slots:
                symbol = slot.get("symbol")
                if not symbol: continue
                
                norm_symbol = (bybit_rest_service._strip_p(symbol) or "").upper()
                slot_id = slot["id"]

                # V4.2.6: Persistence Shield - Don't even touch if opened in the last 120 seconds
                entry_ts = slot.get("timestamp_last_update") or 0
                if (time.time() - entry_ts) < 120:
                     continue

                if bybit_rest_service.execution_mode == "PAPER":
                    if norm_symbol not in exchange_map:
                        # RECOVERY INSTEAD OF CLEARING
                        entry_price = float(slot.get("entry_price", 0))
                        side = slot.get("side")
                        
                        # V4.9.4.3: Validate before re-adopting
                        if not side or entry_price <= 0:
                            logger.warning(f"Sync: Slot {slot_id} ({symbol}) has invalid data (side={side}, entry={entry_price}). Skipping.")
                            continue
                        
                        logger.warning(f"Sync [PAPER PERSISTENCE]: Slot {slot_id} ({symbol}) missing from memory. RE-ADOPTING.")
                        
                        qty = float(slot.get("qty", 0))
                        if qty <= 0:
                            qty = 5.0 * 50 / entry_price # Fallback calculation
                            
                        bybit_rest_service.paper_positions.append({
                            "symbol": norm_symbol, 
                            "side": side,
                            "avgPrice": entry_price, 
                            "stopLoss": float(slot.get("current_stop", 0)),
                            "size": qty,
                            "positionValue": qty * entry_price, 
                            "unrealisedPnl": 0
                        })
                        # Update map so next iteration knows it's there
                        exchange_map[norm_symbol] = bybit_rest_service.paper_positions[-1]
                        continue
                else:
                    # REAL MODE: Clear if truly stale
                    if norm_symbol not in exchange_map:
                        logger.warning(f"Sync [REAL]: Clearing stale slot {slot_id} for {symbol}")
                        await firebase_service.update_slot(slot_id, {
                            "symbol": None, "entry_price": 0, "current_stop": 0, 
                            "status_risco": "IDLE", "side": None, "pnl_percent": 0
                        })

            # 4. Import Missing Positions (Exchange has it, DB doesn't)
            for symbol, pos in exchange_map.items():
                if any(bybit_rest_service._strip_p(s.get("symbol") or "").upper() == symbol for s in slots):
                    continue 

                # Find empty slot
                empty_slot = next((s for s in slots if not s.get("symbol")), None)
                if not empty_slot:
                    continue
                
                logger.info(f"Sync: Recovering {symbol} into Slot {empty_slot['id']}.")
                await firebase_service.update_slot(empty_slot["id"], {
                    "symbol": symbol,
                    "side": pos.get("side"),
                    "entry_price": float(pos.get("avgPrice", 0)),
                    "current_stop": float(pos.get("stopLoss", 0)),
                    "status_risco": "RECOVERED",
                    "pnl_percent": 0,
                    "qty": float(pos.get("size", 0)),
                    "timestamp_last_update": time.time()
                })
                # Refresh local list
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
            # Side is normalized
            side_norm = (side or "").upper()
            is_risk_free = False
            if side_norm == "BUY":
                if stop and entry and stop >= entry:
                    is_risk_free = True
            elif side_norm == "SELL":
                if stop and entry and stop <= entry:
                    is_risk_free = True
            
            if not is_risk_free:
                real_risk += self.margin_per_slot
        
        # V4.9.4.2: Include pending slots in risk calculation to prevent over-deployment
        real_risk += len(self.pending_slots) * self.margin_per_slot
        
        return real_risk

    async def can_open_new_slot(self, symbol: str = None, slot_type: str = "SNIPER"):
        """
        V4.3: Checks if a new slot can be opened based on:
        1. Duplicate Guard (absolute - no symbol in any slot)
        2. Slot Type Separation (SNIPER=1-5, SURF=6-10)
        3. 20% risk cap (Hard Limit)
        4. Progressive Expansion per slot type
        """
        slots = await firebase_service.get_active_slots()
        
        # 1. ABSOLUTE Duplicate Guard (normalize symbol for comparison)
        if symbol:
            norm_symbol = symbol.replace(".P", "").upper()
            for s in slots:
                existing_sym = (s.get("symbol") or "").replace(".P", "").upper()
                if existing_sym == norm_symbol:
                    logger.warning(f"V4.3 Duplicate Guard: {symbol} already in Slot {s['id']}. BLOCKED.")
                    return None
            
            # Check local pending lock as well
            if any(p_sym == norm_symbol for p_sym, p_id in self.pending_slots):
                 logger.warning(f"V4.9.4.2 Atomic Lock: {symbol} already pending for execution. BLOCKED.")
                 return None
        
        # 2. Slot Type Separation
        if slot_type == "SNIPER":
            type_slots = [s for s in slots if s["id"] <= 5]
            slot_range = range(1, 6)
        else:  # SURF
            type_slots = [s for s in slots if s["id"] >= 6]
            slot_range = range(6, 11)
        
        active_type_slots = [s for s in type_slots if s.get("symbol")]
        active_count = len(active_type_slots)
        if active_count > 0:
            active_list = [f"Slot({s['id']}):{s['symbol']}" for s in active_type_slots]
            logger.info(f"V4.9.4.2 Debug: Active {slot_type} slots: {', '.join(active_list)}")
        
        # 3. Hard Risk Cap Check (global)
        real_risk = await self.calculate_real_risk()
        if (real_risk + self.margin_per_slot) > self.risk_cap:
            logger.warning(f"Risk Cap Reached: {real_risk*100:.1f}% + {self.margin_per_slot*100}% > {self.risk_cap*100}%")
            return None
        
        # 4. Progressive Expansion Logic (per slot type)
        max_initial = 2 if slot_type == "SNIPER" else 2  # Start with 2 of each type
        
        if active_count >= max_initial:
            # Check for Risk Free in this slot type
            risk_free_count = 0
            for s in active_type_slots:
                entry = s.get("entry_price", 0)
                stop = s.get("current_stop", 0)
                side_norm = (s.get("side") or "").lower()
                if entry > 0:
                    if side_norm == "buy" and stop >= entry:
                        risk_free_count += 1
                    elif side_norm == "sell" and stop <= entry:
                        risk_free_count += 1
            
            allowed = max_initial + risk_free_count
            if active_count >= allowed:
                import time
                now = time.time()
                log_key = f"progression_cap_{slot_type}"
                last = self.last_log_times.get(log_key, 0)
                if now - last > 60:
                    logger.info(f"V4.3 {slot_type} Cap: Active({active_count}) >= Allowed({allowed}) [Initial {max_initial} + RiskFree {risk_free_count}]")
                    self.last_log_times[log_key] = now
                return None
        
        # 5. Find available slot in the correct range
        pending_ids = [p_id for p_sym, p_id in self.pending_slots]
        for s in slots:
            if s["id"] in slot_range and not s.get("symbol") and s["id"] not in pending_ids:
                return s["id"]
        
        return None

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

    async def open_position(self, symbol: str, side: str, sl_price: float = 0, tp_price: float = None, pensamento: str = "", slot_type: str = "SNIPER"):
        """V4.3: Executes Sniper/Surf entry with separated slot types (SNIPER=1-5, SURF=6-10)."""
        async with self.execution_lock:
            # 1. Total Awareness: Check availability & local lock
            norm_symbol = (bybit_rest_service._strip_p(symbol) or "").upper()
            
            # 1.1 Duplicate Guard (Firebase + Memory)
            active_slots = await firebase_service.get_active_slots()
            if any(bybit_rest_service._strip_p(S.get("symbol") or "").upper() == norm_symbol for S in active_slots):
                logger.warning(f"Iron Lock: Signal {symbol} already active in Firebase. BLOCKED.")
                return None
            
            if any(p_sym == norm_symbol for p_sym, p_id in self.pending_slots):
                 logger.warning(f"Iron Lock: Signal {symbol} already pending in memory. BLOCKED.")
                 return None

            # 1.2 Vault & Risk Guard
            trading_allowed, reason = await vault_service.is_trading_allowed()
            if not trading_allowed:
                logger.warning(f"Trading blocked: {reason}")
                await firebase_service.log_event("VAULT", f"Trade BLOCKED: {reason}", "WARNING")
                return None
            
            slot_id = await self.can_open_new_slot(symbol=symbol, slot_type=slot_type)
            if not slot_id:
                logger.warning(f"Risk Cap: No slots available for {symbol} ({slot_type})")
                return None
            
            # 1.3 Atomic Lock: Claim the slot in memory before any network calls
            self.pending_slots.add((norm_symbol, slot_id))
            logger.info(f"Iron Lock: Claimed Slot {slot_id} for {symbol}. Proceeding with execution...")

        try:
            # 2. Fetch Market Data & Calculate Order
            ticker = await bybit_rest_service.get_tickers(symbol=symbol)
            current_price = float(ticker.get("result", {}).get("list", [{}])[0].get("lastPrice", 0))
            
            if current_price == 0:
                logger.error(f"Could not fetch price for {symbol}")
                return None

            info = await asyncio.to_thread(bybit_rest_service.get_instrument_info, symbol)
            qty_step = float(info.get("lotSizeFilter", {}).get("qtyStep", 0.001))
            
            balance = await asyncio.to_thread(bybit_rest_service.get_wallet_balance)
            if balance < 10:
                logger.warning(f"Balance too low: ${balance}")
                return None
                
            margin = balance * self.margin_per_slot
            raw_qty = (margin * settings.LEVERAGE) / current_price
            
            import math
            precision = max(0, int(-math.log10(qty_step))) if qty_step > 0 else 3
            qty = round(raw_qty, precision)
            if qty <= 0: qty = qty_step

            # 3. Stop Loss Logic (Protocol Elite)
            sl_percent = 0.01 if slot_type == "SNIPER" else 0.015
            final_sl = sl_price
            if final_sl <= 0:
                final_sl = current_price * (1 - sl_percent) if side == "Buy" else current_price * (1 + sl_percent)
            
            # Validation
            if side == "Buy" and final_sl >= current_price: final_sl = current_price * (1 - sl_percent)
            if side == "Sell" and final_sl <= current_price: final_sl = current_price * (1 + sl_percent)
            
            # Take Profit (Sniper only)
            final_tp = tp_price
            if slot_type == "SNIPER":
                final_tp = current_price * (1 + self.sniper_tp_percent) if side == "Buy" else current_price * (1 - self.sniper_tp_percent)

            # 4. Atomic Deployment
            squadron_emoji = "🎯" if slot_type == "SNIPER" else "🏄"
            await firebase_service.log_event("Captain", f"{squadron_emoji} {slot_type} DEPLOYED: {side} {qty} {symbol} @ {current_price}", "SUCCESS")

            order = await asyncio.wait_for(bybit_rest_service.place_atomic_order(symbol, side, qty, final_sl, final_tp), timeout=10.0)
            
            if order:
                await firebase_service.update_slot(slot_id, {
                    "symbol": symbol,
                    "side": side,
                    "qty": qty,
                    "entry_price": current_price,
                    "current_stop": final_sl,
                    "target_price": final_tp,
                    "slot_type": slot_type,
                    "status_risco": "ATIVO",
                    "pnl_percent": 0.0,
                    "pensamento": pensamento,
                    "timestamp_last_update": time.time()
                })
                await self.update_banca_status()
                return order
            else:
                return None

        except Exception as e:
            logger.error(f"Execution Error for {symbol}: {e}")
            return None
        finally:
            # 5. Release Lock
            if (norm_symbol, slot_id) in self.pending_slots:
                self.pending_slots.remove((norm_symbol, slot_id))


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
                    # Fetch position to get size (Simulation aware)
                    pos_list = await bybit_rest_service.get_active_positions(symbol=symbol)
                    for pos in pos_list:
                        size = float(pos.get("size", 0))
                        if size > 0:
                            await bybit_rest_service.close_position(symbol, pos["side"], size)
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

    async def position_reaper_loop(self):
        """
        Background loop that runs every 30s to detect closed positions on Bybit
        and finalize their data in Firebase (History + Slot clearing).
        """
        logger.info("Position Reaper loop active.")
        while True:
            try:
                await self.sync_slots_with_exchange()
                await self.update_banca_status()
            except Exception as e:
                logger.error(f"Error in Position Reaper: {e}")
            await asyncio.sleep(30) # Scan every 30s

    async def register_sniper_trade(self, trade_data: dict):
        """
        V4.2/V4.3.1: Registra um trade Sniper no ciclo de 20 trades.
        Chamado pelo Position Reaper quando um trade SNIPER fecha.
        """
        try:
            slot_type = trade_data.get("slot_type", "SNIPER")
            pnl = trade_data.get("pnl", 0)
            
            # Use the updated vault service method
            if slot_type == "SNIPER":
                await vault_service.register_sniper_trade(trade_data)
                status_msg = "Win" if pnl > 0 else "Loss"
                logger.info(f"Sniper {status_msg} registered in Vault: {trade_data.get('symbol')} ${pnl:.2f}")
        except Exception as e:
            logger.error(f"Error registering sniper trade: {e}")

bankroll_manager = BankrollManager()
