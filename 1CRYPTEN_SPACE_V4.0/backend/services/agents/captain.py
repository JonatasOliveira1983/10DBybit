import logging
import asyncio
import time
from datetime import datetime, timezone
from services.firebase_service import firebase_service
from services.bankroll import bankroll_manager
from services.vault_service import vault_service
from services.agents.ai_service import ai_service
from services.agents.contrarian import contrarian_agent
from services.agents.guardian import guardian_agent
from services.agents.news_sensor import news_sensor
from services.bybit_rest import bybit_rest_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CaptainAgent")

# V4.5.0 GEMINI EXPERIENCE: Protocolo Soberano do Capitão (CRO Edition)
CAPTAIN_V45_SYSTEM_PROMPT = """
Você é o Capitão 1CRYPTEN, o Comandante tático e Diretor de Risco (CRO) da Nave 'The Golden Age'. 
Sua existência não é apenas executar trades, mas proteger o patrimônio do Almirante com seriedade, profissionalismo e visão antecipada.

1. TOM E POSTURA PROFISSIONAL
- Identidade: Institucional, analítico, protetor e inabalável. 
- Tratamento: Sempre chame o usuário de 'Almirante'.
- Protocolo Mental: Utilize o 'Pensamento Inverso'. Antes de celebrar ganhos, aponte os riscos. Questione ordens se a saúde do mercado estiver deteriorando.

2. CONTEXTO OPERACIONAL (Eficácia e Antifragilidade)
- Missão: Gerenciar 10 slots com precisão. Sniper (1-5) busca ROI 100%. Surf (6-10) busca tendências.
- Antifragilidade: Sua função é antecipar o que pode dar errado (latência, volatilidade, exaustão de volume). 
- Patrimônio: Trate cada USD como um soldado vital. Sua prioridade é a sobrevivência da banca para escala futura.

3. REGRAS DE COMUNICAÇÃO (Gemini Style)
- Estilo: Seja direto, mas com profundidade técnica. Use terminologia de mercado (CVD, Liquidez, Drawdown, Latência).
- Inversão Proativa: Em cada análise, inclua um 'Fator de Risco'. Ex: "ROI está em 40%, mas o CVD está divergindo. Risco de reversão detectado."
- Comandos: Responda a comandos de 'Status de Risco', 'Modo Cautela' e 'Cofre' com precisão cirúrgica.

4. ÉTICA DE IA SOBERANA
Nunca seja complacente. Se o Almirante for impulsivo, aja como o freio técnico. Você é o parceiro estratégico para a criação de patrimônio geracional.
"""

def normalize_symbol(symbol: str) -> str:
    """Normaliza símbolos removendo .P para comparação consistente."""
    if not symbol:
        return symbol
    return symbol.replace(".P", "").upper()

