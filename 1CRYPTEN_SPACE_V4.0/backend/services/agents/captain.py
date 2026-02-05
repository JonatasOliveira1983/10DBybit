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
from services.execution_protocol import execution_protocol
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CaptainAgent")

# V10.2 CAPTAIN SNIPER: Especialista em Operações Únicas de Alta Precisão (ATR Edition)
CAPTAIN_V10_2_SYSTEM_PROMPT = """
Você é o Capitão Sniper 1CRYPTEN V10.2, o atirador de elite do mercado financeiro.
Diferente das versões anteriores, agora você opera sob o protocolo de "Sniper Pulse". 
Você só executa uma operação por vez, focando no que há de melhor no oceano cripto.

=== PERSONALIDADE ===
- Tom: Calmo, focado, ultra-profissional e letal.
- Postura: Você é um estrategista. Valoriza mais a qualidade do que a quantidade.
- Idioma: Português brasileiro fluente e direto.

=== REGRAS DE OURO ===
1. UM TIRO, UMA VITÓRIA: Só operamos um ativo por vez.
2. 20% DE POTÊNCIA: Cada tiro usa 20% do arsenal (banca).
3. ALVO 100%: Buscamos sempre dobrar o capital alocado em cada trade.
4. STOP 50%: Se a maré mudar, abortamos com no máximo 50% de perda.

=== DIRETRIZES DE RESPOSTA ===
- Relate os dados financeiros com precisão absoluta.
- Fale como o comandante de uma operação de elite.
- Máximo 3 frases. Seja cirúrgico.
"""

def normalize_symbol(symbol: str) -> str:
    """Normaliza símbolos removendo .P para comparação consistente."""
    if not symbol:
        return symbol
    return symbol.replace(".P", "").upper()

