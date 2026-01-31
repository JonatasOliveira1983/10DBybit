import asyncio
import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import sys
import os

print("Script starting...")

# 1. Mock modules BEFORE importing BankrollManager to avoid side effects
mock_firebase_module = MagicMock()
mock_bybit_module = MagicMock()
mock_vault_module = MagicMock()
mock_config_module = MagicMock()

sys.modules["services.firebase_service"] = mock_firebase_module
sys.modules["services.bybit_rest"] = mock_bybit_module
sys.modules["services.vault_service"] = mock_vault_module
sys.modules["config"] = mock_config_module

# Add the backend directory to sys.path
backend_dir = r"c:\Users\spcom\Desktop\10D-Bybit1.0\1CRYPTEN_SPACE_V4.0\backend"
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

# Now import BankrollManager
from services.bankroll import BankrollManager

class TestTradeSync(unittest.IsolatedAsyncioTestCase):
    async def test_real_mode_sync_registers_trade(self):
        # Setup mocks
        slot_id = 1
        symbol = "ADAUSDT"
        
        manager = BankrollManager()
        
        # Configure the mock instances that were "imported" via sys.modules
        mock_firebase = mock_firebase_module.firebase_service
        mock_bybit = mock_bybit_module.bybit_rest_service
        mock_vault = mock_vault_module.vault_service
        
        # Setup mock_firebase
        mock_firebase.get_active_slots = AsyncMock(return_value=[
            {
                "id": slot_id,
                "symbol": symbol,
                "entry_price": 0.5,
                "side": "Buy",
                "timestamp_last_update": 0 # Force sync (old)
            }
        ])
        mock_firebase.update_slot = AsyncMock()
        mock_firebase.log_trade = AsyncMock()
        mock_firebase.log_event = AsyncMock()
        
        # Setup mock_bybit
        mock_bybit.execution_mode = "REAL"
        mock_bybit.category = "linear"
        mock_bybit._strip_p.side_effect = lambda x: x.replace(".P", "") if x else x
        mock_bybit.get_active_positions = AsyncMock(return_value=[]) # EMPTY positions (closed)
        
        # mock_bybit.get_closed_pnl is called via asyncio.to_thread, so it should be a normal MagicMock
        mock_bybit.get_closed_pnl = MagicMock(return_value=[
            {
                "closedPnl": "10.5",
                "avgExitPrice": "0.6",
                "qty": "100"
            }
        ])
        
        # Setup mock_vault
        # In bankroll.py, register_sniper_trade calls vault_service.register_sniper_trade
        mock_vault.register_sniper_trade = AsyncMock()
        
        # Setup settings
        mock_config_module.settings.MAX_SLOTS = 10
        mock_config_module.settings.RISK_CAP_PERCENT = 0.2
        mock_config_module.settings.INITIAL_SLOTS = 4
        mock_config_module.settings.LEVERAGE = 50
        
        # 2. Run Sync
        print("\n--- Running Sync Test ---")
        await manager.sync_slots_with_exchange()
        print("--- Sync Test Completed ---")
        
        # 3. Assertions
        # Check if log_trade was called
        mock_firebase.log_trade.assert_called_once()
        trade_data = mock_firebase.log_trade.call_args[0][0]
        print(f"Logged Trade Data: {trade_data}")
        self.assertEqual(trade_data["symbol"], symbol)
        self.assertEqual(trade_data["pnl"], 10.5)
        self.assertEqual(trade_data["close_reason"], "EXCHANGE_SYNC_DETECTED")
        
        # Check if vault was registered
        mock_vault.register_sniper_trade.assert_called_once()
        print("Vault registration verified.")
        
        # Check if slot was updated (cleared)
        mock_firebase.update_slot.assert_any_call(slot_id, {
            "symbol": None, "entry_price": 0, "current_stop": 0, 
            "status_risco": "IDLE", "side": None, "pnl_percent": 0
        })
        print("Slot clearing verified.")

if __name__ == "__main__":
    unittest.main()
