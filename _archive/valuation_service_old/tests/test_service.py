import pytest
from unittest.mock import MagicMock
from valuation_service.service import ValuationService
from valuation_service.connectors import BaseConnector

def test_valuation_service_initialization():
    mock_connector = MagicMock(spec=BaseConnector)
    service = ValuationService(mock_connector)
    assert service.connector == mock_connector

def test_calculate_valuation_flow():
    mock_connector = MagicMock(spec=BaseConnector)
    
    # Mock data return for get_valuation_inputs
    mock_connector.get_valuation_inputs.return_value = {
        "revenues_base": 1000.0,
        "ebit_reported_base": 100.0,
        "book_equity": 500.0,
        "book_debt": 200.0,
        "cash": 100.0,
        "shares_outstanding": 10.0,
        "stock_price": 50.0,
        "risk_free_rate": 0.04
    }
    
    service = ValuationService(mock_connector)
    
    result = service.calculate_valuation("AAPL", assumptions={})
    
    assert result is not None
    assert "value_of_equity" in result
    # Verify the connector method was called
    mock_connector.get_valuation_inputs.assert_called_once_with("AAPL")