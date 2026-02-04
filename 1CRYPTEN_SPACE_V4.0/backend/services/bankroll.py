from __future__ import annotations
import logging
import asyncio
import time
import math
from typing import Optional, List, Dict, Any, Tuple
from services.firebase_service import firebase_service
from services.bybit_rest import bybit_rest_service
from services.vault_service import vault_service
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BankrollManager")

def get_slot_type(slot_id: int) -> str:
    """
    [V8.0] SINGLE ORDER SNIPER: Only SNIPER strategy is active.
    """
    return "SNIPER"

class BankrollManager:
    def __init__(self):
        self.max_slots = settings.MAX_SLOTS
        self.risk_cap = 0.20 
        self.margin_per_slot = 0.20 # 20% per slot (Single Sniper rule)
        self.initial_slots = 1
        self.last_log_times = {} # Cooldown for logs
        # V4.2: Sniper TP = +2% price = 100% ROI @ 50x
        self.sniper_tp_percent = 0.02  # 2% price movement
        self.execution_lock = asyncio.Lock() # Iron Lock Atomic Protector
        self.pending_slots = set() # V4.9.4.2: Local memory lock to prevent duplicate assignments

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

                # V4.2.6: Persistence Shield - Don't even touch if opened in the last 10 seconds
                entry_ts = slot.get("timestamp_last_update") or 0
                if (time.time() - entry_ts) < 10:
                     continue

                if norm_symbol in exchange_map:
                    # UPDATING ACTIVE SLOT WITH REAL EXCHANGE DATA
                    pos = exchange_map[norm_symbol]
                    real_margin = float(pos.get("positionIM", 0))
                    if real_margin <= 0:
                        real_margin = (float(pos.get("size", 0)) * float(pos.get("avgPrice", 0))) / 50
                    
                    unrealised_pnl = float(pos.get("unrealisedPnl", 0))
                    pnl_pct = (unrealised_pnl / real_margin * 100) if real_margin > 0 else 0
                    
                    await firebase_service.update_slot(slot_id, {
                        "entry_margin": real_margin,
                        "pnl_percent": pnl_pct,
                        "qty": float(pos.get("size", 0)),
                        "entry_price": float(pos.get("avgPrice", 0)),
                        "liq_price": float(pos.get("liqPrice", 0)),
                        "timestamp_last_update": time.time()
                    })
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
                        
                        # V5.2.3: Anti-Persistence Loop Guard
                        # Check if slot was updated (reset) in the last 15 seconds to avoid re-adoption race condition
                        if (time.time() - entry_ts) < 15:
                            logger.info(f"Sync [PAPER]: Slot {slot_id} recently updated/reset. Skipping re-adoption guard.")
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
                        logger.warning(f"Sync [REAL]: Detected closed position for {symbol} in Slot {slot_id}")
                        
                        # V5.2.2: Register closed trade before clearing slot
                        try:
                            # Fetch last closed PnL for this symbol
                            closed_list = await bybit_rest_service.get_closed_pnl(symbol=symbol, limit=1)
                            if closed_list:
                                last_pnl = closed_list[0]
                                pnl_val = float(last_pnl.get("closedPnl", 0))
                                exit_price = float(last_pnl.get("avgExitPrice", 0))
                                qty = float(last_pnl.get("qty", 0))
                                
                                trade_data = {
                                    "symbol": symbol,
                                    "side": slot.get("side"),
                                    "entry_price": float(slot.get("entry_price", 0)),
                                    "exit_price": exit_price,
                                    "qty": qty,
                                    "pnl": pnl_val,
                                    "slot_id": slot_id,
                                    "slot_type": get_slot_type(slot_id),
                                    "close_reason": "EXCHANGE_SYNC_DETECTED"
                                }
                                
                                # 1. Log to history
                                await firebase_service.log_trade(trade_data)
                                
                                # 2. Register in Vault (Cycle)
                                await self.register_sniper_trade(trade_data)
                                
                                logger.info(f"Sync [REAL]: Trade registered for {symbol} | PnL: ${pnl_val:.2f}")
                        except Exception as pnl_err:
                            logger.error(f"Sync [REAL]: Error fetching closed PnL for {symbol}: {pnl_err}")

                        logger.warning(f"Sync [REAL]: Clearing stale slot {slot_id} for {symbol}")
                        await firebase_service.update_slot(slot_id, {
                            "symbol": None, "entry_price": 0, "current_stop": 0, "entry_margin": 0,
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
                    "entry_margin": float(pos.get("positionIM", 0)),
                    "current_stop": float(pos.get("stopLoss", 0)),
                    "status_risco": "RECOVERED",
                    "slot_type": get_slot_type(empty_slot["id"]), # V5.4.5: Ensure correct logic type
                    "pnl_percent": float(pos.get("unrealisedPnl", 0)) / float(pos.get("positionIM", 1)) * 100 if float(pos.get("positionIM", 0)) > 0 else 0,
                    "qty": float(pos.get("size", 0)),
                    "opened_at": time.time(), # Fallback for recovery
                    "liq_price": float(pos.get("liqPrice", 0)),
                    "timestamp_last_update": time.time()
                })
                # Refresh local list
                slots = await firebase_service.get_active_slots()

            await firebase_service.log_event("Bankroll", f"Sync Complete. Active: {len(active_symbols)}", "SUCCESS")

        except Exception as e:
            logger.error(f"Error during slot sync: {e}")


    async def calculate_real_risk(self):
        """
        Calculates the real risk for the single Sniper slot.
        """
        slots = await firebase_service.get_active_slots()
        real_risk = 0.0
        
        # Only slot 1 matters
        slot = next((s for s in slots if s["id"] == 1), None)
        if slot and slot.get("symbol"):
            entry = slot.get("entry_price")
            stop = slot.get("current_stop")
            side = slot.get("side")
            side_norm = (side or "").upper()
            
            is_risk_free = False
            if side_norm == "BUY" and stop and entry and stop >= entry:
                is_risk_free = True
            elif side_norm == "SELL" and stop and entry and stop <= entry:
                is_risk_free = True
            
            if not is_risk_free:
                real_risk = self.margin_per_slot
        
        # Add pending risk if any
        if self.pending_slots:
            real_risk = self.margin_per_slot
        
        return real_risk

    async def can_open_new_slot(self, symbol: str = None, slot_type: str = "SNIPER") -> Optional[int]:
        """
        [V7.0] SINGLE TRADE SNIPER RULE:
        Strictly allows opening a slot ONLY if ALL slots are empty.
        Always returns slot 1 as the primary sniper slot.
        """
        try:
            slots = await firebase_service.get_active_slots()
            occupied = [s for s in slots if s.get("symbol")]
            
            if len(occupied) > 0:
                logger.info(f"🚫 SINGLE SNIPER RULE: Waiting for {occupied[0]['symbol']} to close.")
                return None
            
            # Atomic Lock Check
            if self.pending_slots:
                 logger.warning(f"Atomic Lock: System already processing a trade. BLOCKED.")
                 return None

            # Check if this symbol is already the one being processed
            if symbol:
                norm_symbol = symbol.replace(".P", "").upper()
                if any(p_sym == norm_symbol for p_sym, p_id in self.pending_slots):
                     return None

            # If empty, return slot 1 as the designated Sniper slot
            return 1
            
        except Exception as e:
            logger.error(f"Error checking slot availability: {e}")
            return None

    async def update_banca_status(self):
        """Updates the banca_status table in Supabase."""
        try:
            real_risk = await self.calculate_real_risk()
            slots = await firebase_service.get_active_slots()
            available_slots_count = sum(1 for s in slots if s["symbol"] is None)
            
            # Fetch real balance from Bybit - NON-BLOCKING
            total_equity = await bybit_rest_service.get_wallet_balance()
            
            banca = await firebase_service.get_banca_status()
            if banca:
                # V5.2.2: Calculate Cumulative Profit from All Trades
                trades = await firebase_service.get_trade_history(limit=1000)
                # V6.0: PnL Summation Guard - Filter extreme outliers (e.g. from naming collisions)
                # Cap individual trade impact on visual total to prevent dashboard breakage
                total_pnl = sum(t.get("pnl", 0) for t in trades if abs(t.get("pnl", 0)) < 2000)
                
                # [V5.2.5] Fetch cycle-specific data from Vault Service
                vault_status = await vault_service.get_cycle_status()
                cycle_profit = vault_status.get("cycle_profit", 0)
                vault_total = vault_status.get("vault_total", 0)
                
                # [V8.1] Preserve configured_balance if set by user
                config_bal = banca.get("configured_balance")
                update_data = {
                    "id": banca.get("id", "status"),
                    "saldo_real_bybit": total_equity,  # Real balance from Bybit
                    "risco_real_percent": real_risk,
                    "slots_disponiveis": available_slots_count,
                    "lucro_total_acumulado": total_pnl,
                    "lucro_ciclo": cycle_profit,
                    "vault_total": vault_total,
                    "saldo_total": config_bal if config_bal else total_equity
                }
                await firebase_service.update_banca_status(update_data)
                
                # Snapshot logging: Log once every 6 hours (approx)
                if not hasattr(self, "_last_snapshot_time"):
                    self._last_snapshot_time = 0
                
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
        """[V8.0] Executes Single Sniper entry on Slot 1."""
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
            ticker_list = ticker.get("result", {}).get("list", [])
            if not ticker_list:
                logger.error(f"Could not fetch exact price for {symbol} (Match Failed)")
                return None
            
            current_price = float(ticker_list[0].get("lastPrice", 0))
            
            if current_price == 0:
                logger.error(f"Could not fetch price for {symbol}")
                return None

            info = await bybit_rest_service.get_instrument_info(symbol)
            if not info:
                logger.error(f"Could not fetch instrument info for {symbol}")
                return None
            
            # [V8.0] Strict 50x Leverage Guard
            max_lev = float(info.get("leverageFilter", {}).get("maxLeverage", 0))
            if max_lev != 50.0:
                logger.warning(f"🚫 STRATEGY BLOCK: {symbol} has {max_lev}x max leverage. Only 50x pairs allowed.")
                return None

            qty_step = float(info.get("lotSizeFilter", {}).get("qtyStep", 0.001))
            
            # [V8.1] Prioritize User's Configured Bankroll over real balance
            status = await firebase_service.get_banca_status()
            config_balance = status.get("configured_balance", 0)  # User's manual setting
            real_balance = status.get("saldo_real_bybit", 0) or await bybit_rest_service.get_wallet_balance()
            
            if config_balance >= 20:
                balance = config_balance
                logger.info(f"📊 Using User's Configured Bankroll: ${balance:.2f} (Real: ${real_balance:.2f})")
            else:
                balance = real_balance
                logger.info(f"📊 No configured balance. Using Real Bybit Balance: ${balance:.2f}")

            if balance < 20:
                logger.warning(f"❌ BANKROLL BELOW V8.0 MINIMUM ($20): ${balance:.2f}. Blocked.")
                return None
                
            # [V8.0] STRATEGY: 20% Margin Rule
            # Every trade uses exactly 20% of the current bankroll.
            # Min bankroll $20 => Min margin $4.
            margin = balance * 0.20
            
            if margin < 4.0:
                 margin = 4.0 # Force minimum operational margin if balance allows
            
            if margin < 1.0:
                logger.warning(f"❌ Balance too low for 20% margin trade: ${balance:.2f}")
                return False
            
            # [V8.1] Calculate final SL - 1% Stop-Loss Rule (Cross Margin)
            sl_percent = 0.01  # 1% Stop-Loss for all Sniper trades
            final_sl = sl_price if sl_price > 0 else (current_price * (1 - sl_percent) if side == "Buy" else current_price * (1 + sl_percent))
            
            # Calculate Qty based on fixed margin and leverage
            # Formula: margin = (qty * price) / leverage => qty = (margin * leverage) / price
            raw_qty = (margin * settings.LEVERAGE) / current_price

            # [V5.4.5] Margin calculation for slot record
            margin = (raw_qty * current_price) / settings.LEVERAGE

            precision = max(0, int(-math.log10(qty_step))) if qty_step > 0 else 3
            qty = round(raw_qty, precision)
            if qty <= 0: qty = qty_step
            
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
                    "entry_margin": margin,
                    "current_stop": final_sl,
                    "target_price": final_tp,
                    "slot_type": slot_type,
                    "status_risco": "ATIVO",
                    "pnl_percent": 0.0,
                    "pensamento": pensamento,
                    "opened_at": time.time(),
                    "liq_price": 0, # Sync will update this
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
        V4.2/V4.3.1: Registra um trade no ciclo (Sniper ou Surf).
        Chamado pelo Position Reaper quando um trade fecha.
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
            logger.error(f"Error registering trade in vault: {e}")

bankroll_manager = BankrollManager()
