import asyncio
import logging
import time
import json
import os
from pybit.unified_trading import HTTP
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BybitREST")

class BybitREST:
    def __init__(self):
        self._session = None
        self.category = settings.BYBIT_CATEGORY
        self.time_offset = 0
        self.is_initialized = False
        
        # Paper Trading State
        self.execution_mode = settings.BYBIT_EXECUTION_MODE # "REAL" or "PAPER"
        self.paper_balance = settings.BYBIT_SIMULATED_BALANCE
        self.paper_positions = [] # List of dicts matching Bybit schema
        self.paper_orders_history = [] 
        self._paper_engine_task = None
        self._instrument_cache = {} # Cache for tickSize and stepSize
        self.last_balance = 0.0 # V5.2.4.6: Cache for non-blocking health checks
        self.PAPER_STORAGE_FILE = "paper_storage.json"
        
        # V5.3.4: Closure Idempotency Shield
        self.pending_closures = set()
        # V5.4.0: Distributed Lock via RedisService
        from services.redis_service import redis_service
        self.redis = redis_service

    def _load_paper_state(self):
        """Loads paper positions and balance from disk."""
        if self.execution_mode != "PAPER": return
        try:
            if os.path.exists(self.PAPER_STORAGE_FILE):
                with open(self.PAPER_STORAGE_FILE, 'r') as f:
                    data = json.load(f)
                    self.paper_positions = data.get("positions", [])
                    self.paper_balance = data.get("balance", settings.BYBIT_SIMULATED_BALANCE)
                    self.paper_orders_history = data.get("history", [])
                logger.info(f"📂 [PAPER] State loaded. Positions: {len(self.paper_positions)} | Balance: ${self.paper_balance:.2f}")
            else:
                logger.info("📂 [PAPER] No storage file found. Starting fresh.")
        except Exception as e:
            logger.error(f"❌ [PAPER] Failed to load state: {e}")

    def _save_paper_state(self):
        """Saves paper positions and balance to disk."""
        if self.execution_mode != "PAPER": return
        try:
            data = {
                "positions": self.paper_positions,
                "balance": self.paper_balance,
                "history": self.paper_orders_history[-50:] # Keep last 50 only
            }
            with open(self.PAPER_STORAGE_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            # logger.debug("💾 [PAPER] State saved.")
        except Exception as e:
            logger.error(f"❌ [PAPER] Failed to save state: {e}")

    def normalize_symbol(self, symbol: str) -> str:
        """
        [V6.0] Robust Mapping: Standardizes symbols for Bybit V5 API.
        Strips .P suffix, ensures upper case, and prevents common mapping errors.
        """
        if not symbol: return ""
        norm = symbol.strip().upper()
        if norm.endswith(".P"):
            norm = norm[:-2]
        
        # Security Guard: Ensure it ends with USDT (or USDC)
        if not (norm.endswith("USDT") or norm.endswith("USDC")):
            # Fallback: if it's just 'BTC', return 'BTCUSDT'
            if norm: norm = f"{norm}USDT"
            
        return norm

    def _strip_p(self, symbol: str) -> str:
        """Standardizes symbols for Bybit API calls."""
        return self.normalize_symbol(symbol)

    async def initialize(self):
        """Asynchronously initializes the Bybit session and synchronizes time."""
        if self.is_initialized:
            return

        logger.info("BybitREST: Initializing session and time sync...")
        
        # Create a temporary session to fetch server time
        temp_session = HTTP(testnet=settings.BYBIT_TESTNET)
        try:
            local_start = int(time.time() * 1000)
            server_time_resp = await asyncio.to_thread(temp_session.get_server_time)
            server_time = int(server_time_resp.get("result", {}).get("timeSecond", 0)) * 1000
            if server_time == 0: 
                server_time = int(int(server_time_resp.get("result", {}).get("timeNano", 0)) / 1000000)
            
            if server_time > 0:
                self.time_offset = server_time - local_start
                logger.info(f"Bybit Time Sync: Offset detected as {self.time_offset}ms. Applying patch...")
                
                # Monkeypatch pybit's internal helper to use synced time
                import pybit._helpers as pybit_helpers
                _orig_time = time.time
                def synced_timestamp():
                    return int((_orig_time() + (self.time_offset / 1000.0)) * 1000)
                
                pybit_helpers.generate_timestamp = synced_timestamp
                logger.info("Bybit Time Patch applied successfully.")
        except Exception as e:
            logger.error(f"Failed to sync time with Bybit: {e}")

        # Create the actual session
        self._session = HTTP(
            testnet=settings.BYBIT_TESTNET,
            api_key=settings.BYBIT_API_KEY.strip() if settings.BYBIT_API_KEY else None,
            api_secret=settings.BYBIT_API_SECRET.strip() if settings.BYBIT_API_SECRET else None,
            recv_window=30000,
        )
        self.is_initialized = True
        logger.info("BybitREST: Session initialized.")
        
        # Load Paper State on startup
        if self.execution_mode == "PAPER":
            self._load_paper_state()


    @property
    def session(self):
        """Returns the Bybit HTTP session. Ensure initialize() was called before use for best results."""
        if self._session is None:
            # Fallback for synchronous calls, though initialize() is preferred
            self._session = HTTP(
                testnet=settings.BYBIT_TESTNET,
                api_key=settings.BYBIT_API_KEY.strip() if settings.BYBIT_API_KEY else None,
                api_secret=settings.BYBIT_API_SECRET.strip() if settings.BYBIT_API_SECRET else None,
                recv_window=30000,
            )
        return self._session
    def get_elite_50x_pairs(self):
        """
        🚀 REFINAMENTO ESTRATÉGICO V6.0: Escaneia apenas pares com alavancagem >= 50x.
        Foca nos ~85 pares de elite da Bybit para maximizar precisão e liquidez.
        """
        try:
            # 1. Fetch ALL instruments info
            logger.info("BybitREST: Fetching Elite 50x+ Instruments (Sniper Strategy)...")
            instr_resp = self.session.get_instruments_info(category="linear")
            instr_list = instr_resp.get("result", {}).get("list", [])
            
            # 2. Filter by USDT suffix AND leverage >= 50x
            candidates = {}
            for info in instr_list:
                symbol = info.get("symbol")
                if not symbol or not symbol.endswith("USDT"):
                    continue
                
                max_lev = float(info.get("leverageFilter", {}).get("maxLeverage", 0))
                # Filtro rigoroso: Apenas cavalos de corrida (50x+)
                if max_lev >= 50:
                    candidates[symbol] = info
            
            logger.info(f"BybitREST: Identified {len(candidates)} Elite pairs with 50x+ leverage.")
            
            # 3. Sort by Turnover to ensure we track the most liquid targets
            tickers_resp = self.session.get_tickers(category="linear")
            ticker_list = tickers_resp.get("result", {}).get("list", [])
            
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
            
            # Return all elite pairs (usually ~85)
            final_symbols = [f"{x['symbol']}.P" for x in final_candidates]
            
            logger.info(f"BybitREST: Elite Scan Successful. Monitoring {len(final_symbols)} high-leverage assets.")
            return final_symbols
        except Exception as e:
            logger.error(f"Error in Elite 50x scan: {e}")
            return ["BTCUSDT.P", "ETHUSDT.P", "SOLUSDT.P"]

    def get_top_200_usdt_pairs(self):
        """Deprecated: Use get_elite_50x_pairs for Sniper Protocol."""
        return self.get_elite_50x_pairs()

    async def get_wallet_balance(self):
        """Fetches the total equity from the Bybit account (UNIFIED or CONTRACT)."""
        # logger.info(f"[DEBUG] get_wallet_balance called. Mode: {self.execution_mode}")
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
                # V5.2.4.3: Added 10s timeout
                response = await asyncio.wait_for(asyncio.to_thread(self.session.get_wallet_balance, accountType="UNIFIED"), timeout=10.0)
                result = response.get("result", {}).get("list", [{}])[0]
                equity = float(result.get("totalEquity", 0))
                logger.info(f"UNIFIED Equity: {equity}")
                self.last_balance = equity # V5.2.4.6: Update cache
                if equity > 0: return equity
            except Exception as ue: 
                logger.warning(f"UNIFIED balance fetch failed: {ue}")
            
            # Try CONTRACT if UNIFIED fails or is 0
            logger.info("Fetching balance (CONTRACT)...")
            # V5.2.4.3: Added 10s timeout
            response = await asyncio.wait_for(asyncio.to_thread(self.session.get_wallet_balance, accountType="CONTRACT"), timeout=10.0)
            result = response.get("result", {}).get("list", [{}])[0]
            coins = result.get("coin", [])
            usdt_coin = next((c for c in coins if c.get("coin") == "USDT"), {})
            equity = float(usdt_coin.get("equity", 0))
            logger.info(f"CONTRACT Equity: {equity}")
            self.last_balance = equity # V5.2.4.6: Update cache
            return equity
        except Exception as e:
            logger.error(f"Error fetching wallet balance: {e}")
            return self.last_balance # V5.2.4.6: Return cached on error

    async def get_active_positions(self, symbol: str = None):
        """Fetches currently open linear positions (Real or Simulated)."""
        if self.execution_mode == "PAPER":
            if symbol:
                norm_symbol = self._strip_p(symbol).upper()
                return [p for p in self.paper_positions if p["symbol"].upper() == norm_symbol]
            return self.paper_positions

        try:
            params = {"category": self.category, "settleCoin": "USDT"}
            if symbol: params["symbol"] = symbol
            
            # V5.2.4.3: Added 10s timeout
            response = await asyncio.wait_for(asyncio.to_thread(self.session.get_positions, **params), timeout=10.0)
            pos_list = response.get("result", {}).get("list", [])
            # Filter for positions with size > 0
            active = [p for p in pos_list if float(p.get("size", 0)) > 0]
            return active
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return []

    async def get_tickers(self, symbol: str = None):
        """
        Fetches ticker data with [V6.0] Exact Match Protection.
        If a symbol is provided, only that exact symbol's data is returned.
        """
        try:
            api_symbol = self.normalize_symbol(symbol)
            params = {"category": self.category}
            if api_symbol: params["symbol"] = api_symbol
            
            # V5.2.4.3: Added 5s timeout
            response = await asyncio.wait_for(asyncio.to_thread(self.session.get_tickers, **params), timeout=5.0)
            
            # [V6.0] Robust Mapping verification
            if api_symbol:
                ticker_list = response.get("result", {}).get("list", [])
                
                # Check 1: Did we get anything?
                if not ticker_list:
                    logger.warning(f"⚠️ [BYBIT] No ticker found for exactly {api_symbol}")
                    return response
                
                # Check 2: Exact Match Verification
                # Bybit can return the whole list if symbol is slightly off or if they change API behavior
                actual_symbol = ticker_list[0].get("symbol")
                if actual_symbol != api_symbol:
                    logger.error(f"🚨 [TICKER COLLISION] Requested {api_symbol} but Bybit returned {actual_symbol}!")
                    # Invalidate list to prevent bankroll.py from using wrong price
                    response["result"]["list"] = [] 
                elif len(ticker_list) > 1:
                    logger.warning(f"⚠️ [TICKER AMBIGUITY] Multiple results for {api_symbol}. Filtering for exact match.")
                    response["result"]["list"] = [t for t in ticker_list if t.get("symbol") == api_symbol]
            
            return response
        except Exception as e:
            logger.error(f"Error fetching tickers for {symbol}: {e}")
            return {}

    async def get_instrument_info(self, symbol: str):
        """Fetches precision and lot size filtering for a symbol with local caching."""
        try:
            api_symbol = self._strip_p(symbol)
            if api_symbol in self._instrument_cache:
                return self._instrument_cache[api_symbol]

            # V5.2.4.3: Added 5s timeout
            response = await asyncio.wait_for(asyncio.to_thread(self.session.get_instruments_info, category="linear", symbol=api_symbol), timeout=5.0)
            info = response.get("result", {}).get("list", [{}])[0]
            
            if info:
                self._instrument_cache[api_symbol] = info
            
            return info
        except Exception as e:
            logger.error(f"Error fetching instrument info for {symbol}: {e}")
            return {}

    async def round_price(self, symbol: str, price: float) -> float:
        """
        Rounds the price to the nearest tickSize allowed by Bybit.
        Essential for avoiding 10001 errors and ensuring 'Maker' precision.
        """
        return await self.format_precision(symbol, price)

    async def format_precision(self, symbol: str, price: float) -> float:
        """
        [V5.2.5] Precision Engine: Normaliza preços baseado no tickSize real da Bybit.
        """
        if price <= 0: return price
        
        info = await self.get_instrument_info(symbol)
        tick_size_str = info.get("priceFilter", {}).get("tickSize")
        
        if not tick_size_str:
            return price # Fallback
            
        from decimal import Decimal, ROUND_HALF_UP
        tick_size = Decimal(tick_size_str)
        price_dec = Decimal(str(price))
        
        # Formula: round(price / tickSize) * tickSize
        rounded = (price_dec / tick_size).quantize(Decimal('1'), rounding=ROUND_HALF_UP) * tick_size
        
        # Normalize to remove trailing zeros and convert back to float
        return float(rounded.normalize())




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
                self._save_paper_state()
                
                # Return fake order response
                return {
                    "retCode": 0,
                    "result": {"orderId": f"PAPER-{api_symbol}-123", "orderLinkId": f"PAPER-{api_symbol}-123"}
                }

            except Exception as e:
                logger.error(f"[PAPER] Failed to place simulated order: {e}")
                return None

        try:
            # [V5.2.5] Precision Engine: Normalizar preços antes do envio
            sl_final = await self.format_precision(symbol, sl_price)
            tp_final = await self.format_precision(symbol, tp_price) if tp_price else None

            order_params = {
                "category": self.category,
                "symbol": api_symbol,
                "side": side,
                "orderType": "Market",
                "qty": str(qty),
                "stopLoss": str(sl_final) if sl_final > 0 else None,
                "tpTriggerBy": "LastPrice",
                "slTriggerBy": "LastPrice",
                "tpslMode": "Full",
            }
            if tp_final:
                order_params["takeProfit"] = str(tp_final)

            response = await asyncio.to_thread(self.session.place_order, **order_params)
            logger.info(f"Atomic order placed for {symbol}: {response}")
            return response
        except Exception as e:
            logger.error(f"Failed to place atomic order for {symbol}: {e}")
            return None

    async def close_position(self, symbol: str, side: str, qty: float) -> bool:
        """
        Closes a position at market. 
        V5.3.4: Added closure_lock and pending_closures for target/SL coordination.
        Returns True if closure was executed, False if already closed/pending.
        """
        norm_symbol = self._strip_p(symbol).upper()
        
        # V5.4.0: Gemini Lock - Global Atomicity
        lock_acquired = await self.redis.acquire_lock(f"close:{norm_symbol}", lock_timeout=15)
        if not lock_acquired:
            logger.info(f"🛡️ [REDIS LOCK] {norm_symbol} closure already in progress. Skipping.")
            return False

        try:
            if norm_symbol in self.pending_closures:
                logger.info(f"🛡️ [BYBIT] {norm_symbol} already has a local pending closure. Skipping.")
                return False
            
            if self.execution_mode == "PAPER":
                logger.info(f"[PAPER] Closing position {norm_symbol}")
                # Find position
                pos = next((p for p in self.paper_positions if p["symbol"].upper() == norm_symbol), None)
                if pos:
                    # Mark as pending to avoid dual-entry from other tasks
                    self.pending_closures.add(norm_symbol)
                    try:
                        # Calculate Realized PNL to update Paper Balance
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
                        
                        # V5.4.0: UI Pub/Sub - Push closure to frontend
                        await self.redis.publish_update("trade_updates", {
                            "type": "POSITION_CLOSED",
                            "symbol": symbol,
                            "pnl": final_pnl,
                            "reason": "PAPER_CLOSE"
                        })
                        
                        logger.info(f"[PAPER] Closed {symbol}. PNL: ${final_pnl:.2f}. New Balance: ${self.paper_balance:.2f}")
                        self._save_paper_state()
                        
                        # Cleanup pending after a small delay to let other loops sync
                        asyncio.create_task(self._cleanup_pending_closure(norm_symbol))
                        return True
                    except Exception as e:
                        logger.error(f"[PAPER] Error during position closure: {e}")
                        if pos in self.paper_positions:
                            self.paper_positions.remove(pos)
                        self.pending_closures.discard(norm_symbol)
                        return False
                return False

            # REAL MODE
            try:
                self.pending_closures.add(norm_symbol)
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
                # Cleanup pending
                asyncio.create_task(self._cleanup_pending_closure(norm_symbol))
                return True
            except Exception as e:
                logger.error(f"Error closing position for {symbol}: {e}")
                self.pending_closures.discard(norm_symbol)
                return False
        finally:
            # Release Redis Lock
            await self.redis.release_lock(f"close:{norm_symbol}")

    async def _cleanup_pending_closure(self, symbol: str, delay: int = 15):
        """V5.3.4: Helper to clear pending closure flag after a delay."""
        await asyncio.sleep(delay)
        self.pending_closures.discard(symbol)

    async def get_closed_pnl(self, symbol: str, limit: int = 1):
        """Fetches final PnL for closed trades."""
        if self.execution_mode == "PAPER":
            # Filter history by symbol
            relevant = [h for h in self.paper_orders_history if h["symbol"] == symbol]
            # Return last N
            return relevant[-limit:] if relevant else []

        try:
            api_symbol = self._strip_p(symbol)
            # V5.2.4.3: Added 5s timeout
            response = await asyncio.wait_for(asyncio.to_thread(self.session.get_closed_pnl, category=self.category, symbol=api_symbol, limit=limit), timeout=5.0)
            return response.get("result", {}).get("list", [])
        except Exception as e:
            logger.error(f"Error fetching closed PnL for {symbol}: {e}")
            return []

    async def get_klines(self, symbol: str, interval: str = "60", limit: int = 20):
        """Fetches historical klines for ATR and variation calculations."""
        try:
            api_symbol = self._strip_p(symbol)
            # V5.2.4.3: Added 5s timeout
            response = await asyncio.wait_for(asyncio.to_thread(self.session.get_mark_price_kline,
                category=self.category,
                symbol=api_symbol,
                interval=interval,
                limit=limit
            ), timeout=5.0)
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
                self._save_paper_state()
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
                    should_close, reason, new_sl = await execution_protocol.process_order_logic(slot_data, current_price)

                    # [V5.2.5] ELITE FIX: Always process closure if should_close is TRUE
                    if should_close:
                        # Re-calculate ROI for log
                        debug_roi = execution_protocol.calculate_roi(slot_data["entry_price"], current_price, slot_data["side"])
                        logger.info(f"🧐 [PAPER] PROTOCOL HIT: {symbol} | ROI: {debug_roi:.2f}% | Reason: {reason}")

                        to_close.append({
                            "symbol": symbol,
                            "side": pos["side"],
                            "size": float(pos["size"]),
                            "reason": reason,
                            "slot_id": slot_data.get("slot_id"),
                            "slot_type": slot_data.get("slot_type", "SNIPER"),
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
                    was_closed = await self.close_position(sym, side, size)
                    
                    if not was_closed:
                        logger.info(f"⏭️ [PAPER] {sym} already closed or handled. Skipping slot reset/log.")
                        continue
                    
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
                            "slot_id": slot_id,
                            "slot_type": close_data.get("slot_type", "SNIPER") # Use stored type
                        }
                        
                        await firebase_service.hard_reset_slot(slot_id, close_data["reason"], pnl, trade_data)
                        
                        # V5.3.2: Redundancy - Register Persistent Cooldown if SL
                        if "SL" in close_data["reason"] or "STOP" in close_data["reason"]:
                            try:
                                await firebase_service.register_sl_cooldown(sym)
                            except Exception as cd_err:
                                logger.warning(f"[PAPER] Redundancy: Failed to register persistent cooldown: {cd_err}")
                        
                        # V5.2.3: Notify bankroll/vault for statistics sync
                        try:
                            from services.bankroll import bankroll_manager
                            await bankroll_manager.register_sniper_trade({
                                **trade_data,
                                "pnl": pnl,
                                "pnl_percent": (pnl / (close_data["entry_price"] * size / 50)) * 100 if size > 0 else 0, # Rough ROI estimate
                                "slot_type": close_data.get("slot_type", "SNIPER") # Use stored type
                            })
                        except Exception as e:
                            logger.error(f"[PAPER] Failed to notify bankroll of trade closure: {e}")

                        logger.info(f"✅ [PAPER] Slot {slot_id} FREED | {sym} | PNL: ${pnl:.2f} | New Balance: ${self.paper_balance:.2f}")

                # 6. Update trailing stops in Firebase
                for sym, new_sl, slot_id in to_update_sl:
                    # V5.2.4: Ensure new_sl is rounded at the engine level too
                    new_sl = await self.round_price(sym, new_sl)
                    
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
            
            # V5.4.0: UI Pub/Sub - High frequency PnL push (Throttle to once per loop)
            if self.paper_positions:
                pnl_summary = []
                for p in self.paper_positions:
                    p_sym = p["symbol"]
                    c_price = price_map.get(p_sym, 0)
                    if c_price > 0:
                        p_roi = execution_protocol.calculate_roi(float(p["avgPrice"]), c_price, p["side"])
                        # V6.0: Visual Cap
                        if p_roi > 5000: p_roi = 5000
                        if p_roi < -5000: p_roi = -5000
                        pnl_summary.append({"symbol": p_sym, "roi": p_roi})
                
                if pnl_summary:
                    await self.redis.publish_update("ui_updates", {"type": "PNL_PULSE", "data": pnl_summary})

            await asyncio.sleep(1)

bybit_rest_service = BybitREST()

