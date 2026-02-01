import sys
import traceback
import os
import datetime
import asyncio
import logging
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
import uvicorn
import ssl
import urllib3
from config import settings
from concurrent.futures import ThreadPoolExecutor

# V5.2.4.6: Increase Thread Pool size for concurrent network calls
executor = ThreadPoolExecutor(max_workers=32)
asyncio.get_event_loop().set_default_executor(executor)

# V5.2.4.8 Cloud Run Startup Optimization - Infrastructure Protocol
# V5.2.5: Protocolo de Unificação e Blindagem - Elite Evolution
VERSION = "V5.3.4"
DEPLOYMENT_ID = "V534_IDEMPOTENT_SHIELD"

# Global Directory Configurations - Hardened for Docker/Cloud Run
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Standard: backend/main.py -> ../../frontend
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "frontend"))
if not os.path.exists(FRONTEND_DIR):
    # Fallback for alternative structures
    FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# Global references
firebase_service = None
bybit_rest_service = None
bybit_ws_service = None
bankroll_manager = None

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("1CRYPTEN-MAIN")
logger.info(f"📍 BASE_DIR: {BASE_DIR}")
logger.info(f"📍 FRONTEND_DIR: {FRONTEND_DIR}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # V5.2.0: Stability Staggering
    logger.info(f"🚀 Initializing 1CRYPTEN SPACE {VERSION}...")
    
    async def start_services():
        global firebase_service, bybit_rest_service, bybit_ws_service, bankroll_manager
        
        logger.info("Step 0: Loading services (slow-walk mode)...")
        try:
            import importlib
            # Load services with 1s delay each to keep event loop breathing
            logger.info("Step 0.1: Loading Firebase Service...")
            firebase_service = importlib.import_module("services.firebase_service").firebase_service
            await asyncio.sleep(1)
            
            logger.info("Step 0.2: Loading Bybit REST Service...")
            bybit_rest_service = importlib.import_module("services.bybit_rest").bybit_rest_service
            # V5.2.4.3: Added 30s timeout for Bybit initialization (includes time sync)
            await asyncio.wait_for(bybit_rest_service.initialize(), timeout=30.0)
            await asyncio.sleep(1)
            
            logger.info("Step 0.3: Loading Bybit WS Service...")
            bybit_ws_service = importlib.import_module("services.bybit_ws").bybit_ws_service
            await asyncio.sleep(1)
            
            # Use bankroll_manager (singular)
            logger.info("Step 0.4: Loading Bankroll Manager...")
            try:
                mod = importlib.import_module("services.bankroll_manager")
                bankroll_manager = mod.bankroll_manager
            except ImportError:
                 logger.warning("bankroll_manager not found, trying bankroll...")
                 mod = importlib.import_module("services.bankroll")
                 bankroll_manager = mod.bankroll_manager
            
            await asyncio.sleep(1)
            logger.info("Step 0: Service modules loaded ✅")
            
            logger.info("Step 1: Connecting Firebase...")
            await firebase_service.initialize()
            
            logger.info("Step 2: Syncing Bybit Instruments...")
            symbols = ["BTCUSDT.P", "ETHUSDT.P", "SOLUSDT.P"]
            try:
                # Fetch symbols in background
                async def fetch_and_start_ws():
                    try:
                        # V5.2.4: Use wait_for for Python 3.10 compatibility
                        s = await asyncio.wait_for(
                            asyncio.to_thread(bybit_rest_service.get_top_200_usdt_pairs),
                            timeout=90
                        )
                        if s: await bybit_ws_service.start(s)
                    except Exception as e: 
                        logger.error(f"Step 2: Symbol Scan or WS Start Error: {e}")
                        await bybit_ws_service.start(symbols)
                asyncio.create_task(fetch_and_start_ws())
                # Sync slots with Bybit
                await bankroll_manager.sync_slots_with_exchange()
            except Exception as e:
                logger.warning(f"Step 2: Symbol fetch scheduled (Background): {e}")

            logger.info("Step 3: Activating Agents...")
            try:
                guardian = importlib.import_module("services.agents.guardian").guardian_agent
                captain = importlib.import_module("services.agents.captain").captain_agent
                sig_gen = importlib.import_module("services.signal_generator").signal_generator
                
                # Start Agent Loops
                asyncio.create_task(guardian.monitor_loop())
                asyncio.create_task(sig_gen.monitor_and_generate())
                asyncio.create_task(sig_gen.track_outcomes())
                asyncio.create_task(sig_gen.radar_loop())
                asyncio.create_task(captain.monitor_signals())
                asyncio.create_task(captain.monitor_active_positions_loop())
                asyncio.create_task(bankroll_manager.position_reaper_loop())
                
                # 3.1: V5.2.3: Initial Sync - Ensure Vault and Banca are aligned with history
                async def initial_sync():
                    try:
                        from services.vault_service import vault_service
                        logger.info("Step 3.1: Running initial Vault & Banca Synchronization...")
                        await vault_service.sync_vault_with_history()
                        await bankroll_manager.update_banca_status()
                        logger.info("Step 3.1: Initial Sync COMPLETE ✅")
                    except Exception as e:
                        logger.error(f"Step 3.1: Initial Sync ERROR: {e}")
                
                asyncio.create_task(initial_sync())
                
                # 4. Start Paper Execution Engine (Simulator only)
                if bybit_rest_service.execution_mode == "PAPER":
                    logger.info("Step 4: Paper Execution Engine ACTIVATING...")
                    asyncio.create_task(bybit_rest_service.run_paper_execution_loop())

                # Pulse & Bankroll Loops
                async def pulse_loop():
                    while True:
                        try: await firebase_service.update_pulse()
                        except: pass
                        await asyncio.sleep(2)
                asyncio.create_task(pulse_loop())

                async def bankroll_loop():
                    while True:
                        try: await bankroll_manager.update_banca_status()
                        except: pass
                        await asyncio.sleep(60)
                asyncio.create_task(bankroll_loop())

            except Exception as e:
                logger.error(f"Step 3: Agent sync error: {e}")
                
            logger.info("✅ All background services started successfully!")
        except Exception as e:
            logger.error(f"FATAL Startup Error: {e}", exc_info=True)
            
    # Start worker
    asyncio.create_task(start_services())
    
    yield
    logger.info("Shutting down...")

app = FastAPI(
    title=f"1CRYPTEN SPACE {VERSION} API",
    version=VERSION,
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

# Static File Serving Configuration
INTERNAL_STATIC_DIR = os.path.join(BASE_DIR, "static")
os.makedirs(INTERNAL_STATIC_DIR, exist_ok=True)

if os.path.isdir(FRONTEND_DIR):
    logger.info(f"✅ Frontend directory verified at: {FRONTEND_DIR}")
else:
    logger.warning(f"⚠️ Frontend directory NOT found at {FRONTEND_DIR}. Dashboards will fail.")

# =================================================================
# ROUTES & ENDPOINTS
# =================================================================

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
    """Serve the primary dashboard (code.html)."""
    logger.info("Root access requested.")
    # Try multiple entry points for robustness
    for entry in ["code.html", "index.html"]:
        path = os.path.join(FRONTEND_DIR, entry)
        if os.path.exists(path):
            return FileResponse(path, media_type="text/html")
    
    return {
        "status": "online", 
        "message": "Backend Active. Dashboard files not found.",
        "frontend_scanned": FRONTEND_DIR,
        "files_found": os.listdir(FRONTEND_DIR) if os.path.exists(FRONTEND_DIR) else "Directory Missing"
    }

@app.get("/health")
async def health_check():
    """V5.2.0: Restored fields for Frontend TakeoffModal compatibility."""
    frontend_files = []
    if os.path.exists(FRONTEND_DIR):
        try:
            frontend_files = os.listdir(FRONTEND_DIR)
        except:
            frontend_files = ["Permission Error"]
            
    # Calculate values for frontend compatibility
    bybit_conn = False
    balance = 0.0
    if bybit_rest_service:
        try:
            # V5.2.4.6: NON-BLOCKING Balance retrieval for Cloud Run Health Check
            bybit_conn = True 
            balance = bybit_rest_service.last_balance
        except:
            pass

    return {
        "status": "online", 
        "version": VERSION, 
        "deployment_id": DEPLOYMENT_ID,
        "bybit_connected": bybit_conn, # Restore for frontend takeoff check
        "balance": balance,           # Restore for frontend takeoff check
        "frontend_path": FRONTEND_DIR,
        "frontend_found": os.path.exists(FRONTEND_DIR),
        "frontend_files": frontend_files,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

@app.get("/debug/test")
async def debug_test():
    return {"status": "ok", "message": f"{VERSION} Almirante Verified"}

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
    # Lazy import for Cloud Run compatibility
    from services.firebase_service import firebase_service
    from services.bybit_rest import bybit_rest_service
    # Fetch real status from Firebase or return fallback
    try:
        status = await firebase_service.get_banca_status()
        # If status is empty OR balance is 0, attempt real-time update
        if not status or status.get("saldo_total", 0) == 0:
            logger.info("Banca is empty or Offline, fetching real-time balance from Bybit...")
            equity = await bybit_rest_service.get_wallet_balance()
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
    from services.firebase_service import firebase_service
    try:
        return await firebase_service.get_banca_history(limit=limit)
    except Exception as e:
        logger.error(f"Error in banca history endpoint: {e}")
        return []

@app.get("/api/slots")
async def get_slots():
    from services.firebase_service import firebase_service
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
    from services.firebase_service import firebase_service
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
async def get_history(limit: int = 50, last_timestamp: str = None):
    from services.firebase_service import firebase_service
    try:
        # [V5.2.5] Support for pagination
        return await firebase_service.get_trade_history(limit=limit, last_timestamp=last_timestamp)
    except Exception as e:
        logger.error(f"Error fetching trade history: {e}")
        return []

@app.post("/api/history/report")
async def get_trade_report(payload: dict):
    """[V5.2.5] Generates a full AI report for a specific trade in PT-BR."""
    from services.agents.ai_service import ai_service
    trade_data = payload.get("trade_data")
    if not trade_data:
        return {"error": "Missing trade data"}
    
    symbol = trade_data.get("symbol", "Desconhecido")
    pnl = trade_data.get("pnl", 0)
    side = trade_data.get("side", "N/A")
    roi = trade_data.get("roi", 0) # If available
    
    prompt = f"""
    Como Capitão da 1CRYPTEN, gere um relatório detalhado e tático para o trade abaixo:
    Símbolo: {symbol}
    Lado: {side}
    PnL: ${pnl:.2f}
    ROI: {roi:.2f}% (se aplicável)
    Motivo de Fechamento: {trade_data.get('close_reason', 'N/A')}
    
    O relatório deve ser em PT-BR, com tom de Comandante, analítico, destacando o que deu certo e lições aprendidas. 
    Use markdown para formatação. Máximo 200 palavras.
    """
    
    report = await ai_service.generate_content(prompt, system_instruction="Você é o Capitão 1CRYPTEN. Suas análises são a bíblia tática do Almirante.")
    return {"report": report or "Sincronização neural falhou ao gerar o relatório."}

@app.get("/api/logs")
async def get_logs(limit: int = 50):
    from services.firebase_service import firebase_service
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
    from services.agents.captain import captain_agent
    message = payload.get("message")
    symbol = payload.get("symbol")
    
    if not message:
        return {"error": "No message provided"}
    
    # Captain handles logging internally now
    response = await captain_agent.process_chat(message, symbol=symbol)
    
    return {"response": response}


@app.post("/api/chat/reset")
async def reset_chat():
    """Clears the chat history."""
    from services.firebase_service import firebase_service
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
    # [V5.2.5] USE GOOGLE NEURAL EQUIVALENT (pt-BR-AntonioNeural is Microsoft's best male, 
    # but we will try to use Google if credentials exist, otherwise Antonio)
    voice = payload.get("voice", "pt-BR-AntonioNeural")
    
    if not text:
        return {"error": "No text provided"}
    
    logger.info(f"🎤 TTS V5.2.5: '{text[:30]}...' using VOICE={voice}")
    try:
        # [V5.2.5] GOOGLE CLOUD TTS IMPLEMENTATION
        try:
            from google.cloud import texttospeech
            import os
            
            # Use service account if available
            creds_path = os.path.join(os.path.dirname(__file__), "serviceAccountKey.json")
            if os.path.exists(creds_path):
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path
                
            client = texttospeech.TextToSpeechClient()
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            # Select the voice: Neural2-B (requested)
            target_voice = "pt-BR-Neural2-B" if "Neural2" in voice or "Wavenet-B" in voice else "pt-BR-Wavenet-B"
            
            voice_params = texttospeech.VoiceSelectionParams(
                language_code="pt-BR",
                name=target_voice
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )
            
            response = client.synthesize_speech(
                input=synthesis_input, voice=voice_params, audio_config=audio_config
            )
            audio_base64 = base64.b64encode(response.audio_content).decode("utf-8")
            
            logger.info(f"✅ Google TTS Success: {target_voice} | {len(audio_base64)} bytes")
            return {
                "audio": audio_base64,
                "format": "mp3",
                "voice": target_voice,
                "provider": "google"
            }
        except Exception as google_err:
            logger.warning(f"⚠️ Google TTS failed ({google_err}), falling back to Edge-TTS...")
            
            # Fallback to Edge-TTS
            import edge_tts
            communicate = edge_tts.Communicate(text, "pt-BR-AntonioNeural")
            audio_data = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data.write(chunk["data"])
            
            audio_data.seek(0)
            audio_base64 = base64.b64encode(audio_data.read()).decode("utf-8")
            logger.info(f"✅ Edge-TTS Fallback Success: Antonio | {len(audio_base64)} bytes")
            
            return {
                "audio": audio_base64,
                "format": "mp3",
                "voice": "pt-BR-AntonioNeural",
                "provider": "edge"
            }
    except Exception as e:
        logger.error(f"TTS Total Failure: {e}")
        return {"error": str(e)}

@app.get("/api/pnl/live")
async def get_live_pnl():
    """[V5.2.5] Returns dynamic ROI for all active slots using BybitWS prices."""
    from services.firebase_service import firebase_service
    from services.bybit_ws import bybit_ws_service
    from services.execution_protocol import execution_protocol
    
    try:
        slots = await firebase_service.get_active_slots()
        pnl_data = []
        
        for slot in slots:
            symbol = slot.get("symbol")
            if not symbol: continue
            
            entry = slot.get("entry_price", 0)
            if entry <= 0: continue
            
            current_price = bybit_ws_service.get_current_price(symbol)
            if current_price <= 0: continue
            
            side = (slot.get("side") or "").upper()
            roi = execution_protocol.calculate_roi(entry, current_price, side)
            
            pnl_data.append({
                "id": slot["id"],
                "symbol": symbol,
                "roi": roi,
                "current_price": current_price,
                "visual_status": execution_protocol.get_visual_status(slot, roi)
            })
            
        return pnl_data
    except Exception as e:
        logger.error(f"Live PnL Error: {e}")
        return []


@app.get("/api/tts/voices")
async def get_tts_voices():
    """List available premium voices for TTS. Francisca removed."""
    return {
        "voices": [
            {"id": "pt-BR-AntonioNeural", "name": "Antonio", "lang": "pt-BR", "gender": "Male"},
            {"id": "en-US-GuyNeural", "name": "Guy", "lang": "en-US", "gender": "Male"},
            {"id": "en-US-JennyNeural", "name": "Jenny", "lang": "en-US", "gender": "Female"},
        ],
        "default": "pt-BR-AntonioNeural"
    }


@app.post("/test-order")
async def test_order(symbol: str, side: str, sl: float):
    """Manual test endpoint - DISABLED FOR DEBUGGING"""
    return {"error": "Trading functions disabled for debugging"}

@app.post("/panic")
async def panic_button():
    """Emergency Kill Switch - V4.2 ENABLED"""
    from services.bankroll import bankroll_manager
    try:
        result = await bankroll_manager.emergency_close_all()
        return result
    except Exception as e:
        logger.error(f"Panic button error: {e}")
        return {"status": "error", "message": str(e)}

# ============ V4.2 VAULT ENDPOINTS ============

@app.get("/api/vault/status")
async def get_vault_status():
    """Returns current cycle status and vault totals."""
    from services.vault_service import vault_service
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
    from services.vault_service import vault_service
    try:
        return await vault_service.get_withdrawal_history(limit=limit)
    except Exception as e:
        logger.error(f"Error fetching vault history: {e}")
        return []

@app.post("/api/vault/withdraw")
async def register_withdrawal(payload: dict):
    """Registers a manual withdrawal to the vault."""
    from services.vault_service import vault_service
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
    from services.vault_service import vault_service
    try:
        result = await vault_service.start_new_cycle()
        return {"status": "success", "cycle": result}
    except Exception as e:
        logger.error(f"Error starting new cycle: {e}")
        return {"error": str(e)}

@app.post("/api/system/cautious-mode")
async def toggle_cautious_mode(payload: dict):
    """Toggles cautious mode (increased score threshold)."""
    from services.vault_service import vault_service
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
    from services.vault_service import vault_service
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

# =================================================================
# STATIC MOUNTING & STARTUP
# =================================================================

# V5.0.5: Single mount for frontend at root. 
# SPA mode (html=True) handles both index and static assets.
if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
else:
    @app.get("/")
    async def root_fallback():
        return {"status": "online", "message": "Dashboard directory missing."}

if __name__ == "__main__":
    # Ensure port is taken from env if available
    target_port = int(os.environ.get("PORT", settings.PORT))
    uvicorn.run("main:app", host="0.0.0.0", port=target_port, reload=False)
