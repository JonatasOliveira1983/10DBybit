import asyncio
import logging
import time
import datetime
import os
from services.firebase_service import firebase_service

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ResetData")

async def delete_collection(collection_ref, batch_size=500):
    """Auxiliary function to delete a collection in batches."""
    while True:
        docs = await asyncio.to_thread(lambda: list(collection_ref.limit(batch_size).stream()))
        if not docs:
            break
        
        batch = firebase_service.db.batch()
        for doc in docs:
            batch.delete(doc.reference)
        
        await asyncio.to_thread(batch.commit)
        logger.info(f"✅ Deletados {len(docs)} documentos de {collection_ref.id}.")

async def reset_operational_data():
    """
    🧹 TOTAL OPERATIONAL RESET V6.0 (Relentless Batch Edition)
    Limpa Sinais, Slots, Histórico de Trades e Ciclo do Vault.
    """
    logger.info("🚀 Iniciando RESET TOTAL de Dados Operacionais...")
    
    # 0. Limpeza do Engine de Papel (Zombie Positions Shield)
    paper_file = "paper_storage.json"
    if os.path.exists(paper_file):
        try:
            os.remove(paper_file)
            logger.info(f"🔥 Arquivo '{paper_file}' removido com sucesso. Posições zumbis eliminadas.")
        except Exception as e:
            logger.error(f"❌ Erro ao remover '{paper_file}': {e}")
    else:
        logger.info(f"ℹ️ Arquivo '{paper_file}' não encontrado. O engine já está limpo.")

    try:
        # Inicializa a conexão com o Firebase
        await firebase_service.initialize()
        
        if not firebase_service.db:
            logger.error("❌ Falha ao inicializar o banco de dados Firebase.")
            return

        # 1. Limpeza de Sinais (journey_signals)
        logger.info("📡 Limpando coleção 'journey_signals'...")
        await delete_collection(firebase_service.db.collection("journey_signals"))

        # 2. Reset de Slots (slots_ativos)
        logger.info("🎰 Resetando 10 Slots Operacionais ('slots_ativos')...")
        for i in range(1, 11):
            slot_id = str(i)
            slot_ref = firebase_service.db.collection("slots_ativos").document(slot_id)
            slot_data = {
                "id": i,
                "symbol": None,
                "entry_price": 0,
                "current_stop": 0,
                "side": None,
                "pnl_percent": 0,
                "status": "IDLE",
                "visual_status": "IDLE",
                "last_update": time.time()
            }
            slot_ref.set(slot_data)
        logger.info("✅ Todos os 10 slots 'slots_ativos' foram resetados.")

        # 3. Limpeza de Histórico de Trades (trade_history)
        logger.info("📜 Limpando coleção 'trade_history'...")
        await delete_collection(firebase_service.db.collection("trade_history"))

        # 4. Limpeza de Histórico da Banca (banca_history)
        logger.info("📈 Limpando coleção 'banca_history'...")
        await delete_collection(firebase_service.db.collection("banca_history"))

        # 5. Reset do Ciclo do Vault (vault_management/current_cycle)
        logger.info("💎 Resetando Ciclo do Vault...")
        vault_ref = firebase_service.db.collection("vault_management").document("current_cycle")
        default_cycle = {
            "sniper_wins": 0,
            "cycle_number": 1,
            "cycle_profit": 0.0,
            "cycle_losses": 0.0,
            "surf_profit": 0.0,
            "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "in_admiral_rest": False,
            "rest_until": None,
            "vault_total": 0.0,
            "cautious_mode": False,
            "min_score_threshold": 75,
            "total_trades_cycle": 0,
            "accumulated_vault": 0.0
        }
        vault_ref.set(default_cycle)
        logger.info("✅ Ciclo do Vault resetado para o Ciclo #1.")

        # 6. Reset do Status da Banca (banca_status/status)
        logger.info("🏦 Resetando Status da Banca...")
        banca_status_ref = firebase_service.db.collection("banca_status").document("status")
        # Mantemos o saldo se existir, mas zeramos as perdas/lucros do ciclo no resumo
        current_banca = await firebase_service.get_banca_status()
        banca_data = {
            "saldo_total": current_banca.get("saldo_total", 100.0),
            "lucro_hoje": 0.0,
            "trades_hoje": 0,
            "win_rate": 0.0,
            "status": "ONLINE"
        }
        banca_status_ref.set(banca_data)
        logger.info("✅ Status da Banca zerado.")

        # Log final no Firebase para o Almirante ver
        await firebase_service.log_event("SYSTEM", "☢️ TOTAL OPERATIONAL RESET COMPLETED. System is now clean V6.0.", "SUCCESS")

        logger.info("🏁 RESET TOTAL concluído com sucesso.")

    except Exception as e:
        logger.error(f"❌ Erro durante o reset total: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(reset_operational_data())
