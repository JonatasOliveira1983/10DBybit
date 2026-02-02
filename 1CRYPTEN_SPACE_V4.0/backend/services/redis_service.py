import logging
import json
import asyncio
import time
from config import settings
from typing import Optional, Any, Dict

# Use a standard dictionary for in-memory fallback
_LOCAL_CACHE: Dict[str, str] = {}
_LOCAL_EXPIRY: Dict[str, float] = {}

class MockRedis:
    """V5.4.5: Robust In-Memory Fallback for environments without Redis server."""
    async def ping(self): return True
    
    async def set(self, key: str, value: str, ex: int = None, nx: bool = False):
        if nx and key in _LOCAL_CACHE:
            # Check if expired
            if time.time() < _LOCAL_EXPIRY.get(key, float('inf')):
                return False
        
        _LOCAL_CACHE[key] = value
        if ex:
            _LOCAL_EXPIRY[key] = time.time() + ex
        else:
            _LOCAL_EXPIRY[key] = float('inf')
        return True

    async def get(self, key: str):
        if key in _LOCAL_CACHE:
            if time.time() < _LOCAL_EXPIRY.get(key, float('inf')):
                return _LOCAL_CACHE[key]
            else:
                del _LOCAL_CACHE[key]
                del _LOCAL_EXPIRY[key]
        return None

    async def delete(self, key: str):
        _LOCAL_CACHE.pop(key, None)
        _LOCAL_EXPIRY.pop(key, None)

    async def publish(self, channel: str, message: str):
        # Local Pub/Sub mock (just logs for now, or can be extended for local WS)
        return 1

logger = logging.getLogger("RedisService")

class RedisService:
    def __init__(self):
        self.client: Any = None
        self.host = settings.REDIS_HOST
        self.port = settings.REDIS_PORT
        self.db = settings.REDIS_DB
        self.is_connected = False
        self.is_fallback = False

    async def connect(self):
        """Initializes the Redis async client with robust fallback."""
        if self.is_connected:
            return
        
        try:
            import redis.asyncio as redis_lib
            self.client = redis_lib.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                decode_responses=True
            )
            # Test connection with short timeout
            await asyncio.wait_for(self.client.ping(), timeout=2.0)
            self.is_connected = True
            self.is_fallback = False
            logger.info(f"🚀 Redis Connected: {self.host}:{self.port} (DB {self.db})")
        except Exception as e:
            logger.warning(f"⚠️ Redis Connection Failed ({e}). Entering Gemini Fallback Mode (In-Memory).")
            self.client = MockRedis()
            self.is_connected = True
            self.is_fallback = True
            logger.info("💎 Gemini Fallback Active: System is now running in-memory.")

    async def set_ticker(self, symbol: str, price: float):
        """Caches the last price of a symbol (TTL: 60s)."""
        try:
            key = f"ticker:{symbol.upper()}"
            await self.client.set(key, str(price), ex=60)
        except Exception as e:
            logger.error(f"Redis set_ticker error: {e}")

    async def get_ticker(self, symbol: str) -> Optional[float]:
        """Retrieves cached price for a symbol."""
        try:
            val = await self.client.get(f"ticker:{symbol.upper()}")
            return float(val) if val else None
        except Exception: return None

    async def set_cvd(self, symbol: str, cvd: float):
        """Caches the cumulative delta score (TTL: 300s)."""
        try:
            key = f"cvd:{symbol.upper()}"
            await self.client.set(key, str(cvd), ex=300)
        except Exception as e:
            logger.error(f"Redis set_cvd error: {e}")

    async def get_cvd(self, symbol: str) -> float:
        """Retrieves cached CVD score."""
        try:
            val = await self.client.get(f"cvd:{symbol.upper()}")
            return float(val) if val else 0.0
        except Exception: return 0.0

    async def acquire_lock(self, lock_name: str, acquire_timeout: int = 5, lock_timeout: int = 10) -> bool:
        """Distributed atomic lock using SET NX or local Mock."""
        lock_key = f"lock:{lock_name}"
        end_time = time.time() + acquire_timeout
        
        while time.time() < end_time:
            # nx=True handles the atomic check
            if await self.client.set(lock_key, "locked", ex=lock_timeout, nx=True):
                return True
            await asyncio.sleep(0.05)
            
        return False

    async def release_lock(self, lock_name: str):
        """Releases a distributed lock."""
        try:
            await self.client.delete(f"lock:{lock_name}")
        except Exception: pass

    async def publish_update(self, channel: str, data: dict):
        """Publishes a message to a Redis channel for real-time UI updates."""
        try:
            await self.client.publish(channel, json.dumps(data))
        except Exception as e:
            logger.error(f"Redis publish error: {e}")

# Global Instance
redis_service = RedisService()
