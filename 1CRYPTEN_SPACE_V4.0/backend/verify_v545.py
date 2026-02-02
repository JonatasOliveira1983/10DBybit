import asyncio
import logging
import sys
import os

# Mocking services for isolation
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from unittest.mock import AsyncMock, MagicMock
import pytest

@pytest.mark.asyncio
async def test_sentiment_risk_zero():
    from services.execution_protocol import ExecutionProtocol
    ep = ExecutionProtocol()
    
    # Mock Redis Service
    from services.redis_service import redis_service
    redis_service.get_cvd = AsyncMock(return_value=-15000) # Negative CVD (Weakness for Long)
    redis_service.is_connected = True
    
    slot_data = {
        "symbol": "BTCUSDT",
        "side": "Buy",
        "entry_price": 40000,
        "current_stop": 39000,
        "slot_type": "SNIPER"
    }
    
    # ROI 15.5% (Weakness should trigger)
    # ROI = (Price - Entry) / Entry * 50 * 100
    # 15.5 = (P - 40000) / 40000 * 5000
    # 0.0031 = (P - 40000) / 40000
    # 124 = P - 40000 -> P = 40124
    current_price = 40124 
    roi = 15.5
    
    # Mock bybit_rest_service.round_price
    from services.bybit_rest import bybit_rest_service
    bybit_rest_service.round_price = AsyncMock(return_value=40000.0)
    
    should_close, reason, new_stop = await ep.process_sniper_logic(slot_data, current_price, roi)
    
    print(f"Test Result: should_close={should_close}, reason={reason}, new_stop={new_stop}")
    assert should_close is False
    assert new_stop == 40000.0 # Entry point (Risk Zero)

@pytest.mark.asyncio
async def test_surf_staircase():
    from services.execution_protocol import ExecutionProtocol
    ep = ExecutionProtocol()
    
    slot_data = {
        "symbol": "ETHUSDT",
        "side": "Buy",
        "entry_price": 2000,
        "current_stop": 1900,
        "slot_type": "SURF"
    }
    
    # ROI 31% -> Should move to 10%
    roi = 31.0
    current_price = 2012.4 # (2012.4 - 2000)/2000 * 5000 = 31
    
    should_close, reason, new_stop = await ep.process_surf_logic(slot_data, current_price, roi)
    
    # Calculate expected stop for 10% ROI
    # 10 = (S - 2000) / 2000 * 5000
    # 0.002 = (S - 2000) / 2000 -> S - 2000 = 4 -> S = 2004
    
    print(f"Surf Test 30%: new_stop={new_stop}")
    # The ladder is handled in _calculate_surf_trailing_stop which calculates price based on stop_roi
    assert new_stop is not None
    assert new_stop > 2000

if __name__ == "__main__":
    asyncio.run(test_sentiment_risk_zero())
    asyncio.run(test_surf_staircase())
