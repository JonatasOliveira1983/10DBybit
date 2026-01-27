import firebase_admin
from firebase_admin import credentials, firestore
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
        self.db = None
        self.log_buffer = deque(maxlen=50)
        self.signal_buffer = deque(maxlen=50)
        self.slots_cache = [{"id": i, "symbol": None, "entry_price": 0, "current_stop": 0} for i in range(1, 11)]

    async def initialize(self):
        """Asynchronously initializes the Firebase Admin SDK."""

        
        if self.is_active:
            return
            
        try:
            # Load credentials from file with timeout
            cred_path = "serviceAccountKey.json"
            cred = credentials.Certificate(cred_path)
            
            # Avoid re-initializing if already running
            try:
                firebase_admin.get_app()
            except ValueError:
                firebase_admin.initialize_app(cred)
            
            # This is a sync call but we run it in the initialization phase
            self.db = firestore.client()
            self.is_active = True
            logger.info("Firebase Admin SDK initialized successfully.")
        except Exception as e:
            logger.error(f"Error initializing Firebase: {e}")
            logger.warning("Starting FirebaseService in OFFLINE/SAFE MODE.")
            self.is_active = False  # Explicitly set to False


    async def get_banca_status(self):

        
        if not self.is_active:
            return {"saldo_total": 0, "risco_real_percent": 0, "slots_disponiveis": 10, "status": "OFFLINE"}
            
        try:
            # Wrap blocking call with timeout
            doc = await asyncio.wait_for(
                asyncio.to_thread(self.db.collection("banca_status").document("status").get),
                timeout=5.0  # 5 second timeout
            )
            if doc.exists:
                return doc.to_dict()
        except asyncio.TimeoutError:
            logger.error("Firebase timeout ao buscar banca status")
            self.is_active = False  # Disable Firebase on timeout
            return {"saldo_total": 0, "risco_real_percent": 0, "slots_disponiveis": 10, "status": "TIMEOUT"}
        except Exception as e:
            logger.error(f"Error fetching banca: {e}")
        return {"saldo_total": 0, "risco_real_percent": 0, "slots_disponiveis": 10, "status": "ERROR"}

    async def update_banca_status(self, data: dict):
        if not self.is_active: return data
        try:
            await asyncio.to_thread(self.db.collection("banca_status").document("status").set, data, merge=True)
        except Exception: pass
        return data

    async def get_active_slots(self):
        # Always return cache for immediate loop safety
        if not self.is_active: return self.slots_cache
        try:
            def _get_slots():
                docs = self.db.collection("slots_ativos").order_by("id").stream()
                return [doc.to_dict() for doc in docs]
            
            data = await asyncio.wait_for(asyncio.to_thread(_get_slots), timeout=3.0)
            if data and len(data) >= 1:
                # Update local cache with remote data if available
                self.slots_cache = data
            return self.slots_cache
        except Exception: 
            return self.slots_cache

    async def update_slot(self, slot_id: int, data: dict):
        # Update cache first
        for s in self.slots_cache:
            if s["id"] == slot_id:
                s.update(data)
                break
                
        if not self.is_active: return data
        try:
            await asyncio.to_thread(self.db.collection("slots_ativos").document(str(slot_id)).set, data, merge=True)
        except Exception: pass
        return data

    async def log_signal(self, signal_data: dict):
        # 1. Add to local buffer immediately
        signal_data["id"] = f"loc_{int(time.time() * 1000)}"
        signal_data["timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.signal_buffer.appendleft(signal_data)
        
        if not self.is_active: return signal_data["id"]
        try:
            # Wrap blocking call
            await asyncio.wait_for(asyncio.to_thread(self.db.collection("journey_signals").add, signal_data), timeout=5.0)
        except Exception as e: 
            logger.error(f"Erro ao logar sinal no Firebase: {e}")
        return signal_data["id"]

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

firebase_service = FirebaseService()
