"""
Vault Management Service V9.0
Gerencia o ciclo de 10 trades Sniper com diversificação obrigatória e compound automático.
"""
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from services.firebase_service import firebase_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VaultService")


class VaultService:
    def __init__(self):
        self.cycle_doc_path = "vault_management/current_cycle"
        
    async def get_cycle_status(self) -> dict:
        """
        Retorna o status atual do ciclo de 10 trades Sniper.
        Returns: {sniper_wins, cycle_number, cycle_profit, in_admiral_rest, rest_until}
        """
        try:
            if not firebase_service.is_active or not firebase_service.db:
                return self._default_cycle()
            
            def _get():
                doc = firebase_service.db.collection("vault_management").document("current_cycle").get()
                return doc.to_dict() if doc.exists else None
            
            data = await asyncio.to_thread(_get)
            if not data:
                # Initialize if not exists
                await self.initialize_cycle()
                return self._default_cycle()
            
            # Check if rest period has ended
            if data.get("in_admiral_rest") and data.get("rest_until"):
                rest_until = data["rest_until"]
                if hasattr(rest_until, 'timestamp'):
                    rest_until = datetime.fromtimestamp(rest_until.timestamp(), tz=timezone.utc)
                if datetime.now(timezone.utc) > rest_until:
                    # Auto-exit rest mode
                    await self.deactivate_admiral_rest()
                    data["in_admiral_rest"] = False
                    
            return data
            
        except Exception as e:
            logger.error(f"Error getting cycle status: {e}")
            return self._default_cycle()
    
    def _default_cycle(self) -> dict:
        return {
            "sniper_wins": 0,
            "cycle_number": 1,
            "cycle_profit": 0.0,      # Lucro líquido Sniper (Wins - Losses)
            "cycle_losses": 0.0,      # Apenas perdas acumuladas Sniper
            "started_at": datetime.now(timezone.utc).isoformat(),
            "in_admiral_rest": False,
            "rest_until": None,
            "vault_total": 0.0,
            "cautious_mode": False,
            "min_score_threshold": 90,  # [V8.0] Strict Sniper Score
            "total_trades_cycle": 0,    # Target: 10
            "cycle_gains_count": 0,     # [V8.0] Count of trades with PnL > 0
            "cycle_losses_count": 0,    # [V8.0] Count of trades with PnL < 0
            "accumulated_vault": 0.0,
            "sniper_mode_active": True,  # [V8.0] Master Toggle for Captain
            # V9.0 Cycle Diversification & Compound
            "used_symbols_in_cycle": [],  # V9.0: Lista de pares já operados no ciclo
            "cycle_start_bankroll": 0.0,  # V9.0: Banca travada no início do ciclo
            "next_entry_value": 0.0       # V9.0: Valor de entrada (20% da banca ciclo)
        }
    
    async def initialize_cycle(self):
        """Creates initial cycle document if it doesn't exist."""
        try:
            if not firebase_service.is_active or not firebase_service.db:
                return
                
            def _init():
                doc_ref = firebase_service.db.collection("vault_management").document("current_cycle")
                if not doc_ref.get().exists:
                    doc_ref.set(self._default_cycle())
                    logger.info("Vault cycle initialized.")
            
            await asyncio.to_thread(_init)
        except Exception as e:
            logger.error(f"Error initializing cycle: {e}")
    
    # ========== V9.0 CYCLE DIVERSIFICATION ==========
    
    async def is_symbol_used_in_cycle(self, symbol: str) -> bool:
        """
        V9.0: Verifica se um par já foi operado no ciclo atual de 10 trades.
        # V10.2: Dynamic Asset Locking (Drag Mode).
        - Drag Mode Active: Lock for 10 trades (Cycle).
        - Drag Mode Standby: Lock for 3 trades (Flexible).
        """
        try:
            current = await self.get_cycle_status()
            used_symbols = current.get("used_symbols_in_cycle", [])
            norm_symbol = symbol.replace(".P", "").upper()
            
            # V10.1: Check Drag Mode
            from services.signal_generator import signal_generator
            drag_mode = signal_generator.btc_drag_mode
            
            # Current virtual index (next trade would be len + 1)
            current_trade_index = len(used_symbols) + 1
            
            for item in used_symbols:
                # Handle legacy strings (V9.0)
                if isinstance(item, str):
                    if item.replace(".P", "").upper() == norm_symbol:
                        return True # Legacy items are always hard-locked
                
                # Handle V10.1 objects
                elif isinstance(item, dict):
                    item_sym = item.get("symbol", "").replace(".P", "").upper()
                    if item_sym == norm_symbol:
                        if drag_mode:
                            logger.info(f"🔒 {norm_symbol} locked (Drag Mode ACTIVE)")
                            return True # Hard lock in Drag Mode
                        else:
                            # Drag Mode OFF: Check 3-trade rule
                            entry_idx = item.get("entry_index", 0)
                            # If current is 5, entry was 1: 5 - 1 = 4 (> 3). Unlocked.
                            # If current is 4, entry was 1: 4 - 1 = 3 (>= 3). Unlocked.
                            diff = current_trade_index - entry_idx
                            if diff < 3:
                                logger.info(f"🔒 {norm_symbol} locked (Drag Mode STANDBY | diff {diff}/3)")
                                return True
                            else:
                                logger.info(f"🔓 {norm_symbol} UNLOCKED instance found (Drag Mode STANDBY | diff {diff}/3) - Checking for newer locks...")
                                # Continue checking other instances!
                                
            return False
        except Exception as e:
            logger.error(f"Error checking symbol in cycle: {e}")
            return False
    
    async def add_symbol_to_cycle(self, symbol: str):
        """
        V9.0: Adiciona par à lista de exclusão do ciclo.
        V10.1: Stores trade index for partial locking.
        """
        try:
            if not firebase_service.is_active or not firebase_service.db:
                return
            
            current = await self.get_cycle_status()
            used_symbols = current.get("used_symbols_in_cycle", [])
            norm_symbol = symbol.replace(".P", "").upper()
            
            # V10.1: Check if already exists (avoid duplicates even if allowed)
            # Actually, if we re-use, we should probably APPEND the new entry to lock it again?
            # Yes, if we reuse BTC at index 5, it should be locked again until index 8.
            # So simply appending is correct.
            
            current_index = len(used_symbols) + 1
            
            # V10.1 Object structure
            entry = {
                "symbol": norm_symbol,
                "entry_index": current_index,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            used_symbols.append(entry)
            
            total_trades = len(used_symbols)
            
            def _update():
                firebase_service.db.collection("vault_management").document("current_cycle").update({
                    "used_symbols_in_cycle": used_symbols
                })
            
            await asyncio.to_thread(_update)
            logger.info(f"🔄 V10.1: {norm_symbol} adicionado ao ciclo (Trade #{current_index}). Progresso Total: {total_trades}.")
            
            # Se completou 10 trades, iniciar recálculo de compound
            # Note: With reuse, 'total_trades' represents volume, not unique pairs.
            # This aligns with the cycle concept (10 trades total).
            if total_trades >= 10:
                await self.recalculate_cycle_bankroll()
                await self.reset_cycle_symbols()
                
        except Exception as e:
            logger.error(f"Error adding symbol to cycle: {e}")
    
    async def reset_cycle_symbols(self):
        """
        V9.0: Reseta a lista de pares após completar 10 trades.
        """
        try:
            if not firebase_service.is_active or not firebase_service.db:
                return
            
            current = await self.get_cycle_status()
            new_cycle_number = current.get("cycle_number", 1) + 1
            
            def _reset():
                firebase_service.db.collection("vault_management").document("current_cycle").update({
                    "used_symbols_in_cycle": [],
                    "cycle_number": new_cycle_number,
                    "total_trades_cycle": 0,
                    "cycle_gains_count": 0,
                    "cycle_losses_count": 0,
                    "cycle_profit": 0.0,
                    "started_at": datetime.now(timezone.utc).isoformat()
                })
            
            await asyncio.to_thread(_reset)
            await firebase_service.log_event("VAULT", f"🔄 V9.0: CICLO #{new_cycle_number} INICIADO! Lista de exclusão resetada. 83 pares disponíveis.", "SUCCESS")
            logger.info(f"V9.0: Cycle symbols reset. New cycle #{new_cycle_number}")
            
        except Exception as e:
            logger.error(f"Error resetting cycle symbols: {e}")
    
    async def initialize_cycle_bankroll(self, balance: float):
        """
        V9.0: Trava a banca no início de um novo ciclo para compound.
        """
        try:
            if not firebase_service.is_active or not firebase_service.db:
                return
            
            entry_value = balance * 0.20  # 20% margin rule
            
            def _init():
                firebase_service.db.collection("vault_management").document("current_cycle").update({
                    "cycle_start_bankroll": balance,
                    "next_entry_value": entry_value
                })
            
            await asyncio.to_thread(_init)
            logger.info(f"📊 V9.0 Compound: Banca travada em ${balance:.2f}. Entrada: ${entry_value:.2f}")
            await firebase_service.log_event("VAULT", f"📊 V9.0 COMPOUND: Banca do ciclo travada em ${balance:.2f}. Cada trade usará ${entry_value:.2f}.", "SUCCESS")
            
        except Exception as e:
            logger.error(f"Error initializing cycle bankroll: {e}")
    
    async def recalculate_cycle_bankroll(self):
        """
        V9.0: Recalcula a banca após completar 10 trades (Compound).
        Consulta saldo atual na Bybit e atualiza valores.
        """
        try:
            from services.bybit_rest import bybit_rest_service
            
            new_balance = await bybit_rest_service.get_wallet_balance()
            current = await self.get_cycle_status()
            old_bankroll = current.get("cycle_start_bankroll", 0)
            
            profit_pct = ((new_balance - old_bankroll) / old_bankroll * 100) if old_bankroll > 0 else 0
            new_entry = new_balance * 0.20
            
            if not firebase_service.is_active or not firebase_service.db:
                return
            
            def _update():
                firebase_service.db.collection("vault_management").document("current_cycle").update({
                    "cycle_start_bankroll": new_balance,
                    "next_entry_value": new_entry
                })
            
            await asyncio.to_thread(_update)
            
            emoji = "🚀" if profit_pct > 0 else "⚠️"
            logger.info(f"V9.0 Compound: Recálculo completo. Nova banca: ${new_balance:.2f} ({profit_pct:+.2f}%)")
            await firebase_service.log_event("VAULT", f"{emoji} V9.0 COMPOUND RECALCULADO: ${old_bankroll:.2f} → ${new_balance:.2f} ({profit_pct:+.2f}%). Nova entrada: ${new_entry:.2f}", "SUCCESS")
            
        except Exception as e:
            logger.error(f"Error recalculating cycle bankroll: {e}")
    
    async def get_used_symbols_in_cycle(self) -> list:
        """
        V9.0: Retorna lista de pares já usados no ciclo atual.
        """
        try:
            current = await self.get_cycle_status()
            return current.get("used_symbols_in_cycle", [])
        except Exception as e:
            logger.error(f"Error getting used symbols: {e}")
            return []
    
    # ========== END V9.0 ==========

    async def register_sniper_trade(self, trade_data: dict) -> dict:
        """
        [V7.0] SINGLE TRADE SNIPER: Registra um trade no ciclo de 10.
        - Sniper Wins (ROI >= 100%): Sobe o contador de 10x.
        - Sniper Loss ou ROI < 100%: Não conta como win, mas acumula lucro/perda.
        """
        try:
            if not firebase_service.is_active or not firebase_service.db:
                return self._default_cycle()
            
            current = await self.get_cycle_status()
            pnl = trade_data.get("pnl", 0)
            
            # ROI Check: Only count as win if ROI >= 100%
            roi = trade_data.get("pnl_percent", 0)
            if roi == 0 and trade_data.get("entry_price") and trade_data.get("exit_price"):
                from services.execution_protocol import execution_protocol
                roi = execution_protocol.calculate_roi(
                    trade_data["entry_price"], 
                    trade_data["exit_price"], 
                    trade_data.get("side", "Buy")
                )

            new_wins_count = current.get("cycle_gains_count", 0)
            new_losses_count = current.get("cycle_losses_count", 0)
            
            is_gain = pnl > 0
            
            if is_gain:
                new_wins_count += 1
                result_label = "GAIN 🟢"
            else:
                new_losses_count += 1
                result_label = "LOSS 🔴"
                
            new_profit = current.get("cycle_profit", 0) + pnl
            new_total_trades = current.get("total_trades_cycle", 0) + 1
            
            update_data = {
                "cycle_gains_count": new_wins_count,
                "cycle_losses_count": new_losses_count,
                "cycle_profit": new_profit,
                "total_trades_cycle": new_total_trades
            }
            
            def _update():
                firebase_service.db.collection("vault_management").document("current_cycle").update(update_data)
            
            await asyncio.to_thread(_update)
            
            # [V8.0] 10-Trade Cycle Trigger
            if new_total_trades >= 10:
                await firebase_service.log_event("VAULT", f"🏁 CICLO DE 10 TRADES FINALIZADO! Resultado: {new_wins_count}G / {new_losses_count}L. Recalibragem de banca ativada.", "SUCCESS")
                # Automation could go here to lock trading or notify
                
            event_type = "SUCCESS" if is_gain else "WARNING"
            result_msg = f"V8.0 Sniper {result_label} | Progresso: {new_wins_count}G / {new_losses_count}L (Total: {new_total_trades}/10) | PnL: ${pnl:.2f}"
            await firebase_service.log_event("VAULT", result_msg, event_type)
                # In a real implementation, this would trigger a bankroll reset or profit withdrawal
                
            event_type = "SUCCESS" if pnl > 0 else "WARNING"
            result_msg = f"Vault Sniper {result_label} | ROI: {roi:.1f}% | #{new_wins}/10 | Trade #{new_total_trades}/10 | PnL: ${pnl:.2f}"
            await firebase_service.log_event("VAULT", result_msg, event_type)
            
            if new_wins >= 10:
                await firebase_service.log_event("VAULT", f"🏆 CICLO PERFEITO {current.get('cycle_number', 1)}! Sniper Profit: ${new_profit:.2f}", "SUCCESS")
            
            # [V9.0] Fix: Ensure symbol is added to cycle list
            if trade_data.get("symbol"):
                await self.add_symbol_to_cycle(trade_data.get("symbol"))

            return current
            
        except Exception as e:
            logger.error(f"Error registering sniper trade: {e}")
            return self._default_cycle()

    async def sync_vault_with_history(self):
        """
        V5.2.2: Reconstrói o status do ciclo atual baseando-se no histórico de trades.
        Percorre os trades do ciclo atual e recalcula wins (ROI >= 80%) e lucro.
        """
        try:
            logger.info("🔄 Iniciando Sincronização Vault <-> Histórico...")
            if not firebase_service.is_active or not firebase_service.db:
                return
                
            current = await self.get_cycle_status()
            cycle_num = current.get("cycle_number", 1)
            
            # 1. Fetch trades for this cycle (Sniper & Surf)
            def _get_history():
                docs = (firebase_service.db.collection("trade_history").stream())
                return [d.to_dict() for d in docs]
            
            all_trades = await asyncio.to_thread(_get_history)
            
            # Filtro opcional: apenas trades após a data de início do ciclo
            started_at = current.get("started_at")
            trades = all_trades  # Default for loop
            if started_at:
                try:
                    start_dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                    trades = [t for t in all_trades if datetime.fromisoformat(t["timestamp"].replace("Z", "+00:00")) >= start_dt]
                except: pass

            logger.info(f"Encontrados {len(trades)} trades para o Ciclo #{cycle_num}")
            
            # 2. Recalculate
            new_wins = 0
            new_profit = 0.0
            new_losses = 0.0
            new_surf_profit = 0.0
            used_symbols = set()
            
            from services.execution_protocol import execution_protocol
            
            for t in trades:
                pnl = t.get("pnl", 0)
                roi = t.get("pnl_percent", 0)
                slot_type = t.get("slot_type", "SNIPER")
                symbol = t.get("symbol")
                
                # Filter by timestamp if cycle start is known
                if started_at:
                    try:
                        t_dt = datetime.fromisoformat(t["timestamp"].replace("Z", "+00:00"))
                        if t_dt < start_dt: continue
                    except: pass

                if slot_type == "SNIPER":
                    if roi == 0 and t.get("entry_price") and t.get("exit_price"):
                        roi = execution_protocol.calculate_roi(t["entry_price"], t["exit_price"], t.get("side", "Buy"))
                    
                    if roi >= 80.0:
                        new_wins += 1
                    
                    new_profit += pnl
                    if pnl < 0:
                        new_losses += abs(pnl)
                    
                    # Track unique symbols for the cycle
                    if symbol:
                        norm_symbol = symbol.replace(".P", "").upper()
                        used_symbols.add(norm_symbol)
                        
                elif slot_type == "SURF":
                    new_surf_profit += pnl
            
            # 3. Update Database
            update_data = {
                "sniper_wins": new_wins,
                "cycle_profit": new_profit,
                "cycle_losses": new_losses,
                "total_trades_cycle": len([t for t in trades if t.get('slot_type') == 'SNIPER']),
                "used_symbols_in_cycle": list(used_symbols)
            }
            
            def _push():
                firebase_service.db.collection("vault_management").document("current_cycle").update(update_data)
            
            await asyncio.to_thread(_push)
            logger.info(f"✅ Sincronização concluída: #{new_wins}/20 Wins | Total Trades (Sniper): {len([t for t in all_trades if t.get('slot_type') == 'SNIPER'])} | Profit: ${new_profit:.2f} | Symbols: {len(used_symbols)}")
            await firebase_service.log_event("VAULT", f"🔄 SINCRONIA COMPLETA: #{new_wins}/20 | Trades (Sniper): {len([t for t in all_trades if t.get('slot_type') == 'SNIPER'])}/10 | Profit: ${new_profit:.2f}", "SUCCESS")
            
        except Exception as e:
            logger.error(f"Error syncing vault with history: {e}")

    async def calculate_withdrawal_amount(self) -> dict:
        """
        Calcula o valor recomendado para saque (20% do lucro do ciclo).
        Retorna: {recommended_20pct, cycle_profit, vault_total}
        """
        try:
            current = await self.get_cycle_status()
            cycle_profit = current.get("cycle_profit", 0)
            vault_total = current.get("vault_total", 0)
            
            return {
                "recommended_20pct": cycle_profit * 0.20,
                "cycle_profit": cycle_profit,
                "vault_total": vault_total,
                "sniper_wins": current.get("sniper_wins", 0)
            }
        except Exception as e:
            logger.error(f"Error calculating withdrawal: {e}")
            return {"recommended_20pct": 0, "cycle_profit": 0, "vault_total": 0, "sniper_wins": 0}
    
    async def execute_withdrawal(self, amount: float, destination: str = "personal_vault") -> bool:
        """
        Registra uma retirada manual para o Vault.
        """
        try:
            if not firebase_service.is_active or not firebase_service.db:
                return False
            
            current = await self.get_cycle_status()
            new_vault_total = current.get("vault_total", 0) + amount
            
            withdrawal_record = {
                "amount": amount,
                "cycle_number": current.get("cycle_number", 1),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "destination": destination
            }
            
            def _execute():
                # Add to withdrawals subcollection
                firebase_service.db.collection("vault_management").document("withdrawals").collection("history").add(withdrawal_record)
                # Update vault total
                firebase_service.db.collection("vault_management").document("current_cycle").update({
                    "vault_total": new_vault_total
                })
            
            await asyncio.to_thread(_execute)
            await firebase_service.log_event("VAULT", f"💰 Retirada de ${amount:.2f} registrada. Cofre Total: ${new_vault_total:.2f}", "SUCCESS")
            
            return True
        except Exception as e:
            logger.error(f"Error executing withdrawal: {e}")
            return False
    
    async def get_withdrawal_history(self, limit: int = 20) -> list:
        """Retorna histórico de retiradas."""
        try:
            if not firebase_service.is_active or not firebase_service.db:
                return []
            
            def _get():
                docs = (firebase_service.db.collection("vault_management")
                        .document("withdrawals")
                        .collection("history")
                        .order_by("timestamp", direction="DESCENDING")
                        .limit(limit)
                        .stream())
                return [d.to_dict() for d in docs]
            
            return await asyncio.to_thread(_get)
        except Exception as e:
            logger.error(f"Error getting withdrawal history: {e}")
            return []
    
    async def start_new_cycle(self) -> dict:
        """
        Inicia um novo ciclo após completar 20 trades ou retirada manual.
        """
        try:
            if not firebase_service.is_active or not firebase_service.db:
                return self._default_cycle()
            
            current = await self.get_cycle_status()
            new_cycle = current.get("cycle_number", 1) + 1
            
            new_data = {
                "sniper_wins": 0,
                "cycle_number": new_cycle,
                "cycle_profit": 0.0,
                "cycle_losses": 0.0,
                "surf_profit": 0.0,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "in_admiral_rest": current.get("in_admiral_rest", False),
                "rest_until": current.get("rest_until"),
                "vault_total": current.get("vault_total", 0),
                "cautious_mode": False,
                "min_score_threshold": 75,
                "total_trades_cycle": 0,
                "accumulated_vault": current.get("accumulated_vault", 0.0)
            }
            
            def _update():
                firebase_service.db.collection("vault_management").document("current_cycle").set(new_data)
            
            await asyncio.to_thread(_update)
            await firebase_service.log_event("VAULT", f"🚀 Novo Ciclo #{new_cycle} iniciado!", "SUCCESS")
            
            return new_data
        except Exception as e:
            logger.error(f"Error starting new cycle: {e}")
            return self._default_cycle()
    
    async def activate_admiral_rest(self, hours: int = 24) -> bool:
        """
        Ativa o modo de descanso do Almirante (bloqueia novas ordens).
        """
        try:
            if not firebase_service.is_active or not firebase_service.db:
                return False
            
            rest_until = datetime.now(timezone.utc) + timedelta(hours=hours)
            
            def _activate():
                firebase_service.db.collection("vault_management").document("current_cycle").update({
                    "in_admiral_rest": True,
                    "rest_until": rest_until.isoformat()
                })
            
            await asyncio.to_thread(_activate)
            await firebase_service.log_event("VAULT", f"😴 Admiral's Rest ativado por {hours}h. Sistema em standby.", "WARNING")
            
            return True
        except Exception as e:
            logger.error(f"Error activating admiral rest: {e}")
            return False
    
    async def deactivate_admiral_rest(self) -> bool:
        """Desativa manualmente o modo de descanso."""
        try:
            if not firebase_service.is_active or not firebase_service.db:
                return False
            
            def _deactivate():
                firebase_service.db.collection("vault_management").document("current_cycle").update({
                    "in_admiral_rest": False,
                    "rest_until": None
                })
            
            await asyncio.to_thread(_deactivate)
            await firebase_service.log_event("VAULT", "⚡ Admiral's Rest desativado. Sistema operacional.", "SUCCESS")
            
            return True
        except Exception as e:
            logger.error(f"Error deactivating admiral rest: {e}")
            return False
    
    async def set_cautious_mode(self, enabled: bool, min_score: int = 85) -> bool:
        """
        Ativa/desativa modo cautela (aumenta threshold de score).
        """
        try:
            if not firebase_service.is_active or not firebase_service.db:
                return False
            
            def _set():
                firebase_service.db.collection("vault_management").document("current_cycle").update({
                    "cautious_mode": enabled,
                    "min_score_threshold": min_score if enabled else 75
                })
            
            await asyncio.to_thread(_set)
            
            status = f"ATIVADO (Score mínimo: {min_score})" if enabled else "DESATIVADO"
            await firebase_service.log_event("VAULT", f"⚠️ Modo Cautela {status}", "WARNING" if enabled else "INFO")
            
            return True
        except Exception as e:
            logger.error(f"Error setting cautious mode: {e}")
            return False

    async def set_sniper_mode(self, enabled: bool) -> bool:
        """
        [V8.0] Ativa ou Pausa o Capitão Sniper (Master Toggle).
        """
        try:
            if not firebase_service.is_active or not firebase_service.db:
                return False
            
            def _set():
                firebase_service.db.collection("vault_management").document("current_cycle").update({
                    "sniper_mode_active": enabled
                })
            
            await asyncio.to_thread(_set)
            
            status = "AUTORIZADO 🟢" if enabled else "BLOQUEADO 🔴"
            await firebase_service.log_event("VAULT", f"⚓ Capitão Sniper {status} pelo Almirante.", "SUCCESS" if enabled else "WARNING")
            
            return True
        except Exception as e:
            logger.error(f"Error setting sniper mode: {e}")
            return False
    
    async def is_trading_allowed(self) -> tuple[bool, str]:
        """
        Verifica se o sistema pode abrir novos trades.
        Returns: (allowed: bool, reason: str)
        """
        try:
            status = await self.get_cycle_status()
            
            # [V8.0] Master Toggle Check
            if not status.get("sniper_mode_active", True):
                return False, "Capitão Sniper está PAUSADO (Manual Stop)."

            if status.get("in_admiral_rest"):
                rest_until = status.get("rest_until", "")
                return False, f"Admiral's Rest ativo até {rest_until}"
            
            # [V5.2.5] Meta 100 Block
            if status.get("total_trades_cycle", 0) >= 100:
                return False, "META 100 ATINGIDA: Extraia 50% do lucro para continuar."
            
            return True, "Trading autorizado"
        except Exception as e:
            logger.error(f"Error checking trading permission: {e}")
            return True, "Fallback: Trading autorizado"

    async def get_dynamic_margin(self) -> float:
        """
        [V5.2.5] Calcula a margem dinâmica: 5% do saldo total (Banca + Lucro Ciclo).
        Garante o crescimento exponencial conforme planejado.
        """
        try:
            from services.bybit_rest import bybit_rest_service
            balance = await bybit_rest_service.get_wallet_balance()
            
            # Margem = 5% do saldo total atual
            margin = balance * 0.05
            
            # Garantir mínimo de $5 para evitar ordens rejeitadas
            return max(5.0, margin)
        except Exception as e:
            logger.error(f"Error calculating dynamic margin: {e}")
            return 5.0
    
    async def get_min_score_threshold(self) -> int:
        """Retorna o threshold de score atual (75 normal, 85+ em modo cautela)."""
        try:
            status = await self.get_cycle_status()
            return status.get("min_score_threshold", 75)
        except:
            return 75


vault_service = VaultService()