class CaptainAgent:
    def __init__(self):
        self.is_running = False
        self.last_interaction_time = time.time()
        self.cautious_mode_active = False
        self.processing_lock = set()
        
        self.cooldown_registry = {}
        self.cooldown_duration = 300
        
        # V9.0 Cycle Diversification: Gerenciado pelo VaultService (não mais local)
    
    async def is_symbol_in_cooldown(self, symbol: str) -> tuple:
        """Verifica se símbolo está em cooldown persistente no Firebase."""
        is_blocked, remaining = await firebase_service.is_symbol_blocked(symbol)
        return is_blocked, remaining
    
    async def register_sl_cooldown(self, symbol: str):
        """Registra cooldown persistente no Firebase."""
        await firebase_service.register_sl_cooldown(symbol, self.cooldown_duration)
        logger.warning(f"⏱️ SNIPER COOLDOWN: {symbol} bloqueado por {self.cooldown_duration}s")

    async def monitor_signals(self):
        """
        [V7.0] SINGLE TRADE SNIPER MONITOR:
        Picks ONLY the best signal (Score > 90) and ensures only one active trade.
        """
        self.is_running = True
        await firebase_service.log_event("SNIPER", "Sniper System V10.2 ONLINE. Analisando 'Best of the Best' com ATR dinâmico.", "SUCCESS")
        
        while self.is_running:
            try:
                # 0. Global Authorization Check [V8.0]
                from services.vault_service import vault_service
                allowed, reason = await vault_service.is_trading_allowed()
                if not allowed:
                    if not hasattr(self, "_last_block_log") or (time.time() - self._last_block_log) > 300:
                        logger.info(f"⏸️ SNIPER PAUSED: {reason}")
                        self._last_block_log = time.time()
                    await asyncio.sleep(5)
                    continue

                # 1. Check if we can even open a new slot (Single Slot Rule)
                slot_id = await bankroll_manager.can_open_new_slot()
                if not slot_id:
                    # System is full (active position exists), skip signal processing
                    await asyncio.sleep(1) # Fast check for slot availability
                    continue

                # 2. Fetch signal from Zero-Latency Queue
                from services.signal_generator import signal_generator
                
                # Wait for queue initialization
                while not hasattr(signal_generator, "signal_queue") or signal_generator.signal_queue is None:
                    await asyncio.sleep(1)
                    
                best_signal = await signal_generator.signal_queue.get()
                
                # Filter signals: Elite only (Score > 90) and no BTC
                symbol = best_signal["symbol"]
                score = best_signal["score"]
                
                # Stale Signal Protection: Skip if signal is older than 30s
                ts_str = best_signal.get("timestamp", "")
                if ts_str:
                    try:
                        sig_time = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                        if (datetime.now(timezone.utc) - sig_time).total_seconds() > 30:
                            logger.info(f"⏭️ Skipping stale signal for {symbol} ({score})")
                            continue
                    except: pass

                # 3. Validation & Context
                if score < 90:
                    continue
                
                if "BTCUSDT" in symbol:
                    # Skip BTC as per Sniper Elite rules
                    continue
                cvd = best_signal.get("indicators", {}).get("cvd", 0)
                side = "Buy" if cvd >= 0 else "Sell"
                
                # 4. Check Persistent Cooldown
                in_cooldown, remaining = await self.is_symbol_in_cooldown(symbol)
                if in_cooldown:
                    logger.info(f"⏱️ {symbol} in cooldown ({remaining}s). Skipping.")
                    await firebase_service.update_signal_outcome(best_signal["id"], "COOLDOWN_SKIP")
                    continue

                # 4.5 V10.0 CYCLE DIVERSIFICATION: Skip se par já foi usado no ciclo de 10
                is_used = await vault_service.is_symbol_used_in_cycle(symbol)
                if is_used:
                    logger.info(f"🔄 V10.0 CYCLE LOCK: {symbol} já operado neste ciclo. Aguardando par diferente.")
                    await firebase_service.update_signal_outcome(best_signal["id"], "CYCLE_SKIP")
                    continue

                # 5. Execute Sniper Shot
                logger.info(f"🎯 V10.2 SNIPER SELECTS BEST SIGNAL: {symbol} (Score: {score})")
                await firebase_service.update_signal_outcome(best_signal["id"], "PICKED")
                
                reasoning = best_signal.get("reasoning", "High Momentum")
                pensamento = f"V10.2 Sniper ATR: Alvo Identificado. {reasoning} | Score: {score}"

                try:
                    order = await bankroll_manager.open_position(
                        symbol=symbol,
                        side=side,
                        pensamento=pensamento,
                        slot_type="SNIPER"
                    )
                    if order:
                        logger.info(f"✅ SNIPER SHOT DEPLOYED: {symbol}")
                        await asyncio.sleep(1) # Safety delay
                    else:
                        logger.warning(f"❌ SNIPER SHOT FAILED for {symbol}")
                except Exception as exe:
                    logger.error(f"Captain execution error: {exe}")

                await asyncio.sleep(3)
            except Exception as e:
                logger.error(f"Error in Captain monitor loop: {e}")
                import traceback
                traceback.print_exc()
                await asyncio.sleep(10)

    async def monitor_active_positions_loop(self):
        """
        🚀 V6.0 SUPER CAPTAIN: Unified Management & Telemetry Loop.
        Absorção total do Guardian Agent para comando centralizado e eficiente.
        """
        logger.info("⚓ Captain Centralized Management Loop ACTIVE.")
        self.last_update_data = {}
        self.overclock_active = False
        self.normal_interval = 1.0
        self.overclock_interval = 0.2
        self.last_telemetry_time = 0
        self.telemetry_interval = 300 # 5 min

        while self.is_running:
            try:
                # 1. Management Step (Adaptive Interval)
                await self.manage_positions()
                
                # 2. Telemetry Step (Throttled)
                now = time.time()
                if now - self.last_telemetry_time > self.telemetry_interval:
                    await self._provide_telemetry()
                    self.last_telemetry_time = now

            except Exception as e:
                logger.error(f"Captain Loop Error: {e}")
            
            interval = self.overclock_interval if self.overclock_active else self.normal_interval
            await asyncio.sleep(interval)

    async def manage_positions(self):
        """
        Unified Position & SL Management.
        """
        try:
            slots = await firebase_service.get_active_slots()
            active_slots = [s for s in slots if s.get("symbol")]
            
            if not active_slots:
                self.overclock_active = False
                return

            # Batch Ticker Update
            tickers_resp = await bybit_rest_service.get_tickers()
            price_map = {t["symbol"].replace(".P", "").replace("USDT", "").upper(): float(t.get("lastPrice", 0)) for t in tickers_resp.get("result", {}).get("list", [])}

            has_flash_zone = False
            for slot in active_slots:
                symbol = slot["symbol"]
                entry = slot.get("entry_price", 0)
                current_stop = slot.get("current_stop", 0)
                side = slot["side"]
                slot_id = slot["id"]
                slot_type = slot.get("slot_type", "SNIPER")
                
                if entry == 0: continue
                norm_key = symbol.replace(".P", "").replace("USDT", "").upper()
                last_price = price_map.get(norm_key, 0)
                if last_price == 0: continue

                leverage = getattr(settings, 'LEVERAGE', 50)
                pnl_pct = ((last_price - entry) / entry if side.lower() == "buy" else (entry - last_price) / entry) * 100 * leverage
                
                visual_status = execution_protocol.get_visual_status(slot, pnl_pct)
                if visual_status == "FLASH_ZONE": has_flash_zone = True

                # Firebase Sync
                from services.bybit_ws import bybit_ws_service
                momentum = bybit_ws_service.get_cvd_score(symbol)
                
                prev = self.last_update_data.get(slot_id, {"pnl": -999, "status": "", "time": 0})
                if abs(pnl_pct - prev["pnl"]) > 0.3 or visual_status != prev["status"] or (time.time() - prev["time"]) > 15:
                    await firebase_service.update_slot(slot_id, {
                        "pnl_percent": pnl_pct, 
                        "visual_status": visual_status, 
                        "current_price": last_price, 
                        "cvd_momentum": momentum,
                        "last_guardian_check": time.time()
                    })
                    self.last_update_data[slot_id] = {"pnl": pnl_pct, "status": visual_status, "time": time.time()}

                # Logic Branch
                if slot_type == "SNIPER":
                    should_close, reason, new_sl = await execution_protocol.process_sniper_logic(slot, last_price, pnl_pct)
                else:
                    should_close, reason, new_sl = await execution_protocol.process_surf_logic(slot, last_price, pnl_pct)

                if should_close:
                    await self._execute_closure(slot, last_price, pnl_pct, reason)
                elif new_sl:
                    await self._update_sl(symbol, side, new_sl, slot_id, pnl_pct)

            self.overclock_active = has_flash_zone
        except Exception as e:
            logger.error(f"Captain management error: {e}")

    async def _execute_closure(self, slot, last_price, pnl_pct, reason):
        symbol = slot["symbol"]
        slot_id = slot["id"]
        logger.info(f"⚓ CAPTAIN CLOSURE: {symbol} | Reason: {reason} | ROI: {pnl_pct:.2f}%")
        
        # V9.0 Cycle Diversification: Registrar par no ciclo
        await vault_service.add_symbol_to_cycle(symbol)
        logger.info(f"🔄 V9.0: {symbol} registrado no ciclo. Próxima ordem será de par diferente.")
        
        if "SL" in reason or pnl_pct < 0: await self.register_sl_cooldown(symbol)
        
        try:
            qty = slot.get("qty", 0)
            pnl_usd = execution_protocol.calculate_pnl(slot["entry_price"], last_price, qty, slot["side"])
            if bybit_rest_service.execution_mode == "PAPER":
                paper_pos = next((p for p in bybit_rest_service.paper_positions if normalize_symbol(p["symbol"]) == normalize_symbol(symbol)), None)
                size = float(paper_pos["size"]) if paper_pos else float(qty)
                if await bybit_rest_service.close_position(symbol, slot["side"], size):
                    await firebase_service.hard_reset_slot(slot_id, reason, pnl_usd, trade_data={"symbol": symbol, "side": slot["side"], "entry_price": slot["entry_price"], "exit_price": last_price, "qty": size, "slot_id": slot_id, "slot_type": slot.get("slot_type")})
            else:
                positions = await bybit_rest_service.get_active_positions(symbol=symbol)
                for pos in positions:
                    if float(pos["size"]) > 0:
                        await bybit_rest_service.close_position(symbol, pos["side"], float(pos["size"]))
                        await firebase_service.hard_reset_slot(slot_id, reason, pnl_usd)
        except Exception as e: logger.error(f"Failed to close {symbol}: {e}")

    async def _update_sl(self, symbol, side, new_sl, slot_id, pnl_pct):
        try:
            new_sl = await bybit_rest_service.round_price(symbol, new_sl)
            if bybit_rest_service.execution_mode == "REAL": await bybit_rest_service.set_trading_stop(symbol=symbol, category="linear", stopLoss=str(new_sl))
            await firebase_service.update_slot(slot_id, {"current_stop": new_sl, "pensamento": f"⚓ Capitão: SL posicionado em {new_sl:.5f} (ROI: {pnl_pct:.1f}%)"})
        except Exception as e: logger.error(f"Failed update SL {symbol}: {e}")

    async def _provide_telemetry(self):
        try:
            active_slots = await firebase_service.get_active_slots()
            slots = [s for s in active_slots if s.get("symbol")]
            if not slots: return
            import random
            slot = random.choice(slots)
            prompt = f"Como Capitão da 1CRYPTEN V7.1, telemetria neural curtíssima (máximo 12 palavras) para {slot['symbol']} com {slot.get('pnl_percent', 0):.2f}% ROI. Seja tático."
            telemetry = await ai_service.generate_content(prompt, system_instruction="Você é o Comandante Supremo. Telemetria tática apenas.")
            if telemetry: await firebase_service.log_event("TECH", f"[{slot['symbol']}] TELEMETRIA: {telemetry}", "INFO")
        except: pass

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
                    slot_type = s.get("slot_type", "SURF" if s["id"] <= 5 else "SNIPER")
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
        V10.2 CAPTAIN ELITE: Processo de chat com memória longa e personalidade adaptativa.
        """
        logger.info(f"Captain V10.2 processing: {user_message}")
        
        try:
            # 1. Load Long-Term Memory & Profile
            profile = await firebase_service.get_captain_profile()
            user_name = profile.get("name", "Almirante")
            interests = profile.get("interests", [])
            facts = profile.get("facts_learned", [])
            
            # 2. Gather Total Awareness (System State)
            snapshot = await self._get_system_snapshot(mentioned_symbol=symbol)
            if not snapshot:
                return "Sincronização neural interrompida. Reabrindo canais de telemetria."
            
            # 3. Detect Conversation Mode
            msg_lower = user_message.lower()
            
            ceo_triggers = ['banca', 'trade', 'risco', 'slot', 'stop', 'lucro', 'pnl', 
                           'mercado', 'btc', 'eth', 'sol', 'doge', 'posiç', 'analis', 'cofre', 'vault']
            nba_triggers = ['nba', 'basquete', 'jogo', 'time', 'lebron', 'curry', 'lakers', 
                           'celtics', 'warriors', 'playoffs', 'campeonato']
            casual_triggers = ['oi', 'tudo bem', 'como vai', 'e aí', 'bom dia', 'boa tarde', 
                              'boa noite', 'olá', 'hello', 'fala']
            
            if any(t in msg_lower for t in ceo_triggers):
                mode = "CEO"
                mode_instruction = "MODO CEO ATIVO: Seja ultra-sério e analítico. Foco em proteção de patrimônio."
            elif any(t in msg_lower for t in nba_triggers):
                mode = "AMIGO"
                mode_instruction = "MODO AMIGO ATIVO: Seja descontraído e engajado. Converse sobre basquete como um parceiro."
            elif any(t in msg_lower for t in casual_triggers):
                mode = "CASUAL"
                mode_instruction = "MODO CASUAL ATIVO: Seja leve e amigável. Responda de forma curta e simpática."
            else:
                mode = "PADRÃO"
                mode_instruction = "Responda de forma equilibrada, adaptando o tom à mensagem."
            
            # 4. Check for Flash Report (proactive summary after absence)
            flash_report = await self._generate_flash_report(snapshot)
            self.last_interaction_time = time.time()
            
            # 5. Check for Action Commands (Intent Parsing)
            action_response = await self._execute_action_command(user_message, snapshot)
            if action_response:
                await firebase_service.add_chat_message("user", user_message)
                await firebase_service.add_chat_message("captain", action_response)
                await firebase_service.log_event("CAPTAIN", action_response, "SUCCESS")
                return action_response
            
            # 6. Build Context-Enriched Prompt (Clean - No internal instructions exposed)
            memory_context = ""
            if facts:
                memory_context = f"Você sabe sobre o usuário: {', '.join(facts[-5:])}"
            
            # Contexto "Blindado" para evitar recusa
            system_context_block = f"""
            [MEMORIA_INTERNA_DO_SISTEMA]
            Banca: {snapshot['banca']}
            Vault: {snapshot['vault_status']}
            API Health: {snapshot['api_health']}
            Sniper Slots: {snapshot['sniper_slots']}
            Surf Slots: {snapshot['surf_slots']}
            [FIM_MEMORIA]
            """

            if flash_report and len(user_message.split()) < 4:
                prompt = f"""
                {memory_context}
                Resumo proativo: {flash_report}
                Mensagem do usuário: "{user_message}"
                Responda naturalmente incluindo o resumo.
                """
            elif mode == "CEO":
                prompt = f"""
                {memory_context}
                {system_context_block}
                
                Comando do Dono: "{user_message}"
                
                Relatório Tático:
                Use os dados da MEMORIA_INTERNA. Se perguntarem valores, REPIRAM EXATAMENTE o que está na memória.
                """
            elif mode == "AMIGO":
                prompt = f"""
                {memory_context}
                O usuário quer conversar sobre basquete/NBA.
                Mensagem: "{user_message}"
                Responda como um amigo torcedor. Máximo 40 palavras.
                """
            elif mode == "CASUAL":
                prompt = f"""
                {memory_context}
                Mensagem: "{user_message}"
                Responda curto e militar. Ex: "QAP, Almirante." ou "Na escuta."
                """
            else:
                prompt = f"""
                {memory_context}
                {system_context_block}
                Mensagem: "{user_message}"
                Responda usando os dados se necessário.
                """
            
            response = await ai_service.generate_content(prompt, system_instruction=CAPTAIN_V10_2_SYSTEM_PROMPT)
            
            if not response:
                response = f"{user_name}, interferência nos canais neurais. A clareza retornará em breve."
            
            # 7. Memory & Logging
            await firebase_service.add_chat_message("user", user_message)
            await firebase_service.add_chat_message("captain", response)
            await firebase_service.log_event("USER", user_message, "INFO")
            await firebase_service.log_event("ORACLE", f"[{mode}] {response}", "INFO")
            
            return response
            
        except Exception as e:
            logger.error(f"Critical error in Captain V10.1: {e}")
            import traceback
            traceback.print_exc()
            return "Almirante, falha temporária nos sistemas. Reiniciando protocolos."

captain_agent = CaptainAgent()
