import sys
import traceback

try:
    print("DEBUG: Importing asyncio...")
    import asyncio
    print("DEBUG: Importing logging...")
    import logging
    from fastapi import FastAPI
    from fastapi.responses import FileResponse
    from fastapi.middleware.cors import CORSMiddleware
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
    # V4.3.2: Cloud Run Optimized Startup - FULLY NON-BLOCKING
    # Health checks must succeed BEFORE services are fully initialized
    logger.info("🚀 Initializing 1CRYPTEN SPACE V4.5.0 Backend...")
    logger.info("☁️ Cloud Run Mode: Fast startup, async service initialization")
    
    async def start_services():
        """Background service initialization - does NOT block app startup"""
        try:
            # Give Cloud Run time to confirm health check first
            await asyncio.sleep(2)
            
            # 1. Initialize Firebase with timeout protection
            logger.info("Step 1: Initializing Firebase (background)...")
            try:
                await asyncio.wait_for(firebase_service.initialize(), timeout=30.0)
                logger.info("Step 1: Firebase initialized ✅")
            except asyncio.TimeoutError:
                logger.warning("Step 1: Firebase init timeout - continuing in offline mode")
            
            # 2. Fetch Top Symbols with timeout
            logger.info("Step 2: Fetching Top Symbols...")
            try:
                symbols = await asyncio.wait_for(
                    asyncio.to_thread(bybit_rest_service.get_top_200_usdt_pairs),
                    timeout=30.0
                )
                logger.info(f"Step 2.1: Tracking top {len(symbols)} symbols.")
            except asyncio.TimeoutError:
                logger.warning("Step 2: Symbol fetch timeout - using defaults")
                symbols = ["BTCUSDT.P", "ETHUSDT.P", "SOLUSDT.P"]
            
            # 2.2 Sync Slots with Bybit (non-critical)
            logger.info("Step 2.2: Syncing slots...")
            try:
                await asyncio.wait_for(bankroll_manager.sync_slots_with_exchange(), timeout=15.0)
            except Exception as e:
                logger.warning(f"Step 2.2: Slot sync skipped: {e}")
            
            # 3. Start WebSocket monitoring
            if symbols:
                logger.info("Step 3: WebSocket Monitoring ENABLED.")
                try:
                    await bybit_ws_service.start(symbols)
                except Exception as e:
                    logger.error(f"Step 3: WebSocket start error: {e}")
            
            # 4. Start Background Tasks
            logger.info("Step 4: Background loops ENABLED.")
            asyncio.create_task(guardian_agent.monitor_loop())
            asyncio.create_task(signal_generator.monitor_and_generate())
            asyncio.create_task(signal_generator.track_outcomes())
            asyncio.create_task(bankroll_manager.position_reaper_loop())
            asyncio.create_task(signal_generator.radar_loop())
            asyncio.create_task(captain_agent.monitor_signals())
            asyncio.create_task(captain_agent.monitor_active_positions_loop())
            
            # Start Pulse Monitor Loop (V4.0 Heartbeat)
            async def pulse_loop():
                while True:
                    try:
                        await firebase_service.update_pulse()
                    except Exception: pass
                    await asyncio.sleep(2)
            asyncio.create_task(pulse_loop())

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
            try:
                await asyncio.wait_for(firebase_service.initialize_db(), timeout=15.0)
                await asyncio.wait_for(bankroll_manager.update_banca_status(), timeout=15.0)
            except Exception as e:
                logger.warning(f"Step 5: DB setup error (non-fatal): {e}")

            # 6. Start Paper Execution Engine (Simulator only)
            if bybit_rest_service.execution_mode == "PAPER":
                logger.info("Step 6: Paper Execution Engine ACTIVATING...")
                asyncio.create_task(bybit_rest_service.run_paper_execution_loop())

            logger.info("✅ All background services started successfully!")
        except Exception as e:
            logger.error(f"❌ Error during background startup: {e}", exc_info=True)
    
    # V4.3.2: Start services in background - DO NOT AWAIT
    # This allows FastAPI to start responding to health checks immediately
    asyncio.create_task(start_services())
    
    # Signal to Cloud Run that we're ready BEFORE services finish
    logger.info("✅ FastAPI app ready - accepting connections")
    logger.info(f"🔗 Listening on port {os.environ.get('PORT', 5001)}")
    
    yield
    # Shutdown logic
    logger.info("Shutting down...")

