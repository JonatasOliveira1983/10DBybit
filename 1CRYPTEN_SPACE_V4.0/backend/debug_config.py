from config import settings
import os

print("=== DEBUG CONFIG ===")
print(f"BYBIT_TESTNET: {settings.BYBIT_TESTNET}")
print(f"BYBIT_EXECUTION_MODE: {settings.BYBIT_EXECUTION_MODE}")
print(f"BYBIT_SIMULATED_BALANCE: {settings.BYBIT_SIMULATED_BALANCE}")
print(f"BYBIT_CATEGORY: {settings.BYBIT_CATEGORY}")
print("--- ENV VARS ---")
print(f"ENV_TESTNET: {os.environ.get('BYBIT_TESTNET')}")
print(f"ENV_EXEC_MODE: {os.environ.get('BYBIT_EXECUTION_MODE')}")
