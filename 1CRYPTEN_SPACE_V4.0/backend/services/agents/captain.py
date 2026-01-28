import logging
import asyncio
from datetime import datetime, timezone
from services.firebase_service import firebase_service
from services.bankroll import bankroll_manager
from services.agents.ai_service import ai_service
from services.agents.contrarian import contrarian_agent
from services.agents.guardian import guardian_agent
from services.agents.news_sensor import news_sensor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CaptainAgent")

class CaptainAgent:
    def __init__(self):
        self.is_running = False

    async def monitor_signals(self):
        """
        Monitors the journey_signals table for elite signals and executes trades via BankrollManager.
        """
        self.is_running = True
        await firebase_service.log_event("Captain", "Sniper mode activated. Monitoring elite signals.", "SUCCESS")
        
        while self.is_running:
            try:
                # 1. Fetch recent signals not yet processed
                signals = await firebase_service.get_recent_signals(limit=10)
                
                # 1.1 Refresh active slots ONCE per cycle to avoid double entry and save Firebase quota
                active_slots = await firebase_service.get_active_slots()
                active_symbols = [s["symbol"] for s in active_slots if s.get("symbol")]

                logger.info(f"Captain scanned {len(signals)} signals. Active: {len(active_symbols)}")
                
                for signal in signals:
                    # Skip if already has an outcome (means it was already processed)
                    if signal.get("outcome") is not None:
                        continue

                    # Sniper Rule: Skip BTCUSDT (Only use BTC as market compass)
                    if "BTCUSDT" in signal["symbol"]:
                        continue

                    if signal["symbol"] in active_symbols:
                        continue

                    # Efficiency: Use fixed threshold (85) since ML is disabled
                    sniper_threshold = 85
                    if signal["score"] < sniper_threshold:
                         continue


                    # 2. Sensor Audit (V4.0 Sovereignty)
                    contrarian_advice = await contrarian_agent.analyze(signal["symbol"])
                    is_healthy, latency = await guardian_agent.check_api_health()
                    news_advice = await news_sensor.analyze()
                    
                    # 3. Decision & Reasoning
                    cvd = signal.get("indicators", {}).get("cvd", 0)
                    side = "Buy" if cvd >= 0 else "Sell"
                    
                    pensamento_base = f"Soberania V4.0: Analisei o fluxo (CVD: {cvd:.2f}). "
                    
                    if contrarian_advice.get("sentiment") == side:
                        pensamento_base += "Contrarian confirma força. "
                    else:
                        pensamento_base += "Entrada técnica por exaustão. "
                    
                    pensamento_base += news_advice.get("pensamento", "") + " "
                    
                    if not is_healthy:
                        pensamento_base += "⚠️ Cuidado: Latência elevada."
                    else:
                        pensamento_base += "🛡️ Latência OK."

                    # Enhanced AI Thought (GLM-4.7 Primary)
                    prompt_ai = f"""
                    Como Capitão da Nave 1CRYPTEN, justifique em uma frase curta e técnica sua entrada em {signal['symbol']} ({side}).
                    Indicadores: CVD={cvd:.2f}, Score={signal['score']}, Contrarian={contrarian_advice.get('sentiment')}.
                    Contexto: {pensamento_base}
                    """
                    ai_thought = await ai_service.generate_content(prompt_ai, system_instruction="Você é o Capitão Soberano da 1CRYPTEN. Fale de forma institucional e precisa.")
                    pensamento = ai_thought if ai_thought else pensamento_base

                    # 4. Try to open position
                    logger.info(f"Captain executing Elite Signal: {signal['symbol']} (Score: {signal['score']})")
                    await firebase_service.log_event("Captain", f"Executing Sniping protocol for {signal['symbol']} (Score: {signal['score']})", "SUCCESS")
                    
                    # Execute via BankrollManager
                    await bankroll_manager.open_position(
                        symbol=signal["symbol"],
                        side=side,
                        pensamento=pensamento # Pass the reasoning to bankroll
                    )

                await asyncio.sleep(10) # Reduced scan frequency to 10s
            except Exception as e:
                logger.error(f"Error in Captain monitor loop: {e}")
                await asyncio.sleep(10)

    async def monitor_active_positions_loop(self):
        """
        Periodically analyzes active trades and provides AI commentary (telemetry).
        """
        logger.info("Captain Telemetry loop active.")
        while self.is_running:
            try:
                active_slots = await firebase_service.get_active_slots()
                trading_slots = [s for s in active_slots if s.get("symbol")]
                
                if not trading_slots:
                    await asyncio.sleep(60)
                    continue

                # AI Quota Saver: Pick only ONE slot per cycle to provide telemetry
                import random
                slot = random.choice(trading_slots)
                
                symbol = slot["symbol"]
                pnl = slot.get("pnl_percent", 0)
                side = slot.get("side", "Buy")
                
                # Generate short telemetry update
                prompt = f"Como Capitão da 1CRYPTEN, forneça uma telemetria neural curtíssima (máximo 12 palavras) para {symbol} ({side}) com {pnl:.2f}% ROI. Seja técnico."
                telemetry = await ai_service.generate_content(prompt, system_instruction="Você é o Capitão Soberano. Sua fala é telemetria neural de elite.")
                
                if not telemetry:
                    # Technical Fallback if AI is offline/unbalanced
                    telemetry = f"Vetor {symbol} em {pnl:.2f}% ROI. Sincronia {side} ativa."
                
                # Ensure symbol is in the message for frontend filtering
                await firebase_service.log_event("Captain", f"[{symbol}] TELEMETRIA: {telemetry}", "INFO")

                await asyncio.sleep(300) # Full sweep every 5 minutes to save quota
            except Exception as e:
                logger.error(f"Error in telemetry loop: {e}")
                await asyncio.sleep(60)

captain_agent = CaptainAgent()