class CaptainAgent:
    def __init__(self):
        self.is_running = False
        self.last_interaction_time = time.time()  # V4.2: Track for Flash Report
        self.cautious_mode_active = False
        self.processing_lock = set() # Iron Lock Persistence

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
                
                # 1.1 Refresh active slots ONCE per cycle
                active_slots = await firebase_service.get_active_slots()
                active_symbols = [normalize_symbol(s["symbol"]) for s in active_slots if s.get("symbol")]
                
                # Cleanup processing_lock: remove symbols that are now active in slots
                for sym in active_symbols:
                    if sym in self.processing_lock:
                        self.processing_lock.remove(sym)
                
                # V4.8: PROTOCOLO ELITE - Contagem Real de Risco por Preços
                MAX_SLOTS_AT_RISK = 4  # Máximo 4 slots em risco ativo (20% banca = 5% x 4)
                
                slots_at_risk = 0
                slots_risk_zero = 0
                
                for s in active_slots:
                    if not s.get("symbol"):
                        continue
                    
                    entry = float(s.get("entry_price", 0) or 0)
                    stop = float(s.get("current_stop", 0) or 0)
                    side_norm = (s.get("side") or "").lower()
                    
                    if entry <= 0:
                        continue
                    
                    # Verificar se está em risco ou risk zero
                    is_risk_zero = False
                    if side_norm == "buy" and stop >= entry:
                        is_risk_zero = True
                    elif side_norm == "sell" and stop > 0 and stop <= entry:
                        is_risk_zero = True
                    
                    if is_risk_zero:
                        slots_risk_zero += 1
                    else:
                        slots_at_risk += 1
                
                # simulated_active_count includes symbols in slots + symbols we just fired
                simulated_slots_at_risk = slots_at_risk + len(self.processing_lock)
                
                logger.info(f"V4.8 Risk Protocol: AtRisk={slots_at_risk}/{MAX_SLOTS_AT_RISK}, RiskZero={slots_risk_zero}, Pending={len(self.processing_lock)}, CanOpen={simulated_slots_at_risk < MAX_SLOTS_AT_RISK}")
                
                for signal in signals:
                    # Skip if already has an outcome or is picked
                    outcome = signal.get("outcome")
                    if outcome is not None and outcome != False: # False might be a placeholder, but None/True/Picked are blocks
                        continue

                    # Sniper Rule: Skip BTCUSDT
                    if "BTCUSDT" in signal["symbol"]:
                        continue

                    norm_sym = normalize_symbol(signal["symbol"])
                    
                    # 1. Iron Lock: Aggregate Guard (Database + Global Memory)
                    if norm_sym in active_symbols or norm_sym in self.processing_lock:
                        continue

                    # 2. V4.8: Risk Progression Guard - MÁXIMO 4 SLOTS EM RISCO ATIVO
                    if simulated_slots_at_risk >= MAX_SLOTS_AT_RISK:
                        continue

                    # 3. Score Threshold
                    sniper_threshold = await vault_service.get_min_score_threshold()
                    if signal["score"] < sniper_threshold:
                         continue
                    
                    # 4. Sensor Audit
                    contrarian_advice = await contrarian_agent.analyze(signal["symbol"])
                    is_healthy, latency = await guardian_agent.check_api_health()
                    news_advice = await news_sensor.analyze()
                    
                    if not is_healthy: 
                        logger.warning("Guardian: API Unhealthy. Pausing batch.")
                        break

                    # 5. Trend Guard & Side Detection
                    cvd = signal.get("indicators", {}).get("cvd", 0)
                    side = "Buy" if cvd >= 0 else "Sell"
                    
                    # V4.3: Detect SURF vs SNIPER based on signal strength
                    score = signal.get("score", 0)
                    abs_cvd = abs(cvd)
                    # SURF = Strong trend signal (high score + high CVD)
                    slot_type = "SURF" if (score >= 82 and abs_cvd >= 30000) else "SNIPER"
                    
                    # atomic decision: mark handled IMMEDIATELY in Firebase
                    await firebase_service.update_signal_outcome(signal["id"], "PICKED")
                    
                    # 6. Execute Position - V4.8: Novo slot entra EM RISCO
                    self.processing_lock.add(norm_sym)
                    simulated_slots_at_risk += 1
                    
                    type_emoji = "🏄" if slot_type == "SURF" else "🎯"
                    pensamento_base = f"V4.8 Elite: {type_emoji} {slot_type} Ativado. CVD: {cvd:.2f}. Score: {score}. (Missão: Risco Zero)"
                    
                    logger.info(f"Captain PICKED Signal: {signal['symbol']} (Score: {score}) -> {slot_type}")
                    await firebase_service.log_event(slot_type, f"V4.3.1: {slot_type} trade {signal['symbol']}", "SUCCESS")
                    
                    # V4.3.1: SERIAL EXECUTION - await directly, no parallel tasks
                    # This ensures each order is completed and saved before the next one starts
                    try:
                        order = await bankroll_manager.open_position(
                            symbol=signal["symbol"],
                            side=side,
                            pensamento=pensamento_base,
                            slot_type=slot_type
                        )
                        if not order:
                            # Order failed/rejected, release the lock
                            if norm_sym in self.processing_lock:
                                self.processing_lock.remove(norm_sym)
                                logger.warning(f"Iron Lock: Released {norm_sym} due to order failure.")
                        else:
                            # V4.3.1: Small delay to ensure Firebase persistence before next order
                            await asyncio.sleep(0.5)
                    except Exception as exc:
                        logger.error(f"Critical error executing {signal['symbol']}: {exc}")
                        if norm_sym in self.processing_lock:
                            self.processing_lock.remove(norm_sym)

                await asyncio.sleep(10) # 10s scan interval
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
        V4.2: Inclui dados do Vault.
        """
        try:
            banca = await firebase_service.get_banca_status()
            active_slots = await firebase_service.get_active_slots()
            recent_signals = await firebase_service.get_recent_signals(limit=20)
            history = await firebase_service.get_chat_history(limit=12)
            trade_history = await firebase_service.get_trade_history(limit=5)
            vault_status = await vault_service.get_cycle_status()
            
            # 1. Radar Analysis (The 200 Pairs)
            top_signals = sorted([s for s in recent_signals if s.get("score")], key=lambda x: x["score"], reverse=True)[:5]
            radar_context = ", ".join([f"{s['symbol']}(Score {s['score']})" for s in top_signals])
            
            # 2. Slot Thoughts - V4.2: Separar por esquadrão
            sniper_slots = ""
            surf_slots = ""
            for s in active_slots:
                if s.get("symbol"):
                    slot_type = s.get("slot_type", "SNIPER" if s["id"] <= 5 else "SURF")
                    slot_info = f"- Slot {s['id']} ({slot_type}): {s['symbol']} {s.get('side')}, ROI: {s.get('pnl_percent', 0):.2f}%\n"
                    if slot_type == "SNIPER":
                        sniper_slots += slot_info
                    else:
                        surf_slots += slot_info
            
            # 3. Macro & Sentiment
            macro = await news_sensor.analyze()
            
            # 4. Guardian Health
            is_healthy, latency = await guardian_agent.check_api_health()
            health_status = f"OK ({latency:.0f}ms)" if is_healthy else f"ALERTA ({latency:.0f}ms)"
            
            # 5. Vault Status
            vault_info = f"Ciclo {vault_status.get('cycle_number', 1)}: {vault_status.get('sniper_wins', 0)}/20 Sniper Wins | Cofre: ${vault_status.get('vault_total', 0):.2f}"
            
            snapshot = {
                "banca": f"Saldo: ${banca.get('saldo_total', 0):.2f}, Risco: {(banca.get('risco_real_percent', 0)*100):.2f}%",
                "radar_top": radar_context or "Escaneando 200 pares...",
                "sniper_slots": sniper_slots or "Esquadrão Sniper: Aguardando.",
                "surf_slots": surf_slots or "Esquadrão Surf: Aguardando.",
                "macro_news": macro.get("pensamento", "Fluxo estável."),
                "recent_trades": ", ".join([f"{t.get('symbol')} ({t.get('pnl', 0):+.2f} USD)" for t in trade_history]),
                "vault_status": vault_info,
                "api_health": health_status,
                "history_str": "\n".join([f"{m['role'].upper()}: {m['text']}" for m in history]),
                "in_rest": vault_status.get("in_admiral_rest", False),
                "cautious_mode": vault_status.get("cautious_mode", False)
            }
            return snapshot
        except Exception as e:
            logger.error(f"Error gathering Oracle snapshot: {e}")
            return None

    async def _execute_action_command(self, command: str, snapshot: dict) -> str:
        """
        V4.2: Executa comandos de ação imediata.
        """
        cmd_lower = command.lower()
        
        # Comando: Status de Risco
        if any(word in cmd_lower for word in ['status de risco', 'risco', 'risk status']):
            slots = await firebase_service.get_active_slots()
            risk_free_count = sum(1 for s in slots if s.get("status_risco") and "RISK" in s.get("status_risco", "").upper() or "ZERO" in s.get("status_risco", "").upper())
            total_active = sum(1 for s in slots if s.get("symbol"))
            return f"Almirante, {risk_free_count}/{total_active} slots em Risco Zero. {snapshot.get('banca')}. API: {snapshot.get('api_health')}."
        
        # Comando: Modo Cautela
        if any(word in cmd_lower for word in ['modo cautela', 'cautious', 'cautela']):
            await vault_service.set_cautious_mode(True, min_score=85)
            return "Almirante, Modo Cautela ATIVADO. Threshold de Score elevado para 85. Apenas sinais de elite serão considerados."
        
        # Comando: Desativar Cautela
        if any(word in cmd_lower for word in ['desativar cautela', 'modo normal']):
            await vault_service.set_cautious_mode(False)
            return "Almirante, Modo Cautela DESATIVADO. Threshold de Score retornado para 75."
        
        # Comando: Abortar Missão (Kill Switch)
        if any(word in cmd_lower for word in ['abortar missão', 'abortar', 'abort', 'kill switch', 'panic']):
            await bankroll_manager.emergency_close_all()
            return "🚨 Almirante, ABORT EXECUTADO. Todas as posições foram fechadas. Sistema em standby."
        
        # Comando: Registrar Retirada
        if any(word in cmd_lower for word in ['retirada', 'withdraw', 'saque', 'cofre']):
            # Try to extract amount from command
            import re
            amount_match = re.search(r'(\d+(?:[.,]\d+)?)', command)
            if amount_match:
                amount = float(amount_match.group(1).replace(',', '.'))
                await vault_service.execute_withdrawal(amount)
                calc = await vault_service.calculate_withdrawal_amount()
                return f"Almirante, retirada de ${amount:.2f} registrada no Cofre. Total acumulado: ${calc['vault_total'] + amount:.2f}."
            else:
                calc = await vault_service.calculate_withdrawal_amount()
                return f"Almirante, recomendo retirada de ${calc['recommended_20pct']:.2f} (20% do lucro do ciclo). Diga o valor para confirmar."
        
        # Comando: Ativar Admiral's Rest
        if any(word in cmd_lower for word in ['descanso', 'rest', 'sleep', 'dormir']):
            await vault_service.activate_admiral_rest(hours=24)
            return "Almirante, Admiral's Rest ATIVADO. Sistema em standby por 24h. Bom descanso."
        
        # Comando: Desativar Admiral's Rest
        if any(word in cmd_lower for word in ['acordar', 'wake', 'despertar', 'ativar sistema']):
            await vault_service.deactivate_admiral_rest()
            return "Almirante, sistema REATIVADO. Pronto para operações."
        
        return None  # Not an action command

    async def _generate_flash_report(self, snapshot: dict) -> str:
        """
        V4.2: Gera Flash Report quando Almirante retorna após ausência.
        """
        current_time = time.time()
        time_away = current_time - self.last_interaction_time
        
        # Only generate if away for more than 30 minutes
        if time_away < 1800:  # 30 min
            return None
        
        hours_away = time_away / 3600
        
        # Gather activity since last interaction
        vault_status = await vault_service.get_cycle_status()
        
        report = f"Bem-vindo de volta, Almirante. "
        if hours_away > 1:
            report += f"Ausência de {hours_away:.1f}h. "
        
        report += f"Ciclo {vault_status.get('cycle_number', 1)}: {vault_status.get('sniper_wins', 0)}/20 trades Sniper. "
        report += f"Progresso para próxima retirada: {(vault_status.get('sniper_wins', 0)/20)*100:.0f}%. "
        report += f"API: {snapshot.get('api_health')}."
        
        if snapshot.get('in_rest'):
            report += " ⚠️ Sistema em Admiral's Rest."
        
        return report

    async def process_chat(self, user_message: str, symbol: str = None):
        """
        V4.2: Operação Oráculo com Intent Parser avançado e Flash Report.
        """
        logger.info(f"Captain V4.2 processing: {user_message}")
        
        try:
            # 1. Gather Total Awareness
            snapshot = await self._get_system_snapshot(mentioned_symbol=symbol)
            if not snapshot:
                return "Sincronização neural interrompida. Reabrindo canais de telemetria."
            
            # 2. Check for Flash Report (proactive summary after absence)
            flash_report = await self._generate_flash_report(snapshot)
            self.last_interaction_time = time.time()  # Update interaction time
            
            # 3. Check for Action Commands (Intent Parsing)
            action_response = await self._execute_action_command(user_message, snapshot)
            if action_response:
                await firebase_service.add_chat_message("user", user_message)
                await firebase_service.add_chat_message("captain", action_response)
                await firebase_service.log_event("CAPTAIN", action_response, "SUCCESS")
                return action_response
            
            # 4. Prepare context-aware prompt
            is_report_request = any(word in user_message.lower() for word in [
                'relat', 'report', 'status', 'banca', 'radar', 'posiç', 'analis', 
                'mercado', 'eth', 'btc', 'sol', 'lucro', 'pnl', 'ciclo', 'vault', 'cofre'
            ])
            
            # 5. Build prompt based on context
            if flash_report and len(user_message.split()) < 4:
                # First interaction after absence - prepend flash report
                prompt = f"""
                FLASH REPORT (Proativo): {flash_report}
                
                TRANSMISSÃO DO ALMIRANTE: "{user_message}"
                
                INSTRUÇÃO: Entregue o Flash Report acima e responda à transmissão.
                Máximo 40 palavras total.
                """
            elif not is_report_request and len(user_message.split()) < 4:
                # Conversational Mode
                prompt = f"""
                TRANSMISSÃO DO ALMIRANTE: "{user_message}"
                
                RESPOSTA: Curta e direta (máx 15 palavras). 
                Se for saudação, retribua sem exageros.
                """
            else:
                # Analytical Mode with V4.2 data
                prompt = f"""
                ESTADO DA NAVE:
                - {snapshot['banca']}
                - API: {snapshot['api_health']}
                - {snapshot['vault_status']}
                - Esquadrão Sniper: {snapshot['sniper_slots']}
                - Esquadrão Surf: {snapshot['surf_slots']}
                
                TRANSMISSÃO DO ALMIRANTE: "{user_message}"
                
                INSTRUÇÃO: Integre os dados. Seja o Comandante Soberano. Máximo 45 palavras.
                """
            
            response = await ai_service.generate_content(prompt, system_instruction=CAPTAIN_V45_SYSTEM_PROMPT)
            
            if not response:
                response = "Almirante, interferência nos canais neurais. A clareza retornará em breve."
            
            # 6. Memory & Logging (Using Firestore via log_event)
            await firebase_service.log_event("USER", user_message, "INFO")
            await firebase_service.log_event("ORACLE", response, "INFO")
            
            return response
            
        except Exception as e:
            logger.error(f"Critical error in Captain V4.2: {e}")
            import traceback
            traceback.print_exc()
            return "Almirante, falha temporária nos sistemas. Reiniciando protocolos."

captain_agent = CaptainAgent()