app = FastAPI(
    title="1CRYPTEN SPACE V4.5.0 API",
    version="4.5.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this. For local dev/file open, * is needed.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Server Frontend Static Files safely
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Navigate up from backend -> 1CRYPTEN_SPACE_V4.0 -> root -> frontend
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "frontend"))

# Prioritize internal static folder for assets
INTERNAL_STATIC_DIR = os.path.join(BASE_DIR, "static")
if not os.path.isdir(INTERNAL_STATIC_DIR):
    os.makedirs(INTERNAL_STATIC_DIR, exist_ok=True)

if not os.path.isdir(FRONTEND_DIR):
    logger.warning(f"⚠️ Frontend directory NOT found at {FRONTEND_DIR}. PWA features might failing.")
else:
    logger.info(f"Frontend directory established at: {FRONTEND_DIR}")
    # Mount Frontend at root first
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="frontend_static")

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
        return FileResponse(index_path, media_type="text/html")
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

@app.get("/banca/ui")
async def get_banca_ui():
    """Serve the Banca Command Center HTML page."""
    banca_html_path = os.path.join(FRONTEND_DIR, "banca_command_center_v4.0", "code.html")
    if os.path.exists(banca_html_path):
        return FileResponse(banca_html_path)
    return {"error": "Banca UI file not found"}

@app.get("/vault/ui")
async def get_vault_ui():
    """Serve the Vault Management HTML page."""
    vault_html_path = os.path.join(FRONTEND_DIR, "vault_v4.0", "code.html")
    if os.path.exists(vault_html_path):
        return FileResponse(vault_html_path)
    return {"error": "Vault UI file not found"}

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

@app.get("/api/banca-history")
async def get_banca_history(limit: int = 50):
    try:
        return await firebase_service.get_banca_history(limit=limit)
    except Exception as e:
        logger.error(f"Error in banca history endpoint: {e}")
        return []

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
async def get_history(limit: int = 50):
    try:
        # Fetch real trade history instead of generic signals
        return await firebase_service.get_trade_history(limit=limit)
    except Exception as e:
        logger.error(f"Error fetching trade history: {e}")
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

@app.post("/api/chat")
async def chat_with_captain(payload: dict):
    """Interactive endpoint to talk to the Captain."""
    message = payload.get("message")
    symbol = payload.get("symbol")
    
    if not message:
        return {"error": "No message provided"}
    
    
    # Captain handles logging internally now
    # 2. Process via Captain (symbol is passed only here for internal context)
    response = await captain_agent.process_chat(message, symbol=symbol)
    
    return {"response": response}


@app.post("/api/chat/reset")
async def reset_chat():
    """Clears the chat history."""
    await firebase_service.clear_chat_history()
    return {"status": "success", "message": "Chat history cleared."}


# ============ V4.3.1 PREMIUM TTS ENDPOINT ============
@app.post("/api/tts")
async def text_to_speech(payload: dict):
    """
    Premium Text-to-Speech using Edge-TTS (Free Microsoft Voices).
    Returns base64 encoded MP3 audio.
    """
    import edge_tts
    import base64
    import io
    
    text = payload.get("text", "")
    voice = payload.get("voice", "pt-BR-FranciscaNeural")  # Premium Brazilian voice
    
    if not text:
        return {"error": "No text provided"}
    
    try:
        # Generate audio
        communicate = edge_tts.Communicate(text, voice)
        audio_data = io.BytesIO()
        
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.write(chunk["data"])
        
        audio_data.seek(0)
        audio_base64 = base64.b64encode(audio_data.read()).decode("utf-8")
        
        return {
            "audio": audio_base64,
            "format": "mp3",
            "voice": voice
        }
    except Exception as e:
        logger.error(f"TTS Error: {e}")
        return {"error": str(e)}


