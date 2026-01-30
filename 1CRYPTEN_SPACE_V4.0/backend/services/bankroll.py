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

    async def sync_slots_with_exchange(self):
        """
        Two-way sync:
        1. Clears slots that have no matching position on Bybit (Stale).
        2. Populates empty slots with active Bybit positions (Recovery).
        """
        logger.info("Starting Slot <-> Exchange Synchronization...")
        try:
            # 1. Fetch Exchange Data
            positions = await bybit_rest_service.get_active_positions()
            # Map symbol -> position_data
            # NOTE: We use normalized symbols for comparison
            exchange_map = {bybit_rest_service._strip_p(p["symbol"]): p for p in positions}
            active_symbols = list(exchange_map.keys())
            logger.info(f"Exchange Positions ({len(active_symbols)}): {active_symbols}")

            # 2. Fetch DB Slots
            slots = await firebase_service.get_active_slots()
            db_symbols = {s["symbol"]: s["id"] for s in slots if s.get("symbol")}

            # RECOVERY LOGIC for PAPER MODE:
            is_server_restart = (bybit_rest_service.execution_mode == "PAPER" and len(exchange_map) == 0)

            # 3. Clear Stale Slots (DB has it, Exchange doesn't)
            for slot in slots:
                symbol = slot.get("symbol")
                if not symbol: continue
                
                norm_symbol = bybit_rest_service._strip_p(symbol)
                
                # V4.2.6: Persistence Shield - Don't clear if opened in the last 60 seconds
                # to avoid "flicker" during sync delays.
                entry_ts = slot.get("timestamp_last_update") or 0
                if (time.time() - entry_ts) < 60:
                     continue

                if is_server_restart and norm_symbol not in exchange_map:
                    # Avoid double recovery of the same symbol if it exists in slots multiple times with/without .P
                    if any(p["symbol"] == norm_symbol for p in bybit_rest_service.paper_positions):
                        continue
                        
                    logger.info(f"Sync [PAPER RECOVERY]: Re-adopting {symbol} into memory state.")
                    bybit_rest_service.paper_positions.append({
                        "symbol": norm_symbol, "side": slot.get("side"),
                        "avgPrice": float(slot.get("entry_price", 0)), 
                        "stopLoss": float(slot.get("current_stop", 0)),
                        "size": 5.0 / float(slot.get("entry_price", 1)) if float(slot.get("entry_price", 0)) > 0 else 1.0,
                        "positionValue": 5.0, "unrealisedPnl": 0
                    })
                    # Add to local exchange_map immediately to prevent next loop iteration from thinking it's still missing
                    exchange_map[norm_symbol] = bybit_rest_service.paper_positions[-1]
                    continue

                if norm_symbol not in exchange_map:
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
            # V4.3.1: Use normalized symbols for comparison to avoid duplicates
            db_symbols_normalized = {bybit_rest_service._strip_p(s.get("symbol", "")): s["id"] for s in slots if s.get("symbol")}
            
            for symbol, pos in exchange_map.items():
                # V4.3.1: Check normalized symbol to prevent duplicates like ONDOUSDT.P vs ONDOUSDT
                if symbol in db_symbols_normalized:
                    continue  # Already exists, skip recovery
                
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
                # V4.3.1: Also update the normalized map
                db_symbols_normalized[symbol] = empty_slot["id"]

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
            side_norm = (side or "").lower()
            if side_norm == "buy":
                if stop and entry and stop >= entry:
                    is_risk_free = True
            elif side_norm == "sell":
                if stop and entry and stop <= entry:
                    is_risk_free = True
            
            if not is_risk_free:
                real_risk += self.margin_per_slot
        
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
        
        # 2. Slot Type Separation
        if slot_type == "SNIPER":
            type_slots = [s for s in slots if s["id"] <= 5]
            slot_range = range(1, 6)
        else:  # SURF
            type_slots = [s for s in slots if s["id"] >= 6]
            slot_range = range(6, 11)
        
        active_type_slots = [s for s in type_slots if s.get("symbol")]
        active_count = len(active_type_slots)
        
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
        for s in slots:
            if s["id"] in slot_range and not s.get("symbol"):
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
            # 0. Redundant Duplicate Guard
            active_slots = await firebase_service.get_active_slots()
            norm_symbol = bybit_rest_service._strip_p(symbol)
            if any(bybit_rest_service._strip_p(S.get("symbol")) == norm_symbol for S in active_slots if S.get("symbol")):
                logger.warning(f"Iron Lock: Redundant Guard blocked duplicate {symbol}.")
                return None

        # V4.2: Check if trading is allowed (Admiral's Rest, etc)
        async with self.execution_lock:
            trading_allowed, reason = await vault_service.is_trading_allowed()
            if not trading_allowed:
                logger.warning(f"Trading blocked: {reason}")
                await firebase_service.log_event("VAULT", f"Trade BLOCKED: {reason}", "WARNING")
                return None
            
            # V4.3: Check for duplication and limits (passing slot_type)
            slot_id = await self.can_open_new_slot(symbol=symbol, slot_type=slot_type)
            if not slot_id:
                return None
            
            # V4.3: slot_type is now a parameter, not derived from slot_id
            # V4.2: Check dynamic score threshold from vault (Cautious Mode)
            min_score = await vault_service.get_min_score_threshold()
            if min_score > 75:
                logger.info(f"Cautious Mode active: Min score threshold = {min_score}")

            # 1. Fetch Current Price
            ticker = await bybit_rest_service.get_tickers(symbol=symbol)
            current_price = float(ticker.get("result", {}).get("list", [{}])[0].get("lastPrice", 0))
            
            if current_price == 0:
                logger.error(f"Could not fetch price for {symbol}")
                await firebase_service.log_event("Captain", f"Trade FAILED: Could not fetch price for {symbol}.", "WARNING")
                return None

            # 2. Dynamic Qty calculation
            info = await asyncio.to_thread(bybit_rest_service.get_instrument_info, symbol)
            qty_step = float(info.get("lotSizeFilter", {}).get("qtyStep", 0.001))
            
            balance = await asyncio.to_thread(bybit_rest_service.get_wallet_balance)
            if balance < 10:
                logger.warning(f"Balance too low for trading: ${balance}")
                return None
                
            margin = balance * self.margin_per_slot # Exactly 5%
            leverage = settings.LEVERAGE # 50x
            raw_qty = (margin * leverage) / current_price
            
            # Round to qtyStep precision
            import math
            precision = max(0, int(-math.log10(qty_step))) if qty_step > 0 else 3
            qty = round(raw_qty, precision)
            if qty <= 0: qty = qty_step # Use minimum lot

            # 3. Final SL Safety Check - V4.5.1 Protocol Elite
            # SNIPER: SL = -50% ROI = 1% price movement @ 50x
            # SURF: SL = -75% ROI = 1.5% price movement @ 50x
            sniper_sl_percent = 0.01  # 1% price = -50% ROI @ 50x
            surf_sl_percent = 0.015   # 1.5% price = -75% ROI @ 50x
            
            sl_percent = sniper_sl_percent if slot_type == "SNIPER" else surf_sl_percent
            
            final_sl = sl_price
            if final_sl <= 0:
                if side == "Buy":
                    final_sl = current_price * (1 - sl_percent)
                else:
                    final_sl = current_price * (1 + sl_percent)
            
            # Validation: Ensure SL is on correct side
            if side == "Buy" and final_sl >= current_price: 
                final_sl = current_price * (1 - sl_percent)
            if side == "Sell" and final_sl <= current_price: 
                final_sl = current_price * (1 + sl_percent)
            
            logger.info(f"[{slot_type}] SL Calculated: {final_sl:.8f} ({sl_percent*100:.1f}% from {current_price:.8f})")
            
            # V4.2: SNIPER vs SURF TP
            final_tp = tp_price
            if slot_type == "SNIPER":
                if side == "Buy":
                    final_tp = current_price * (1 + self.sniper_tp_percent)
                else:
                    final_tp = current_price * (1 - self.sniper_tp_percent)
                logger.info(f"[SNIPER] Slot {slot_id}: TP set at {final_tp:.5f} | SL at {final_sl:.5f}")
            else:
                final_tp = None  # SURF: No TP
                logger.info(f"[SURF] Slot {slot_id}: No TP (Guardian Trailing) | Hard SL at {final_sl:.5f}")

            squadron_emoji = "🎯" if slot_type == "SNIPER" else "🏄"
            await firebase_service.log_event("Captain", f"{squadron_emoji} {slot_type} DEPLOYED: {side} {qty} {symbol} @ {current_price} | HARD STOP: {final_sl}", "SUCCESS")

            # Place Atomic Order
            try:
                order = await asyncio.wait_for(bybit_rest_service.place_atomic_order(symbol, side, qty, final_sl, final_tp), timeout=10.0)
            except Exception as e:
                logger.error(f"Timeout/Error placing order for {symbol}: {e}")
                order = None
            
            if order:
                await firebase_service.update_slot(slot_id, {
                    "symbol": symbol,
                    "side": side,
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

    async def register_sniper_win(self, trade_data: dict):
        """
        V4.2: Registra uma vitória Sniper no ciclo de 20 trades.
        Chamado pelo Position Reaper quando um trade SNIPER fecha com lucro.
        """
        try:
            slot_type = trade_data.get("slot_type", "SNIPER")
            pnl = trade_data.get("pnl", 0)
            
            # Only register if it's a SNIPER win
            if slot_type == "SNIPER" and pnl > 0:
                await vault_service.register_sniper_win(trade_data)
                logger.info(f"Sniper Win registered: {trade_data.get('symbol')} +${pnl:.2f}")
        except Exception as e:
            logger.error(f"Error registering sniper win: {e}")

bankroll_manager = BankrollManager()
