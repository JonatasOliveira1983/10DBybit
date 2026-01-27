import sys
import traceback

try:
    print("DEBUG: Importing asyncio...")
    import asyncio
    print("DEBUG: Importing logging...")
    import logging
    from fastapi import FastAPI
    from contextlib import asynccontextmanager
    
    print("DEBUG: Importing basic services...")
    # Firebase service imported but disabled
    from services.firebase_service import firebase_service
    from services.bybit_rest import bybit_rest_service
    print("DEBUG: Agent imports disabled for debugging...")
    from services.bybit_ws import bybit_ws_service
    from services.bankroll import bankroll_manager
    from services.agents.guardian import guardian_agent
    from services.agents.gemini import gemini_agent
    from services.agents.contrarian import contrarian_agent
    from services.agents.captain import captain_agent
    from services.signal_generator import signal_generator
    print("DEBUG: Basic imports complete.")
    from fastapi.staticfiles import StaticFiles
    import uvicorn
    from config import settings

except Exception as e:
    print("CRITICAL STARTUP ERROR:")
    traceback.print_exc()
    sys.exit(1)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("1CRYPTEN-MAIN")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("🚀 Initializing 1CRYPTEN SPACE V4.0 Backend...")
    
    async def start_services():
        try:
            # 1. Initialize Firebase (Mandatory for DB features)
            logger.info("Step 1: Initializing Firebase...")
            await firebase_service.initialize()
            
            # 2. Fetch Top 100 Symbols
            logger.info("Step 2: Fetching Top Symbols...")
            symbols = await asyncio.to_thread(bybit_rest_service.get_top_100_usdt_pairs)
            logger.info(f"Step 2.1: Tracking top {len(symbols)} symbols.")
            
            # 2.2 Sync Slots with Bybit to clear stale entries and recover missing positions
            await bankroll_manager.sync_slots_with_exchange()

            # 3. Start WebSocket monitoring (ENABLED)

            if symbols:
                logger.info("Step 3: WebSocket Monitoring ENABLED.")
                await asyncio.to_thread(bybit_ws_service.start, symbols)
            
            # 4. Start Background Tasks
            logger.info("Step 4: Background loops ENABLED.")
            asyncio.create_task(guardian_agent.monitor_loop())
            asyncio.create_task(signal_generator.monitor_and_generate())
            asyncio.create_task(signal_generator.track_outcomes())
            asyncio.create_task(captain_agent.monitor_signals())
            # asyncio.create_task(gemini_agent.analyze_journey_and_recalibrate()) # Disabled for Sniper Mode
            
            # Start Bankroll Sync Loop
            async def bankroll_loop():
                while True:
                    try:
                        await bankroll_manager.update_banca_status()
                    except Exception as e:
                        logger.error(f"Error in bankroll loop: {e}")
                    await asyncio.sleep(60)
            asyncio.create_task(bankroll_loop())
            
            # 5. Initial Bankroll & DB Setup
            logger.info("Step 5: DB setup ENABLED.")
            await firebase_service.initialize_db()
            await bankroll_manager.update_banca_status()
            logger.info("✅ System Services started successfully (minimal mode).")
        except Exception as e:
            logger.error(f"❌ Error during background startup: {e}", exc_info=True)
    # Kick off background startup - COMPLETELY NON-BLOCKING FOR APP BOOT
    asyncio.create_task(start_services())
    
    yield
    # Shutdown logic
    logger.info("Shutting down...")

app = FastAPI(
    title="1CRYPTEN SPACE V4.0 API",
    version="4.0",
    lifespan=lifespan
)

# Server Frontend Static Files safely
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Navigate up from backend -> 1CRYPTEN_SPACE_V4.0 -> root -> frontend
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "frontend"))

if os.path.isdir(FRONTEND_DIR):
    logger.info(f"Frontend directory found at: {FRONTEND_DIR}")
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
else:
    logger.warning(f"⚠️ Frontend directory NOT found at {FRONTEND_DIR}. Static serving disabled.")

from fastapi.responses import FileResponse

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    fav_path = os.path.join(FRONTEND_DIR, "favicon.ico")
    if os.path.exists(fav_path):
        return FileResponse(fav_path)
    return {"error": "favicon not found"}

