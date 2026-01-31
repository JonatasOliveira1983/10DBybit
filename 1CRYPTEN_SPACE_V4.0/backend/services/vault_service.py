"""
Vault Management Service V4.2
Gerencia o ciclo de 20 trades Sniper e retiradas para o Cofre do Almirante.
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
        Retorna o status atual do ciclo de 20 trades.
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
            "surf_profit": 0.0,       # Lucro líquido exclusivo Surf
            "started_at": datetime.now(timezone.utc).isoformat(),
            "in_admiral_rest": False,
            "rest_until": None,
            "vault_total": 0.0,
            "cautious_mode": False,
            "min_score_threshold": 75
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
    
    async def register_sniper_trade(self, trade_data: dict) -> dict:
        """
        V5.2.2: Registra um trade Sniper no ciclo.
        - Sniper Wins (ROI >= 80%): Sobe o contador de 20x.
        - Sniper Loss ou ROI < 80%: Não conta como win, mas acumula lucro/perda.
        """
        try:
            if not firebase_service.is_active or not firebase_service.db:
                return self._default_cycle()
            
            current = await self.get_cycle_status()
            pnl = trade_data.get("pnl", 0)
            
            # ROI Check: Only count as win if ROI >= 80% or was a Flash Zone exit
            # We use entry_price and exit_price to verify ROI if pnl_percent is missing
            roi = trade_data.get("pnl_percent", 0)
            if roi == 0 and trade_data.get("entry_price") and trade_data.get("exit_price"):
                from services.execution_protocol import execution_protocol
                roi = execution_protocol.calculate_roi(
                    trade_data["entry_price"], 
                    trade_data["exit_price"], 
                    trade_data.get("side", "Buy")
                )

            new_wins = current.get("sniper_wins", 0)
            new_losses = current.get("cycle_losses", 0)
            
            is_elite_win = roi >= 80.0
            
            if is_elite_win:
                new_wins += 1
                result_label = "ELITE WIN 💎"
            elif pnl > 0:
                result_label = "SOFT PROFIT 🟢"
            else:
                new_losses += abs(pnl)
                result_label = "LOSS ❌"
                
            new_profit = current.get("cycle_profit", 0) + pnl
            
            update_data = {
                "sniper_wins": new_wins,
                "cycle_losses": new_losses,
                "cycle_profit": new_profit
            }
            
            def _update():
                firebase_service.db.collection("vault_management").document("current_cycle").update(update_data)
            
            await asyncio.to_thread(_update)
            
            event_type = "SUCCESS" if pnl > 0 else "WARNING"
            result_msg = f"Vault Sniper {result_label} | ROI: {roi:.1f}% | #{new_wins}/20 | PnL: ${pnl:.2f}"
            await firebase_service.log_event("VAULT", result_msg, event_type)
            
            if new_wins >= 20:
                await firebase_service.log_event("VAULT", f"🏆 CICLO {current.get('cycle_number', 1)} COMPLETO! Sniper Profit: ${new_profit:.2f}", "SUCCESS")
            
            current.update(update_data)
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
            
            # 1. Fetch trades for this cycle
            def _get_history():
                docs = (firebase_service.db.collection("trade_history")
                        .where("slot_type", "==", "SNIPER")
                        .stream()) # No filter by cycle_number initially if not stored, we check timestamp?
                return [d.to_dict() for d in docs]
            
            trades = await asyncio.to_thread(_get_history)
            
            # Filtro opcional: apenas trades após a data de início do ciclo
            started_at = current.get("started_at")
            if started_at:
                try:
                    start_dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                    trades = [t for t in trades if datetime.fromisoformat(t["timestamp"].replace("Z", "+00:00")) >= start_dt]
                except: pass

            logger.info(f"Encontrados {len(trades)} trades para o Ciclo #{cycle_num}")
            
            # 2. Recalculate
            new_wins = 0
            new_profit = 0.0
            new_losses = 0.0
            
            from services.execution_protocol import execution_protocol
            
            for t in trades:
                pnl = t.get("pnl", 0)
                roi = t.get("pnl_percent", 0)
                
                if roi == 0 and t.get("entry_price") and t.get("exit_price"):
                    roi = execution_protocol.calculate_roi(t["entry_price"], t["exit_price"], t.get("side", "Buy"))
                
                if roi >= 80.0:
                    new_wins += 1
                
                new_profit += pnl
                if pnl < 0:
                    new_losses += abs(pnl)
            
            # 3. Update Database
            update_data = {
                "sniper_wins": new_wins,
                "cycle_profit": new_profit,
                "cycle_losses": new_losses
            }
            
            def _push():
                firebase_service.db.collection("vault_management").document("current_cycle").update(update_data)
            
            await asyncio.to_thread(_push)
            logger.info(f"✅ Sincronização concluída: #{new_wins}/20 Wins | Profit: ${new_profit:.2f}")
            await firebase_service.log_event("VAULT", f"🔄 SINCRONIA COMPLETA: #{new_wins}/20 | Profit: ${new_profit:.2f}", "SUCCESS")
            
        except Exception as e:
            logger.error(f"Error syncing vault with history: {e}")

    async def register_surf_trade(self, trade_data: dict) -> dict:
        """
        V4.9.4: Registra lucro/perda do modo Surf de forma independente.
        """
        try:
            if not firebase_service.is_active or not firebase_service.db:
                return self._default_cycle()
            
            current = await self.get_cycle_status()
            pnl = trade_data.get("pnl", 0)
            new_surf_profit = current.get("surf_profit", 0) + pnl
            
            update_data = {"surf_profit": new_surf_profit}
            
            def _update():
                firebase_service.db.collection("vault_management").document("current_cycle").update(update_data)
                
            await asyncio.to_thread(_update)
            await firebase_service.log_event("VAULT", f"🏄 Surf Trade Registered | PnL: ${pnl:.2f} | Surf Net: ${new_surf_profit:.2f}", "INFO")
            
            current.update(update_data)
            return current
        except Exception as e:
            logger.error(f"Error registering surf trade: {e}")
            return self._default_cycle()
    
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
                "min_score_threshold": 75
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
    
    async def is_trading_allowed(self) -> tuple[bool, str]:
        """
        Verifica se o sistema pode abrir novos trades.
        Returns: (allowed: bool, reason: str)
        """
        try:
            status = await self.get_cycle_status()
            
            if status.get("in_admiral_rest"):
                rest_until = status.get("rest_until", "")
                return False, f"Admiral's Rest ativo até {rest_until}"
            
            return True, "Trading autorizado"
        except Exception as e:
            logger.error(f"Error checking trading permission: {e}")
            return True, "Fallback: Trading autorizado"
    
    async def get_min_score_threshold(self) -> int:
        """Retorna o threshold de score atual (75 normal, 85+ em modo cautela)."""
        try:
            status = await self.get_cycle_status()
            return status.get("min_score_threshold", 75)
        except:
            return 75


vault_service = VaultService()
