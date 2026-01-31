import logging
import asyncio
import time
from pybit.unified_trading import HTTP
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BybitREST")

class BybitREST:
    def __init__(self):
        self._session = None
        self.category = settings.BYBIT_CATEGORY
        self.time_offset = 0
        
        # Paper Trading State
        self.execution_mode = settings.BYBIT_EXECUTION_MODE # "REAL" or "PAPER"
        self.paper_balance = settings.BYBIT_SIMULATED_BALANCE
        self.paper_positions = [] # List of dicts matching Bybit schema
        self.paper_orders_history = [] 
        self._paper_engine_task = None
    def _strip_p(self, symbol: str) -> str:
        """Strips the .P suffix for Bybit API calls."""
        if not symbol: return symbol
        return symbol.replace(".P", "")

    @property
    def session(self):
        """Lazy initialization of the Bybit HTTP session with time synchronization."""
        if self._session is None:
            # First, create a temporary session to fetch server time
            temp_session = HTTP(testnet=settings.BYBIT_TESTNET)
            try:
                import time
                local_start = int(time.time() * 1000)
                server_time_resp = temp_session.get_server_time()
                server_time = int(server_time_resp.get("result", {}).get("timeSecond", 0)) * 1000
                if server_time == 0: 
                    server_time = int(int(server_time_resp.get("result", {}).get("timeNano", 0)) / 1000000)
                
                if server_time > 0:
                    self.time_offset = server_time - local_start
                    logger.info(f"Bybit Time Sync: Offset detected as {self.time_offset}ms. Applying patch...")
                    
                    # Monkeypatch pybit's internal helper to use synced time
                    # This is the most robust way to solve 10002 without touching local OS time
                    import pybit._helpers as pybit_helpers
                    _orig_time = time.time
                    def synced_timestamp():
                        # pybit's generate_timestamp uses time.time() * 10**3
                        return int((_orig_time() + (self.time_offset / 1000.0)) * 1000)
                    
                    pybit_helpers.generate_timestamp = synced_timestamp
                    logger.info("Bybit Time Patch applied to pybit._helpers.generate_timestamp")
            except Exception as e:
                logger.error(f"Failed to sync time with Bybit: {e}")

            self._session = HTTP(
                testnet=settings.BYBIT_TESTNET,
                api_key=settings.BYBIT_API_KEY.strip() if settings.BYBIT_API_KEY else None,
                api_secret=settings.BYBIT_API_SECRET.strip() if settings.BYBIT_API_SECRET else None,
                recv_window=30000,
            )


        return self._session
    def get_top_200_usdt_pairs(self):
        """Optimized: Fetches top USDT pairs by 24h turnover and filters by leverage >= 50x (USDT.P Focused)."""
        try:
            # 1. Fetch ALL instruments info in one batch (HIGH SPEED)
            logger.info("BybitREST: Fetching all linear instruments for 50x+ Sniper territory...")
            instr_resp = self.session.get_instruments_info(category="linear")
            instr_list = instr_resp.get("result", {}).get("list", [])
            logger.info(f"BybitREST: Received {len(instr_list)} instruments from Bybit.")
            
            # 2. Filter by USDT suffix AND leverage >= 50x
            candidates = {}
            for info in instr_list:
                symbol = info.get("symbol")
                if not symbol or not symbol.endswith("USDT"):
                    continue
                
                max_lev = float(info.get("leverageFilter", {}).get("maxLeverage", 0))
                if max_lev >= 50:
                    candidates[symbol] = info
            
            logger.info(f"BybitREST: Found {len(candidates)} candidates with 50x+ leverage.")
            
            # 3. Get tickers to sort by turnover
            logger.info("BybitREST: Fetching tickers for turnover sorting...")
            tickers_resp = self.session.get_tickers(category="linear")
            ticker_list = tickers_resp.get("result", {}).get("list", [])
            
            # 4. Join and sort
            final_candidates = []
            for t in ticker_list:
                sym = t.get("symbol")
                if sym in candidates:
                    final_candidates.append({
                        "symbol": sym,
                        "turnover": float(t.get("turnover24h", 0))
                    })
            
            # Sort by turnover
            final_candidates.sort(key=lambda x: x["turnover"], reverse=True)
            
            # Take top candidates (Usually around 75-80 meet 50x criteria)
            # Add .P suffix to identify as Perpetuals
            final_symbols = [f"{x['symbol']}.P" for x in final_candidates]
            
            logger.info(f"BybitREST: Operation Sniper successful. Monitored: {len(final_symbols)} Elite 50x+ USDT.P Symbols.")
            return final_symbols
        except Exception as e:
            logger.error(f"Error in Operation Sniper scan: {e}")
            logger.exception(e)
            return ["BTCUSDT.P", "ETHUSDT.P", "SOLUSDT.P"]

    def get_wallet_balance(self):
        """Fetches the total equity from the Bybit account (UNIFIED or CONTRACT)."""
        logger.info(f"[DEBUG] get_wallet_balance called. Mode: {self.execution_mode}")
        if self.execution_mode == "PAPER":
             # Calculate unrealized PNL from active paper positions to show dynamic equity
             unrealized_pnl = 0.0
             # Note: Accurate unrealized PNL requires fetching current prices. 
             # For performance, we might just return static balance + realized, 
             # OR realistically we should update it.
             # Ideally bankroll manager handles this via slots PNL, but here we return raw wallet balance.
             return self.paper_balance

        try:
            # Try UNIFIED first
            logger.info("Fetching balance (UNIFIED)...")
            try:
                response = self.session.get_wallet_balance(accountType="UNIFIED")
                result = response.get("result", {}).get("list", [{}])[0]
                equity = float(result.get("totalEquity", 0))
                logger.info(f"UNIFIED Equity: {equity}")
                if equity > 0: return equity
            except Exception as ue: 
                logger.warning(f"UNIFIED balance fetch failed: {ue}")
            
            # Try CONTRACT if UNIFIED fails or is 0
            logger.info("Fetching balance (CONTRACT)...")
            response = self.session.get_wallet_balance(accountType="CONTRACT")
            result = response.get("result", {}).get("list", [{}])[0]
            coins = result.get("coin", [])
            usdt_coin = next((c for c in coins if c.get("coin") == "USDT"), {})
            equity = float(usdt_coin.get("equity", 0))
            logger.info(f"CONTRACT Equity: {equity}")
            return equity
        except Exception as e:
            logger.error(f"Error fetching wallet balance: {e}")
            return 0.0

    async def get_active_positions(self, symbol: str = None):
        """Fetches currently open linear positions (Real or Simulated)."""
        if self.execution_mode == "PAPER":
            if symbol:
                return [p for p in self.paper_positions if p["symbol"] == symbol]
            return self.paper_positions

        try:
            params = {"category": self.category, "settleCoin": "USDT"}
            if symbol: params["symbol"] = symbol
            
            response = await asyncio.to_thread(self.session.get_positions, **params)
            pos_list = response.get("result", {}).get("list", [])
            # Filter for positions with size > 0
            active = [p for p in pos_list if float(p.get("size", 0)) > 0]
            return active
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return []

    async def get_tickers(self, symbol: str = None):
        """Fetches ticker data for a symbol (v5 category linear)."""
        try:
            api_symbol = self._strip_p(symbol)
            params = {"category": self.category}
            if api_symbol: params["symbol"] = api_symbol
            return await asyncio.to_thread(self.session.get_tickers, **params)
        except Exception as e:
            logger.error(f"Error fetching tickers for {symbol}: {e}")
            return {}

    def get_instrument_info(self, symbol: str):
        """Fetches precision and lot size filtering for a symbol."""
        try:
            api_symbol = self._strip_p(symbol)
            response = self.session.get_instruments_info(category="linear", symbol=api_symbol)
            return response.get("result", {}).get("list", [{}])[0]
        except Exception as e:
            logger.error(f"Error fetching instrument info for {symbol}: {e}")
            return {}




    async def place_atomic_order(self, symbol: str, side: str, qty: float, sl_price: float, tp_price: float = None):
        """
        Sends a Market Order with Stop Loss in the same request.
        This is the Lv 0 Sniper execution.
        """
        if self.execution_mode == "PAPER":
            logger.info(f"[PAPER] Simulating Atomic Order: {side} {qty} {symbol} @ MARKET")
            # 1. Get current price for entry simulation
            api_symbol = self._strip_p(symbol)
            try:
                # Need to fetch real price to simulate entry
                ticker = await asyncio.to_thread(self.session.get_tickers, category="linear", symbol=api_symbol)
                last_price = float(ticker.get("result", {}).get("list", [{}])[0].get("lastPrice", 0))
                
                if last_price == 0:
                    raise Exception("Could not fetch price for paper execution")

                # 2. Create Position Object (Mocking Bybit Schema)
                new_position = {
                    "symbol": api_symbol, # Normalized
                    "side": side,
                    "size": str(qty),
                    "avgPrice": str(last_price),
                    "leverage": str(settings.LEVERAGE if hasattr(settings, 'LEVERAGE') else 50),
                    "stopLoss": str(sl_price),
                    "takeProfit": str(tp_price) if tp_price else "",
                    "createdTime": "123456789" # Mock timestamp
                }
                
                # Check if position already exists (Hedge mode not supported in paper simple impl, assuming One-Way)
                # If exists, we should technically add size/avg down, but for simplicity we reject or replace?
                # Let's simple append or replace.
                existing = next((p for p in self.paper_positions if p["symbol"] == api_symbol), None)
                if existing:
                    logger.warning(f"[PAPER] Overwriting existing position for {api_symbol} (Simpler than averaging).")
                    self.paper_positions.remove(existing)
                
                self.paper_positions.append(new_position)
                logger.info(f"[PAPER] Position Created: {api_symbol} Entry={last_price}")
                
                # Return fake order response
                return {
                    "retCode": 0,
                    "result": {"orderId": f"PAPER-{api_symbol}-123", "orderLinkId": f"PAPER-{api_symbol}-123"}
                }

            except Exception as e:
                logger.error(f"[PAPER] Failed to place simulated order: {e}")
                return None

        try:
            api_symbol = self._strip_p(symbol)
            order_params = {
                "category": self.category,
                "symbol": api_symbol,
                "side": side,
                "orderType": "Market",
                "qty": str(qty),
                "stopLoss": str(sl_price),
                "tpTriggerBy": "LastPrice",
                "slTriggerBy": "LastPrice",
                "tpslMode": "Full", # Use Full T/SL mode
            }
            if tp_price:
                order_params["takeProfit"] = str(tp_price)

            response = await asyncio.to_thread(self.session.place_order, **order_params)
            logger.info(f"Atomic order placed for {symbol}: {response}")
            return response
        except Exception as e:
            logger.error(f"Failed to place atomic order for {symbol}: {e}")
            return None

    async def close_position(self, symbol: str, side: str, qty: float):
        """Closes a position at market."""
        if self.execution_mode == "PAPER":
            logger.info(f"[PAPER] Closing position {symbol}")
            # Find position
            pos = next((p for p in self.paper_positions if p["symbol"] == symbol), None)
            if pos:
                # Calculate Realized PNL to update Paper Balance
                try:
                    from services.execution_protocol import execution_protocol
                    api_symbol = self._strip_p(symbol)
                    ticker = await asyncio.to_thread(self.session.get_tickers, category="linear", symbol=api_symbol)
                    exit_price = float(ticker.get("result", {}).get("list", [{}])[0].get("lastPrice", 0))
                    
                    entry_price = float(pos["avgPrice"])
                    size = float(pos["size"])
                    leverage = float(pos.get("leverage", 50))
                    side = pos["side"]

                    final_pnl = execution_protocol.calculate_pnl(entry_price, exit_price, size, side)
                    
                    self.paper_balance += final_pnl
                    self.paper_orders_history.append({
                        "symbol": symbol,
                        "side": side,
                        "avgEntryPrice": str(entry_price),
                        "avgExitPrice": str(exit_price),
                        "closedPnl": str(final_pnl),
                        "leverage": str(leverage),
                        "qty": str(size),
                        "updatedTime": str(int(time.time() * 1000))
                    })
                    
                    if pos in self.paper_positions:
                        self.paper_positions.remove(pos)
                    logger.info(f"[PAPER] Closed {symbol}. PNL: ${final_pnl:.2f}. New Balance: ${self.paper_balance:.2f}")
                    return {"retCode": 0}
                except Exception as e:
                    logger.error(f"[PAPER] Error during position closure: {e}")
                    if pos in self.paper_positions:
                        self.paper_positions.remove(pos)
                    return {"retCode": 0}
            return {"retCode": 0}

        try:
            # Side is the current position side, so we sell to close a long
            api_symbol = self._strip_p(symbol)
            close_side = "Sell" if side == "Buy" else "Buy"
            response = await asyncio.to_thread(self.session.place_order,
                category=self.category,
                symbol=api_symbol,
                side=close_side,
                orderType="Market",
                qty=str(qty),
                reduceOnly=True
            )
            return response
        except Exception as e:
            logger.error(f"Error closing position for {symbol}: {e}")
            return None

    def get_closed_pnl(self, symbol: str, limit: int = 1):
        """Fetches final PnL for closed trades."""
        if self.execution_mode == "PAPER":
            # Filter history by symbol
            relevant = [h for h in self.paper_orders_history if h["symbol"] == symbol]
            # Return last N
            return relevant[-limit:] if relevant else []

        try:
            api_symbol = self._strip_p(symbol)
            response = self.session.get_closed_pnl(category=self.category, symbol=api_symbol, limit=limit)
            return response.get("result", {}).get("list", [])
        except Exception as e:
            logger.error(f"Error fetching closed PnL for {symbol}: {e}")
            return []

    def get_klines(self, symbol: str, interval: str = "60", limit: int = 20):
        """Fetches historical klines for ATR and variation calculations."""
        try:
            api_symbol = self._strip_p(symbol)
            response = self.session.get_mark_price_kline(
                category=self.category,
                symbol=api_symbol,
                interval=interval,
                limit=limit
            )
            return response.get("result", {}).get("list", [])
        except Exception as e:
            logger.error(f"Error fetching klines for {symbol}: {e}")
            return []

    
    async def set_trading_stop(self, category: str, symbol: str, stopLoss: str, slTriggerBy: str = None, tpslMode: str = None, positionIdx: int = 0):
        """Sets the stop loss for a position."""
        if self.execution_mode == "PAPER":
            api_symbol = self._strip_p(symbol)
            logger.info(f"[PAPER] Updating Stop Loss for {api_symbol} to {stopLoss}")
            pos = next((p for p in self.paper_positions if p["symbol"] == api_symbol), None)
            if pos:
                pos["stopLoss"] = str(stopLoss)
                return {"retCode": 0, "result": {}}
            else:
                return {"retCode": 10001, "retMsg": f"Position {api_symbol} not found in Paper Trading"}

        try:
            api_symbol = self._strip_p(symbol)
            params = {
                "category": category,
                "symbol": api_symbol,
                "stopLoss": stopLoss,
                "positionIdx": positionIdx
            }
            if slTriggerBy: params["slTriggerBy"] = slTriggerBy
            if tpslMode: params["tpslMode"] = tpslMode
            
            response = await asyncio.to_thread(self.session.set_trading_stop, **params)
            return response
        except Exception as e:
            logger.error(f"Error setting SL for {symbol}: {e}")
            return {"retCode": -1, "retMsg": str(e)}

    async def run_paper_execution_loop(self):
        """
        V4.3.1: Engine de execução blindada para modo PAPER.
        Usa ExecutionProtocol para decisões ROI-based e sincroniza com Firebase.
        Intervalo reduzido para 1s para captura de 100% ROI em SNIPER.
        """
        if self.execution_mode != "PAPER":
            return

        # Import here to avoid circular imports
        from services.execution_protocol import execution_protocol
        from services.firebase_service import firebase_service

        logger.info("🚀 V4.3.1 Paper Execution Engine (Blindagem de Execução) ACTIVATING...")
        logger.info(f"   - Loop Interval: 1 second (Fast SNIPER capture)")
        logger.info(f"   - SNIPER Target: {execution_protocol.sniper_target_roi}% ROI")
        logger.info(f"   - SURF Trailing: Escada de Proteção Ativa")
        
        while True:
            try:
                if not self.paper_positions:
                    await asyncio.sleep(2)  # Slightly longer sleep when no positions
                    continue

                # 1. Batch fetch tickers for efficiency
                symbols_to_check = [p["symbol"] for p in self.paper_positions]
                resp = await asyncio.to_thread(self.session.get_tickers, category="linear")
                ticker_list = resp.get("result", {}).get("list", [])
                price_map = {t["symbol"]: float(t.get("lastPrice", 0)) for t in ticker_list}

                # 2. Get Firebase slots for correlation
                slots = await firebase_service.get_active_slots()
                slots_by_symbol = {}
                for s in slots:
                    sym = s.get("symbol")
                    if sym:
                        norm_sym = self._strip_p(sym)
                        slots_by_symbol[norm_sym] = s

                to_close = []
                to_update_sl = []

                # 3. Process each position with ExecutionProtocol
                for pos in self.paper_positions:
                    symbol = pos["symbol"]  # Already normalized (no .P)
                    current_price = price_map.get(symbol, 0)
                    if current_price == 0: 
                        continue

                    # Find matching Firebase slot
                    slot = slots_by_symbol.get(symbol)
                    if not slot:
                        # Try to find by similar symbol patterns
                        for sym_key, slot_data in slots_by_symbol.items():
                            if sym_key == symbol or symbol.startswith(sym_key) or sym_key.startswith(symbol):
                                slot = slot_data
                                break
                    
                    # Build slot_data for ExecutionProtocol
                    slot_data = {
                        "symbol": symbol,
                        "side": pos.get("side", "Buy"),
                        "entry_price": float(pos.get("avgPrice", 0)),
                        "current_stop": float(pos.get("stopLoss", 0)) if pos.get("stopLoss") else 0,
                        "target_price": float(pos.get("takeProfit", 0)) if pos.get("takeProfit") else 0,
                        "slot_type": slot.get("slot_type", "SNIPER") if slot else "SNIPER",
                        "slot_id": slot.get("id") if slot else None
                    }

                    # 4. Execute Protocol Logic
                    should_close, reason, new_sl = execution_protocol.process_order_logic(slot_data, current_price)

                    if should_close:
                        logger.info(f"🎯 [PAPER] CLOSE TRIGGERED: {symbol} | Reason: {reason} | Price: {current_price}")
                        to_close.append({
                            "symbol": symbol,
                            "side": pos["side"],
                            "size": float(pos["size"]),
                            "reason": reason,
                            "slot_id": slot_data.get("slot_id"),
                            "entry_price": slot_data["entry_price"],
                            "exit_price": current_price
                        })
                    elif new_sl is not None:
                        # Update trailing stop
                        to_update_sl.append((symbol, new_sl, slot_data.get("slot_id")))

                # 5. Execute closures with Firebase sync
                for close_data in to_close:
                    sym = close_data["symbol"]
                    side = close_data["side"]
                    size = close_data["size"]
                    slot_id = close_data.get("slot_id")
                    
                    # Close position (this updates paper_balance)
                    await self.close_position(sym, side, size)
                    
                    # Reset Firebase slot atomically
                    if slot_id:
                        # Calculate accurate PNL
                        entry = close_data["entry_price"]
                        exit_price = close_data["exit_price"]
                        side = close_data["side"]
                        
                        pnl = execution_protocol.calculate_pnl(entry, exit_price, size, side)
                        
                        trade_data = {
                            "symbol": sym,
                            "side": side,
                            "entry_price": entry,
                            "exit_price": exit_price,
                            "qty": size,
                            "slot_id": slot_id
                        }
                        
                        await firebase_service.hard_reset_slot(slot_id, close_data["reason"], pnl, trade_data)
                        
                        # V5.2.3: Notify bankroll/vault for statistics sync
                        try:
                            from services.bankroll import bankroll_manager
                            await bankroll_manager.register_sniper_trade({
                                **trade_data,
                                "pnl": pnl,
                                "pnl_percent": (pnl / (close_data["entry_price"] * size / 50)) * 100 if size > 0 else 0, # Rough ROI estimate
                                "slot_type": slot_data["slot_type"]
                            })
                        except Exception as e:
                            logger.error(f"[PAPER] Failed to notify bankroll of trade closure: {e}")

                        logger.info(f"✅ [PAPER] Slot {slot_id} FREED | {sym} | PNL: ${pnl:.2f} | New Balance: ${self.paper_balance:.2f}")

                # 6. Update trailing stops in Firebase
                for sym, new_sl, slot_id in to_update_sl:
                    # Update paper position
                    pos = next((p for p in self.paper_positions if p["symbol"] == sym), None)
                    if pos:
                        pos["stopLoss"] = str(new_sl)
                    
                    # Update Firebase
                    if slot_id:
                        await firebase_service.update_slot(slot_id, {"current_stop": new_sl})

            except Exception as e:
                logger.error(f"Error in Paper Execution Engine V4.3.1: {e}", exc_info=True)
            
            # V4.3.1: Fast loop interval for SNIPER 100% ROI capture
            await asyncio.sleep(1)

bybit_rest_service = BybitREST()

