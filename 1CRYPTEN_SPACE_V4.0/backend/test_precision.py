import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.bybit_rest import bybit_rest_service

async def test_rounding():
    print("🛡️ Verificando Surgência de Precisão (V5.2.4)...")
    
    # Mock session to avoid network calls during initialization
    bybit_rest_service._session = True # Just non-None to avoid lazy init
    
    # Define test cases: (symbol, input_price, expected_output, tick_size)
    test_cases = [
        ("BTCUSDT", 42350.1234, 42350.1, "0.1"),
        ("ETHUSDT", 2250.6789, 2250.65, "0.05"),
        ("SOLUSDT", 98.4321, 98.43, "0.01"),
        ("SHIBUSDT", 0.000008888, 0.00000889, "0.00000001"),
    ]

    for symbol, price, expected, tick in test_cases:
        # Manually seed cache for testing
        bybit_rest_service._instrument_cache[symbol] = {
            "priceFilter": {"tickSize": tick}
        }
        
        rounded = bybit_rest_service.round_price(symbol, price)
        status = "✅" if abs(rounded - expected) < 1e-10 else "❌"
        print(f"{status} {symbol}: {price} -> {rounded} (Tick: {tick}) | Expected: {expected}")

if __name__ == "__main__":
    asyncio.run(test_rounding())