@app.get("/dashboard")
async def get_dashboard():
    # Return the code.html from the frontend folder
    index_path = os.path.join(FRONTEND_DIR, "code.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": "Dashboard file not found"}

@app.get("/")
async def root():
    index_path = os.path.join(FRONTEND_DIR, "code.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Backend Online. Dashboard not found."}

@app.get("/health") # Renamed from "/" to "/health" to avoid conflict with root()
async def health_check():
    return {
        "status": "online", 
        "version": "4.0", 
        "guardian": "disabled",
        "symbols_monitored": 0
    }


@app.get("/banca")
async def get_banca():
    # Fetch real status from Firebase or return fallback
    try:
        status = await firebase_service.get_banca_status()
        # If status is empty OR balance is 0, attempt real-time update
        if not status or status.get("saldo_total", 0) == 0:
            logger.info("Banca is empty or Offline, fetching real-time balance from Bybit...")
            equity = await asyncio.to_thread(bybit_rest_service.get_wallet_balance)
            return {
                "saldo_total": equity,
                "risco_real_percent": 0.0,
                "slots_disponiveis": 10,
                "status": "LIVE_FETCH"
            }
        return status
    except Exception as e:
        logger.error(f"Error fetching banca: {e}")
    
    # Fallback/Debug
    return {
        "saldo_total": 0.0,
        "risco_real_percent": 0.0,
        "slots_disponiveis": 10,
        "status": "ERROR"
    }

@app.get("/api/slots")
async def get_slots():
    try:
        slots = await firebase_service.get_active_slots()
        if slots:
            return slots
    except Exception as e:
        logger.error(f"Error fetching slots: {e}")
    
    # Fallback: 10 empty slots
    return [{"id": i, "symbol": None, "entry_price": 0, "current_stop": 0, "side": None} for i in range(1, 11)]

@app.get("/api/signals")
async def get_signals(min_score: int = 0, limit: int = 20):
    try:
        signals = await firebase_service.get_recent_signals(limit=limit)
        filtered = [s for s in signals if s.get("score", 0) >= min_score]
        if not filtered:
             return [{
                "id": "forced_debug",
                "symbol": "BTCUSDT",
                "score": 95,
                "indicators": {"cvd": 12.5},
                "is_elite": True,
                "timestamp": "Now"
            }]
        return filtered

    except Exception as e:
        logger.error(f"Error fetching signals: {e}")
        # Return a forced signal for UI visibility if error
        return [{
            "id": "forced_debug",
            "symbol": "BTCUSDT",
            "score": 95,
            "indicators": {"cvd": 10.5},
            "is_elite": True,
            "timestamp": "Now"
        }]

@app.get("/api/stats")
async def get_stats():
    # Placeholder for stats - can be expanded
    return {
        "win_rate": 0.0,
        "total_trades": 0,
        "profit_factor": 0.0
    }

@app.get("/api/history")
async def get_history(limit: int = 20):
    try:
        # Reusing get_recent_signals for history for now, or use a specific history method if exists
        return await firebase_service.get_recent_signals(limit=limit)
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        return []

@app.get("/api/logs")
async def get_logs(limit: int = 50):
    try:
        return await firebase_service.get_recent_logs(limit=limit)
    except Exception as e:
        logger.error(f"Error fetching logs: {e}")
        return [{"agent": "System", "message": "Backend Active - Waiting for Agents...", "level": "INFO", "timestamp": "Now"}]


@app.get("/api/btc/regime")
async def get_btc_regime():
    return {
        "regime": "BULLISH", # Placeholder or fetch from GeminiAgent
        "confidence": 0.95
    }


@app.post("/test-order")
async def test_order(symbol: str, side: str, sl: float):
    """Manual test endpoint - DISABLED FOR DEBUGGING"""
    return {"error": "Trading functions disabled for debugging"}

@app.post("/panic")
async def panic_button():
    """Emergency endpoint - DISABLED FOR DEBUGGING"""
    return {"error": "Trading functions disabled for debugging"}

if __name__ == "__main__":
    # Forcing reload=False to avoid multi-process complexity during debugging
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=False)
