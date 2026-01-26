import pytest
from valuation_service.connectors import ConnectorFactory, BaseConnector
from typing import Dict, Any

class MockStatefulConnector(BaseConnector):
    def __init__(self):
        self.call_count = 0
        
    def get_financials(self, ticker: str) -> Dict[str, Any]:
        self.call_count += 1
        return {}
    
    def get_market_data(self, ticker: str) -> Dict[str, Any]:
        return {}

def test_connector_singleton_pattern():
    # Register our mock
    ConnectorFactory.register("stateful_mock", MockStatefulConnector)
    
    # Get first instance
    conn1 = ConnectorFactory.get_connector("stateful_mock")
    conn1.get_financials("AAPL")
    assert conn1.call_count == 1
    
    # Get second instance - should be SAME object
    conn2 = ConnectorFactory.get_connector("stateful_mock")
    assert conn1 is conn2
    
    # Verify state persistence
    conn2.get_financials("AAPL")
    assert conn1.call_count == 2
    assert conn2.call_count == 2