@app.get("/api/tts/voices")
async def get_tts_voices():
    """List available premium voices for TTS."""
    return {
        "voices": [
            {"id": "pt-BR-FranciscaNeural", "name": "Francisca", "lang": "pt-BR", "gender": "Female"},
            {"id": "pt-BR-AntonioNeural", "name": "Antonio", "lang": "pt-BR", "gender": "Male"},
            {"id": "en-US-GuyNeural", "name": "Guy", "lang": "en-US", "gender": "Male"},
            {"id": "en-US-JennyNeural", "name": "Jenny", "lang": "en-US", "gender": "Female"},
        ],
        "default": "pt-BR-FranciscaNeural"
    }


@app.post("/test-order")
async def test_order(symbol: str, side: str, sl: float):
    """Manual test endpoint - DISABLED FOR DEBUGGING"""
    return {"error": "Trading functions disabled for debugging"}

@app.post("/panic")
async def panic_button():
    """Emergency Kill Switch - V4.2 ENABLED"""
    try:
        result = await bankroll_manager.emergency_close_all()
        return result
    except Exception as e:
        logger.error(f"Panic button error: {e}")
        return {"status": "error", "message": str(e)}

# ============ V4.2 VAULT ENDPOINTS ============

from services.vault_service import vault_service

@app.get("/api/vault/status")
async def get_vault_status():
    """Returns current cycle status and vault totals."""
    try:
        status = await vault_service.get_cycle_status()
        calc = await vault_service.calculate_withdrawal_amount()
        return {
            **status,
            "recommended_withdrawal": calc.get("recommended_20pct", 0)
        }
    except Exception as e:
        logger.error(f"Error fetching vault status: {e}")
        return {"error": str(e)}

@app.get("/api/vault/history")
async def get_vault_history(limit: int = 20):
    """Returns withdrawal history."""
    try:
        return await vault_service.get_withdrawal_history(limit=limit)
    except Exception as e:
        logger.error(f"Error fetching vault history: {e}")
        return []

@app.post("/api/vault/withdraw")
async def register_withdrawal(payload: dict):
    """Registers a manual withdrawal to the vault."""
    amount = payload.get("amount", 0)
    if amount <= 0:
        return {"error": "Amount must be greater than 0"}
    
    try:
        success = await vault_service.execute_withdrawal(float(amount))
        if success:
            return {"status": "success", "amount": amount}
        return {"status": "error", "message": "Failed to register withdrawal"}
    except Exception as e:
        logger.error(f"Error registering withdrawal: {e}")
        return {"error": str(e)}

@app.post("/api/vault/new-cycle")
async def start_new_cycle():
    """Starts a new trading cycle."""
    try:
        result = await vault_service.start_new_cycle()
        return {"status": "success", "cycle": result}
    except Exception as e:
        logger.error(f"Error starting new cycle: {e}")
        return {"error": str(e)}

@app.post("/api/system/cautious-mode")
async def toggle_cautious_mode(payload: dict):
    """Toggles cautious mode (increased score threshold)."""
    enabled = payload.get("enabled", False)
    min_score = payload.get("min_score", 85)
    
    try:
        await vault_service.set_cautious_mode(enabled, min_score)
        return {"status": "success", "cautious_mode": enabled, "min_score": min_score}
    except Exception as e:
        logger.error(f"Error toggling cautious mode: {e}")
        return {"error": str(e)}

@app.post("/api/system/admiral-rest")
async def toggle_admiral_rest(payload: dict):
    """Activates/deactivates Admiral's Rest mode."""
    activate = payload.get("activate", False)
    hours = payload.get("hours", 24)
    
    try:
        if activate:
            await vault_service.activate_admiral_rest(hours)
            return {"status": "success", "admiral_rest": True, "hours": hours}
        else:
            await vault_service.deactivate_admiral_rest()
            return {"status": "success", "admiral_rest": False}
    except Exception as e:
        logger.error(f"Error toggling admiral rest: {e}")
        return {"error": str(e)}

# Mount Frontend as main source
if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

if __name__ == "__main__":
    # Forcing reload=False to avoid multi-process complexity during debugging
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=False)
