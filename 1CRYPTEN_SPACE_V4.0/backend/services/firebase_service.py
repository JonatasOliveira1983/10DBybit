import firebase_admin
from firebase_admin import credentials, firestore, db
import asyncio
from config import settings
import logging
import datetime

logger = logging.getLogger("FirebaseService")



# Define Private Key safely as a Python multiline string to avoid string escaping hell
# This is the user provided key
# Initialize Firebase with explicit error handling to strictly enforcing SAFE MODE if key is invalid
# This guarantees the server starts even with broken keys.

from collections import deque
import time

class FirebaseService:
    def __init__(self):
        self.is_active = False
        self.db = None # Firestore
        self.rtdb = None # Realtime DB
        self.log_buffer = deque(maxlen=500) # Increased buffer for offline periods
        self.signal_buffer = deque(maxlen=500)
        # V10.5 Dual Slot System: Limit to 2 slots
        self.slots_cache = [{"id": i, "symbol": None, "entry_price": 0, "current_stop": 0} for i in range(1, 3)]
        self._reconnect_task = None
        # V10.6.5: Connection health tracking
        self._consecutive_failures = 0
        self._last_successful_op = time.time()
        self._reconnect_attempts = 0

    async def initialize(self):
        """Asynchronously initializes the Firebase Admin SDK."""

        
        if self.is_active:
            return
            
        try:
            # Load credentials
            cred = None
            import os
            import json
            
            # 1. Try Environment Variable (Production)
            firebase_env = os.getenv("FIREBASE_CREDENTIALS")
            if firebase_env:
                try:
                    cred_dict = json.loads(firebase_env)
                    cred = credentials.Certificate(cred_dict)
                    logger.info("Loaded Firebase credentials from Environment Variable.")
                except Exception as e:
                    logger.error(f"Failed to parse FIREBASE_CREDENTIALS env var: {e}")

            # 2. Try Local File (Development)
            if not cred:
                cred_path = "serviceAccountKey.json"
                if os.path.exists(cred_path):
                   cred = credentials.Certificate(cred_path)
                   logger.info("Loaded Firebase credentials from local file.")
            
            if not cred:
                raise ValueError("No Firebase credentials found (Env or File).")

            # V5.2.4.4: SSL Resilience Retry Loop for production connectivity
            for attempt in range(3):
                try:
                    # Avoid re-initializing if already running
                    try:
                        app = firebase_admin.get_app()
                    except ValueError:
                        # Initialize with RTDB URL if available
                        options = {}
                        db_url = settings.FIREBASE_DATABASE_URL or os.getenv("FIREBASE_DATABASE_URL")
                        if db_url and db_url != "None":
                            options['databaseURL'] = db_url
                            logger.info(f"Using Firebase Database URL: {db_url}")
                        else:
                            logger.warning("FIREBASE_DATABASE_URL is missing or 'None'. RTDB Pulse will be disabled.")
                        app = firebase_admin.initialize_app(cred, options)
                    
                    # Initialize Clients
                    self.db = firestore.client()
                    try:
                        if 'databaseURL' in options:
                            self.rtdb = db.reference("/")
                            logger.info("Firebase Realtime DB connected.")
                        else:
                            logger.warning("Firebase Realtime DB NOT connected (no URL).")
                    except Exception as e:
                        logger.error(f"Error connecting to RTDB: {e}")

                    self.is_active = True
                    logger.info("Firebase Admin SDK initialized successfully.")
                    
                    # Flush buffers if we just reconnected
                    asyncio.create_task(self._flush_buffers())
                    break # Success!
                except Exception as e:
                    # Catch specific SSL/EOF issues reported in production
                    is_ssl_error = "SSL" in str(e) or "EOF" in str(e)
                    if is_ssl_error and attempt < 2:
                        wait = (attempt + 1) * 3
                        logger.warning(f"🚨 Firebase SSL Init Error (Attempt {attempt+1}/3). Retrying in {wait}s... Error: {e}")
                        await asyncio.sleep(wait)
                    else:
                        raise e

        except Exception as e:
            logger.error(f"Error initializing Firebase: {e}")
            logger.warning("Starting FirebaseService in OFFLINE/SAFE MODE.")
            self.is_active = False  
            
            # Start reconnection loop if not already running
            if not self._reconnect_task or self._reconnect_task.done():
                self._reconnect_task = asyncio.create_task(self._reconnection_loop())

    async def _reconnection_loop(self):
        """
        V10.6.5: Enhanced reconnection loop with exponential backoff.
        Starts at 15s, doubles each attempt, max 60s.
        """
        base_delay = 15  # Start with 15s instead of 60s
        max_delay = 60
        
        while not self.is_active:
            self._reconnect_attempts += 1
            delay = min(base_delay * (2 ** (self._reconnect_attempts - 1)), max_delay)
            
            logger.warning(f"🔄 Firebase Reconnection Attempt #{self._reconnect_attempts} (next in {delay}s)...")
            await self.initialize()
            
            if self.is_active:
                logger.info(f"✅ Firebase RECONNECTED after {self._reconnect_attempts} attempts.")
                self._reconnect_attempts = 0
                self._consecutive_failures = 0
                break
            
            await asyncio.sleep(delay)

    async def _flush_buffers(self):
        """Pushes buffered logs and signals to Firebase after a reconnection."""
        if not self.is_active: return
        
        logger.info(f"Flushing buffers to Firebase: {len(self.log_buffer)} logs, {len(self.signal_buffer)} signals.")
        
        # We don't clear the buffer because it's a deque used for UI as well, 
        # but we can try to push items that are 'local' only.
        # For simplicity, we just log that we are online now.
        await self.log_event("System", "🔥 Firebase Connection Restored. Buffers active.", "SUCCESS")

    async def _health_check(self):
        """
        V10.6.5: Proactive health check triggered by consecutive failures.
        Tests basic Firebase connectivity and triggers reconnection if needed.
        """
        logger.info("🏥 Running Firebase health check...")
        try:
            # Simple read test with short timeout
            test_result = await asyncio.wait_for(
                asyncio.to_thread(self.db.collection("banca_status").document("status").get),
                timeout=5.0
            )
            if test_result.exists:
                logger.info("✅ Firebase health check passed. Resetting failure counter.")
                self._consecutive_failures = 0
                self._last_successful_op = time.time()
            else:
                raise Exception("Health check returned empty result")
        except Exception as e:
            logger.error(f"❌ Firebase health check FAILED: {e}")
            # Mark as inactive and trigger reconnection
            self.is_active = False
            if not self._reconnect_task or self._reconnect_task.done():
                self._reconnect_task = asyncio.create_task(self._reconnection_loop())

    async def get_banca_status(self):
        if not self.is_active:
            # Try to re-initialize if currently inactive
            await self.initialize()
            if not self.is_active:
                return {"saldo_total": 0, "risco_real_percent": 0, "slots_disponiveis": 10, "status": "OFFLINE"}
            
        try:
            # Wrap blocking call with timeout
            doc = await asyncio.wait_for(
                asyncio.to_thread(self.db.collection("banca_status").document("status").get),
                timeout=10.0  # Increased to 10 seconds for reliability
            )
            if doc.exists:
                return doc.to_dict()
        except asyncio.TimeoutError:
            self._consecutive_failures += 1
            logger.warning(f"Firebase timeout ao buscar banca status (failures: {self._consecutive_failures}). Using fallback.")
            # V10.6.5: Auto-trigger reconnection check after 5 consecutive failures
            if self._consecutive_failures >= 5:
                logger.error("🚨 5+ consecutive Firebase failures. Triggering health check...")
                asyncio.create_task(self._health_check())
            return {"saldo_total": 0, "risco_real_percent": 0, "slots_disponiveis": 10, "status": "TIMEOUT"}
        except Exception as e:
            self._consecutive_failures += 1
            logger.error(f"Error fetching banca (failures: {self._consecutive_failures}): {e}")
        return {"saldo_total": 0, "risco_real_percent": 0, "slots_disponiveis": 10, "status": "ERROR"}

    async def update_banca_status(self, data: dict):
        if not self.is_active: return data
        try:
            # Sync to Firestore
            await asyncio.wait_for(asyncio.to_thread(self.db.collection("banca_status").document("status").set, data, merge=True), timeout=5.0)
            
            # V5.2.5: Sync to Realtime DB for instant PWA updates
            if self.rtdb:
                await asyncio.to_thread(self.rtdb.child("banca_status").set, data)
        except Exception as e:
            logger.error(f"Error updating banca status to RTDB: {e}")
        return data

    async def log_banca_snapshot(self, data: dict):
        """Logs a historical snapshot of the bankroll."""
        if not self.is_active: return
        try:
            snapshot = {
                **data,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
            await asyncio.to_thread(self.db.collection("banca_history").add, snapshot)
        except Exception as e:
            logger.error(f"Error logging banca snapshot: {e}")

    async def get_banca_history(self, limit: int = 50):
        """Fetches historical bankroll snapshots."""
        if not self.is_active: return []
        try:
            def _get_history():
                docs = self.db.collection("banca_history").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit).stream()
                return [doc.to_dict() for doc in docs]
            return await asyncio.to_thread(_get_history)
        except Exception as e:
            logger.error(f"Error fetching banca history: {e}")
            return []

    async def log_trade(self, trade_data: dict):
        """Logs a completed trade to history."""
        if not self.is_active: return
        try:
            trade_data["timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            await asyncio.to_thread(self.db.collection("trade_history").add, trade_data)
            logger.info(f"Trade history logged for {trade_data.get('symbol')}")
        except Exception as e:
            logger.error(f"Error logging trade: {e}")

    async def get_trade_history(self, limit: int = 50, last_timestamp: str = None):
        """
        Fetches completed trade history with pagination support.
        [V5.2.5] Support for last_timestamp to enable infinite scroll/pagination.
        """
        if not self.is_active: return []
        try:
            def _get_trades():
                query = self.db.collection("trade_history").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit)
                
                if last_timestamp:
                    try:
                        ts_val = float(last_timestamp)
                        query = query.start_after({"timestamp": ts_val})
                    except (ValueError, TypeError):
                        query = query.start_after({"timestamp": last_timestamp})
                
                docs = query.stream()
                return [doc.to_dict() for doc in docs]
            return await asyncio.to_thread(_get_trades)
        except Exception as e:
            logger.error(f"Error fetching trade history: {e}")
            return []

    async def get_active_slots(self):
        # Resilience: If Firebase is temporarily inactive, return the last known good slots
        if not self.is_active: 
            return self.slots_cache
            
        # Debounce: If we fetched less than 2s ago, return cache immediately to save quota
        now_time = time.time()
        if hasattr(self, 'last_slots_fetch') and (now_time - self.last_slots_fetch) < 2.0:
            return self.slots_cache

        try:
            def _get_slots():
                # Stream the actual documents
                docs = self.db.collection("slots_ativos").order_by("id").stream()
                return [doc.to_dict() for doc in docs]
            
            # Increase timeout further for high-latency environments (V10.6.5 Stability)
            data = await asyncio.wait_for(asyncio.to_thread(_get_slots), timeout=20.0)
            
            if data and len(data) >= 1:
                self.slots_cache = data
                self.last_slots_fetch = now_time
                # V10.6.5: Reset failure counter on success
                self._consecutive_failures = 0
                self._last_successful_op = now_time
                return self.slots_cache
                
        except asyncio.TimeoutError:
            self._consecutive_failures += 1
            logger.warning(f"🕐 Firebase slots timeout (failures: {self._consecutive_failures}). Using cache.")
            if self._consecutive_failures >= 5:
                asyncio.create_task(self._health_check())
        except Exception as e:
            self._consecutive_failures += 1
            err_type = type(e).__name__
            logger.warning(f"Transient Firebase error fetching slots ({err_type}, failures: {self._consecutive_failures}): {e}. Using cache.")
            
        return self.slots_cache

    async def update_slot(self, slot_id: int, data: dict):
        # Update cache first
        for s in self.slots_cache:
            if s["id"] == slot_id:
                s.update(data)
                break
                
        if not self.is_active: return data
        try:
            # Sync to Firestore
            await asyncio.wait_for(asyncio.to_thread(self.db.collection("slots_ativos").document(str(slot_id)).set, data, merge=True), timeout=5.0)
            
            # V5.2.5: Sync to Realtime DB for instant PWA updates
            if self.rtdb:
                await asyncio.to_thread(self.rtdb.child("slots").child(str(slot_id)).update, data)
        except Exception as e:
            logger.error(f"Error updating slot {slot_id} to RTDB: {e}")
        return data

    async def log_signal(self, signal_data: dict):
        # 1. Add to local buffer immediately
        signal_data["id"] = f"loc_{int(time.time() * 1000)}"
        signal_data["timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.signal_buffer.appendleft(signal_data)
        
        if not self.is_active: return signal_data["id"]
        
        # Retry logic for critical signal logging
        for attempt in range(3):
            try:
                # Wrap blocking call
                await asyncio.wait_for(asyncio.to_thread(self.db.collection("journey_signals").add, signal_data), timeout=5.0)
                return signal_data["id"] # Success
            except (asyncio.TimeoutError, Exception) as e: 
                if attempt < 2:
                    wait_time = (attempt + 1) * 2
                    logger.warning(f"Retry {attempt+1}/3: Firebase log_signal failed ({type(e).__name__}). Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"FATAL: log_signal failed after 3 attempts: {e}")
        
        return signal_data["id"] # Return ID anyway as it's in the local buffer

    async def get_recent_signals(self, limit: int = 100):
        # Always return local buffer first for speed and quota saving
        local_data = list(self.signal_buffer)[:limit]
        if not self.is_active or len(local_data) >= 5:
             return local_data
             
        try:
            def _get_signals():
                docs = self.db.collection("journey_signals").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit).stream()
                return [{**doc.to_dict(), "id": doc.id} for doc in docs]
            
            remote = await asyncio.wait_for(asyncio.to_thread(_get_signals), timeout=5.0)
            return remote or local_data
        except Exception: return local_data

    async def log_event(self, agent: str, message: str, level: str = "INFO"):

        data = {
            "agent": agent,
            "message": message,
            "level": level,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        self.log_buffer.appendleft(data)
        
        if not self.is_active: return data
        try:
            await asyncio.to_thread(self.db.collection("system_logs").add, data)
        except Exception: pass
        return data

    async def get_recent_logs(self, limit: int = 50):
        local_data = list(self.log_buffer)[:limit]
        if not self.is_active or len(local_data) >= 5:
            return local_data or [{"agent": "System", "message": "Neural Interface Online. Waiting for logs...", "level": "INFO", "timestamp": "Now"}]
            
        try:
            def _get_logs():
                docs = self.db.collection("system_logs").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit).stream()
                return [doc.to_dict() for doc in docs]
            remote = await asyncio.to_thread(_get_logs)
            return remote or local_data
        except Exception: return local_data


    async def update_signal_outcome(self, signal_id: str, outcome: bool):
        if not self.is_active: return
        try:
            await asyncio.to_thread(self.db.collection("journey_signals").document(signal_id).update, {"outcome": outcome})
        except Exception: pass

    async def update_pulse(self):
        """Sends a heartbeat to Realtime DB for the Pulse Monitor."""
        if not self.is_active or not self.rtdb: return
        try:
            # RTDB is great for this as it has extremely low latency
            data = {
                "timestamp": time.time() * 1000,
                "status": "ONLINE",
                "last_heartbeat": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
            # Add timeout to prevent event loop starvation if RTDB hangs
            # Use root reference directly to avoid NotFound if child doesn't exist
            await asyncio.wait_for(asyncio.to_thread(self.rtdb.update, {"system_pulse": data}), timeout=3.0)
        except (asyncio.TimeoutError, Exception) as e:
            logger.warning(f"Heartbeat failed: {type(e).__name__}. This is usually transient but may trigger LAG in UI.")

    async def update_pulse_drag(self, btc_drag_mode: bool, btc_cvd: float, exhaustion: float):
        """V5.1.0: Updates BTC Drag Mode status in RTDB for the frontend widget."""
        if not self.is_active or not self.rtdb: return
        try:
            data = {
                "btc_drag_mode": btc_drag_mode,
                "btc_cvd": btc_cvd,
                "exhaustion": exhaustion,
                "timestamp": time.time() * 1000
            }
            # V5.2.4.3: Added 3s timeout for RTDB updates
            await asyncio.wait_for(asyncio.to_thread(self.rtdb.update, {"btc_command_center": data}), timeout=3.0)
        except Exception: pass

    async def update_system_state(self, state: str, slots_occupied: int = 0, message: str = ""):
        """
        V10.6: Updates system state in RTDB for frontend synchronization.
        state: SCANNING | MONITORING | PAUSED
        """
        if not self.is_active or not self.rtdb: return
        try:
            data = {
                "current": state,
                "slots_occupied": slots_occupied,
                "message": message,
                "updated_at": time.time() * 1000
            }
            await asyncio.wait_for(asyncio.to_thread(self.rtdb.update, {"system_state": data}), timeout=3.0)
            logger.info(f"🔄 V10.6 System State: {state} (Slots: {slots_occupied}/2)")
        except Exception as e:
            logger.warning(f"Error updating system state: {e}")

    async def get_system_state(self):
        """V10.6: Fetches the current system state from RTDB as a fallback."""
        if not self.is_active or not self.rtdb:
            return {"current": "PAUSED", "message": "Firebase Offline", "slots_occupied": 0}
        try:
            state = await asyncio.to_thread(self.rtdb.child("system_state").get)
            return state or {"current": "PAUSED", "message": "Sem Dados", "slots_occupied": 0}
        except Exception as e:
            logger.error(f"Error fetching system state: {e}")
            return {"current": "PAUSED", "message": "Erro Firebase", "slots_occupied": 0}

    async def update_ws_health(self, latency: float, status: str = "ONLINE"):
        """🆕 V6.0: Updates WebSocket Health (Command Tower) in RTDB."""
        if not self.is_active or not self.rtdb: return
        try:
            data = {
                "latency_ms": latency,
                "status": status,
                "timestamp": time.time() * 1000
            }
            await asyncio.wait_for(asyncio.to_thread(self.rtdb.update, {"ws_command_tower": data}), timeout=2.0)
        except Exception: pass

    async def update_rtdb_slots(self, slots: list):
        """Duplicate slot data to RTDB for high-speed UI refreshes."""
        if not self.is_active or not self.rtdb: return
        try:
            # Convert list to dict for RTDB
            slots_data = {str(s["id"]): s for s in slots}
            # V5.2.4.3: Added 3s timeout for RTDB update
            await asyncio.wait_for(asyncio.to_thread(self.rtdb.child("live_slots").update, slots_data), timeout=3.0)
        except Exception: pass

    async def update_radar_batch(self, batch_data: dict):
        """Updates multiple symbols in RTDB in a single operation."""
        if not self.is_active or not self.rtdb: return
        try:
            # Note: In RTDB, update/set at the root or a subpath is efficient.
            # V5.2.4.3: Added 3s timeout
            await asyncio.wait_for(asyncio.to_thread(self.rtdb.child("market_radar").update, batch_data), timeout=3.0)
        except Exception as e:
            logger.error(f"Error updating radar batch: {e}")

    # --- Operação Oráculo: Chat Memory ---
    async def get_chat_history(self, limit: int = 15):
        """Fetches the recent interactive chat messages from RTDB."""
        if not self.is_active or not self.rtdb: return []
        try:
            def _get_chat_history_sync():
                # Correct way: use .child() on the root reference
                ref = self.rtdb.child("chat_history")
                snapshot = ref.order_by_key().limit_to_last(limit).get()
                if not snapshot: return []
                # RTDB returns a dict, sort by key (timestamp) and return list
                history = [v for k, v in sorted(snapshot.items())]
                return history
            return await asyncio.to_thread(_get_chat_history_sync)
        except Exception as e:
            logger.error(f"Error fetching chat history: {e}")
            return []

    async def add_chat_message(self, role: str, message: str):
        """Adds a message to the chat history in RTDB."""
        if not self.is_active or not self.rtdb: return
        try:
            def _add_chat_message_sync():
                ref = self.rtdb.child("chat_history")
                timestamp = int(time.time() * 1000)
                ref.child(str(timestamp)).set({
                    "role": role,
                    "text": message, # Using 'text' to match standard naming if needed, or 'message'
                    "timestamp": timestamp
                })
                # Cleanup: Keep only last 20 messages to avoid bloat
                snapshot = ref.get()
                if snapshot and len(snapshot) > 20:
                    keys = sorted(snapshot.keys())
                    # Delete everything except the last 20
                    for k in keys[:-20]:
                        ref.child(k).delete()
            await asyncio.to_thread(_add_chat_message_sync)
        except Exception as e:
            logger.error(f"Error adding chat message: {e}")

    async def clear_chat_history(self):
        """Removes all chat messages from RTDB."""
        if not self.is_active or not self.rtdb: return
        try:
            await asyncio.to_thread(self.rtdb.child("chat_history").delete)
            # Log the reset event
            await self.log_event("System", "Chat History Reset by Commander", "INFO")
        except Exception as e:
            logger.error(f"Error clearing chat history: {e}")

    async def get_slot(self, slot_id: int) -> dict:
        """Fetch a specific slot state from Firestore."""
        if not self.is_active: return None
        try:
            doc_ref = self.db.collection("slots_ativos").document(str(slot_id))
            doc = await asyncio.to_thread(doc_ref.get)
            return doc.to_dict() if doc.exists else None
        except Exception:
            return None

    async def hard_reset_slot(self, slot_id: int, reason: str, pnl: float = 0, trade_data: dict = None):
        """
        V5.3.4 Idempotent Reset: Verify slot still active before logging and resetting.
        """
        # Cross-Loop Idempotency check:
        # If this slot was already reset by another loop (e.g. Guardian vs BybitREST), 
        # we skip the logging to avoid duplicates.
        current_state = await self.get_slot(slot_id)
        if not current_state or not current_state.get("symbol"):
            if trade_data:
                logger.warning(f"⚠️ [IDEMPOTENCY] Slot {slot_id} already reset. Skipping duplicate log for {trade_data.get('symbol')}")
            return

        logger.info(f"🚨 [HARD RESET] Slot {slot_id} | Motivo: {reason} | PNL: ${pnl:.2f}")
        
        reset_data = {
            "symbol": None,
            "side": None,
            "entry_price": 0,
            "current_stop": 0,
            "target_price": None,
            "status_risco": "LIVRE",
            "pnl_percent": 0,
            "slot_type": None,
            "pensamento": f"🔄 Reset: {reason}"
        }
        
        # 1. Update slot in Firebase and local cache
        await self.update_slot(slot_id, reset_data)
        
        # 2. Log trade to history if data provided
        if trade_data:
            trade_data["close_reason"] = reason
            trade_data["pnl"] = pnl
            
            # 🆕 V6.0: Generate Auditable Reasoning Report (AI Act 2026)
            initial_reasoning = current_state.get("pensamento", "N/A")
            report = f"--- AUDIT REPORT V6.0 ---\n"
            report += f"SYMBOL: {trade_data.get('symbol')}\n"
            report += f"STRATEGY: {trade_data.get('slot_type')}\n"
            report += f"REASONING: {initial_reasoning}\n"
            report += f"OUTCOME: {'WIN 🚀' if pnl >= 0 else 'LOSS 🛡️'}\n"
            report += f"CLOSE REASON: {reason}\n"
            report += f"PNL USD: ${pnl:.2f}\n"
            report += f"-------------------------"
            
            trade_data["reasoning_report"] = report
            await self.log_trade(trade_data)
        
        # 3. Log event for monitoring
        emoji = "✅" if pnl >= 0 else "❌"
        await self.log_event("ExecutionProtocol", f"{emoji} Slot {slot_id} RESET: {reason} | PNL: ${pnl:.2f}", "SUCCESS" if pnl >= 0 else "WARNING")

    async def initialize_db(self):
        """Creates initial documents if they don't exist."""
        if not self.is_active: return
        
        try:
            # Banca
            doc_ref = self.db.collection("banca_status").document("status")
            banca_doc = await asyncio.to_thread(doc_ref.get)
            if not banca_doc.exists:
                await asyncio.to_thread(doc_ref.set, {
                    "id": "status",
                    "saldo_total": 0,
                    "risco_real_percent": 0,
                    "slots_disponiveis": 10
                })
            
            # Slots
            for i in range(1, 11):
                slot_ref = self.db.collection("slots_ativos").document(str(i))
                slot_doc = await asyncio.to_thread(slot_ref.get)
                if not slot_doc.exists:
                    await asyncio.to_thread(slot_ref.set, {
                        "id": i,
                        "symbol": None,
                        "side": None,
                        "entry_price": 0,
                        "current_stop": 0,
                        "status_risco": "LIVRE",
                        "pnl_percent": 0
                    })
        except Exception as e:
            logger.error(f"Error initializing DB: {e}")

    # --- Capitão Elite V5.0: Long-Term Memory ---
    async def get_captain_profile(self) -> dict:
        """Fetches the Captain's memory profile for the user."""
        if not self.is_active or not self.rtdb: 
            return self._get_default_profile()
        try:
            def _get_profile_sync():
                ref = self.rtdb.child("captain_profile")
                profile = ref.get()
                return profile if profile else None
            profile = await asyncio.to_thread(_get_profile_sync)
            return profile if profile else self._get_default_profile()
        except Exception as e:
            logger.error(f"Error fetching captain profile: {e}")
            return self._get_default_profile()

    def _get_default_profile(self) -> dict:
        """Returns the default Captain profile structure."""
        return {
            "name": "Almirante",
            "interests": ["NBA", "Trading", "Tecnologia"],
            "communication_style": "formal_com_humor",
            "risk_tolerance": "moderado",
            "long_term_goals": [],
            "facts_learned": []
        }

    async def update_captain_profile(self, updates: dict):
        """Updates specific fields in the Captain's profile."""
        if not self.is_active or not self.rtdb: return
        try:
            def _update_profile_sync():
                ref = self.rtdb.child("captain_profile")
                ref.update(updates)
            await asyncio.to_thread(_update_profile_sync)
            logger.info(f"Captain Profile updated: {list(updates.keys())}")
        except Exception as e:
            logger.error(f"Error updating captain profile: {e}")

    async def add_learned_fact(self, fact: str):
        """Adds a new fact to the Captain's knowledge base about the user."""
        if not self.is_active or not self.rtdb: return
        try:
            profile = await self.get_captain_profile()
            facts = profile.get("facts_learned", [])
            if fact not in facts:
                facts.append(fact)
                # Keep only last 20 facts to avoid bloat
                if len(facts) > 20:
                    facts = facts[-20:]
                await self.update_captain_profile({"facts_learned": facts})
                logger.info(f"Captain learned new fact: {fact}")
        except Exception as e:
            logger.error(f"Error adding learned fact: {e}")

    # --- Persistent SL Cooldowns V5.3.2 ---
    async def register_sl_cooldown(self, symbol: str, duration_seconds: int = 300):
        """
        Registers a symbol in SL cooldown in Firebase RTDB.
        Symbol is normalized to ensure consistency.
        """
        if not self.is_active or not self.rtdb: return
        try:
            norm_symbol = symbol.replace(".P", "").upper()
            expiry_time = time.time() + duration_seconds
            
            def _register_sync():
                ref = self.rtdb.child("system_cooldowns").child(norm_symbol)
                ref.set({
                    "symbol": norm_symbol,
                    "expiry_time": expiry_time,
                    "duration": duration_seconds,
                    "timestamp": time.time()
                })
            await asyncio.to_thread(_register_sync)
            logger.warning(f"🛡️ [FIREBASE] Cooldown persistence: {norm_symbol} blocked until {datetime.fromtimestamp(expiry_time).strftime('%H:%M:%S')}")
        except Exception as e:
            logger.error(f"Error registering SL cooldown in Firebase: {e}")

    async def is_symbol_blocked(self, symbol: str) -> tuple:
        """
        Checks if a symbol is in persistent SL cooldown.
        Returns (is_blocked, remaining_seconds).
        """
        if not self.is_active or not self.rtdb: return False, 0
        try:
            norm_symbol = symbol.replace(".P", "").upper()
            
            def _check_sync():
                ref = self.rtdb.child("system_cooldowns").child(norm_symbol)
                snapshot = ref.get()
                return snapshot if snapshot else None
                
            data = await asyncio.to_thread(_check_sync)
            if not data:
                return False, 0
                
            expiry = data.get("expiry_time", 0)
            current_time = time.time()
            
            if current_time < expiry:
                remaining = int(expiry - current_time)
                return True, remaining
            else:
                # Cleanup expired cooldown
                def _cleanup_sync():
                    self.rtdb.child("system_cooldowns").child(norm_symbol).delete()
                await asyncio.to_thread(_cleanup_sync)
                return False, 0
        except Exception as e:
            logger.error(f"Error checking SL cooldown in Firebase: {e}")
            return False, 0

firebase_service = FirebaseService()
