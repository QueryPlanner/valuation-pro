import pytest
from valuation_service.connectors import ConnectorFactory, BaseConnector
from typing import Dict, Any

class MockConnector(BaseConnector):
    def get_financials(self, ticker: str) -> Dict[str, Any]:
        return {"mock": "financials"}
    
    def get_market_data(self, ticker: str) -> Dict[str, Any]:
        return {"mock": "market"}

def test_connector_interface():
    # Ensure BaseConnector enforces implementation
    with pytest.raises(TypeError):
        class IncompleteConnector(BaseConnector):
            pass
        IncompleteConnector()

def test_factory_registration():
    ConnectorFactory.register("mock", MockConnector)
    connector = ConnectorFactory.get_connector("mock")
    assert isinstance(connector, MockConnector)
    assert connector.get_financials("AAPL") == {"mock": "financials"}

def test_factory_invalid_connector():
    with pytest.raises(ValueError):
        ConnectorFactory.get_connector("non_existent")
