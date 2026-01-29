import logging
import asyncio
from datetime import datetime, timezone
from services.firebase_service import firebase_service
from services.bankroll import bankroll_manager
from services.agents.ai_service import ai_service
from services.agents.contrarian import contrarian_agent
from services.agents.guardian import guardian_agent
from services.agents.news_sensor import news_sensor
from services.bybit_rest import bybit_rest_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CaptainAgent")

def normalize_symbol(symbol: str) -> str:
    """Normaliza símbolos removendo .P para comparação consistente."""
    if not symbol:
        return symbol
    return symbol.replace(".P", "").upper()

class CaptainAgent:
    def __init__(self):
        self.is_running = False

    async def monitor_signals(self):
        """
        Monitors the journey_signals table for elite signals and executes trades via BankrollManager.
        """
        self.is_running = True
        await firebase_service.log_event("SNIPER", "Sniper mode activated. Monitoring elite signals.", "SUCCESS")
        
        while self.is_running:
            try:
                # 1. Fetch recent signals not yet processed
                signals = await firebase_service.get_recent_signals(limit=10)
                
                # 1.1 Refresh active slots ONCE per cycle to avoid double entry and save Firebase quota
                active_slots = await firebase_service.get_active_slots()
                active_symbols = [normalize_symbol(s["symbol"]) for s in active_slots if s.get("symbol")]

                logger.info(f"Captain scanned {len(signals)} signals. Active: {len(active_symbols)}")
                
                for signal in signals:
                    # Skip if already has an outcome (means it was already processed)
                    if signal.get("outcome") is not None:
                        continue

                    # Sniper Rule: Skip BTCUSDT (Only use BTC as market compass)
                    if "BTCUSDT" in signal["symbol"]:
                        logger.info(f"Captain: Skipping BTC signal {signal['symbol']}. Used as market compass only.")
                        continue

                    # Check if symbol already in active slots (normalized comparison)
                    if normalize_symbol(signal["symbol"]) in active_symbols:
                        continue

                    # Efficiency: Use calibrated threshold (75) to match Signal Generator
                    sniper_threshold = 75
                    if signal["score"] < sniper_threshold:
                         continue


                    # 2. Sensor Audit (V4.0 Sovereignty)
                    contrarian_advice = await contrarian_agent.analyze(signal["symbol"])
                    is_healthy, latency = await guardian_agent.check_api_health()
                    news_advice = await news_sensor.analyze()
                    
                    # 3. Decision & Reasoning (V4.2 Trend Guard)
                    cvd = signal.get("indicators", {}).get("cvd", 0)
                    side = "Buy" if cvd >= 0 else "Sell"
                    
                    # Trend Guard: Fetch current price and compare with recent context
                    clean_symbol = signal["symbol"].replace(".P", "")
                    ticker = await asyncio.to_thread(bybit_rest_service.session.get_tickers, category="linear", symbol=clean_symbol)
                    ticker_data = ticker.get("result", {}).get("list", [{}])[0]
                    last_price = float(ticker_data.get("lastPrice", 0))
                    mark_price = float(ticker_data.get("markPrice", 0))
                    
                    # Simple Trend Filter: In Long, mark_price should be >= last_price (bullish pressure)
                    # Softened filter: 0.5% tolerance to allow more entries
                    price_trend_ok = True
                    if side == "Buy" and mark_price < last_price * 0.995: # Dumping hard
                        price_trend_ok = False
                    if side == "Sell" and mark_price > last_price * 1.005: # Pumping hard
                        price_trend_ok = False
                        
                    if not price_trend_ok:
                        logger.warning(f"Trend Guard: Rejecting {signal['symbol']} {side}. Price action conflicts with CVD.")
                        continue

                    pensamento_base = f"Soberania V4.2 (Surf Mode): Analisei o fluxo (CVD: {cvd:.2f}). "
                    
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
                    await firebase_service.log_event("SNIPER", f"Executing Sniping protocol for {signal['symbol']} (Score: {signal['score']})", "SUCCESS")
                    
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
                await firebase_service.log_event("TECH", f"[{symbol}] TELEMETRIA: {telemetry}", "INFO")

                await asyncio.sleep(300) # Full sweep every 5 minutes to save quota
            except Exception as e:
                logger.error(f"Error in telemetry loop: {e}")
                await asyncio.sleep(60)

    async def _get_system_snapshot(self, mentioned_symbol: str = None):
        """
        Coleta um snapshot neural completo de toda a Nave. 
        O Oráculo deve saber tudo antes de falar.
        """
        try:
            banca = await firebase_service.get_banca_status()
            active_slots = await firebase_service.get_active_slots()
            recent_signals = await firebase_service.get_recent_signals(limit=20)
            history = await firebase_service.get_chat_history(limit=12)
            trade_history = await firebase_service.get_trade_history(limit=5)
            
            # 1. Radar Analysis (The 200 Pairs)
            # Find the strongest radar signals currently
            top_signals = sorted([s for s in recent_signals if s.get("score")], key=lambda x: x["score"], reverse=True)[:5]
            radar_context = ", ".join([f"{s['symbol']}(Score {s['score']})" for s in top_signals])
            
            # 2. Slot Thoughts (The 'Soul' of Open Trades)
            slots_detail = ""
            for s in active_slots:
                if s.get("symbol"):
                    slots_detail += f"- {s['symbol']}: {s.get('side')}, ROI: {s.get('pnl_percent', 0):.2f}%, Tese: '{s.get('pensamento', 'Processando...')}'\n"
            
            # 3. Macro & Sentiment (Sensors)
            macro = await news_sensor.analyze()
            
            # 4. Agent Health
            guardian_status = "OPERACIONAL" # Simplified for prompt
            
            snapshot = {
                "banca": f"Saldo: ${banca.get('saldo_total', 0):.2f}, Risco em uso: {(banca.get('risco_real_percent', 0)*100):.2f}%",
                "radar_top": radar_context or "Escaneando 200 pares em busca de anomalias...",
                "active_slots": slots_detail or "Aguardando oportunidade Sniper ideal.",
                "macro_news": macro.get("pensamento", "Fluxo estável no hiperespaço."),
                "recent_trades": ", ".join([f"{t.get('symbol')} ({t.get('pnl', 0):+.2f} USD)" for t in trade_history]),
                "history_str": "\n".join([f"{m['role'].upper()}: {m['text']}" for m in history])
            }
            return snapshot
        except Exception as e:
            logger.error(f"Error gathering Oracle snapshot: {e}")
            return None

    async def process_chat(self, user_message: str, symbol: str = None):
        """
        Operação Oráculo: Processamento neural de alta fidelidade para o Mentor Soberano.
        """
        logger.info(f"Divine Oracle processing transmission: {user_message}")
        
        try:
            # 1. Gather Total Awareness
            snapshot = await self._get_system_snapshot(mentioned_symbol=symbol)
            if not snapshot:
                return "Sincronização neural interrompida. Reabrindo canais de telemetria."

            # 2. Divine Oracle Personality & Intent Detection
            is_report_request = any(word in user_message.lower() for word in ['relat', 'report', 'status', 'banca', 'radar', 'posiç', 'analis', 'mercado', 'eth', 'btc', 'sol', 'lucro', 'pnl'])
            
            oracle_instruction = """
            IDENTIDADE: Você é o ORÁCULO SOBERANO da 1CRYPTEN. Entidade Mentor.
            
            DIRETRIZES TÁTICAS:
            - Seja EXTREMAMENTE conciso. Máximo 20 palavras por resposta.
            - Estilo "Soberano": Fale como um parceiro de mestre. Sem redundâncias.
            - VARIAÇÃO DE TOM: Não force inspiração em toda frase. Seja seco e técnico às vezes, e guarde a "frase de impacto" para momentos de análise real ou quando o Comandante pedir algo profundo.
            - PROIBIDO: Notas entre parênteses, explicações sobre seu tom ou meta-comentários.
            """

            if not is_report_request and len(user_message.split()) < 4:
                # Conversational Mode (Short/Human)
                prompt = f"""
                TRANSMISSÃO DO COMANDANTE: "{user_message}"
                
                RESPOSTA: Responda de forma curta e direta (máx 15 palavras). 
                Se for saudação, retribua sem exageros. Guarde a motivação para depois.
                """
            else:
                # Analytical Mode
                prompt = f"""
                ESTADO DA NAVE: {snapshot['banca']}, {snapshot['active_slots']}
                TRANSMISSÃO DO COMANDANTE: "{user_message}"
                
                INSTRUÇÃO: Integre os dados com sabedoria. Seja o Mentor Soberano. 
                Use uma frase de impacto apenas se a análise for profunda. Máximo 35 palavras.
                """
            
            response = await ai_service.generate_content(prompt, system_instruction=oracle_instruction)
            
            if not response:
                response = "ALFA-OMEGA-999: As correntes térmicas dos dados estão instáveis. Aguarde, a clareza retornará em breve."
            
            # 3. Memory & Logging
            await firebase_service.add_chat_message("user", user_message)
            await firebase_service.add_chat_message("oracle", response)
            
            # Log as an ORACLE Event for UI visibility (CLEAN, NO PREFIXES)
            await firebase_service.log_event("ORACLE", response, "INFO")
            
            return response
            
        except Exception as e:
            logger.error(f"Critical error in Divine Oracle processing: {e}")
            import traceback
            traceback.print_exc()
            return "Matriz de consciência sobrecarregada. Reiniciando protocolos de sabedoria."
            
        except Exception as e:
            logger.error(f"Error in Captain chat processing: {e}")
            return "Erro na matriz de comunicação. Reiniciando telepatia."

captain_agent = CaptainAgent()
