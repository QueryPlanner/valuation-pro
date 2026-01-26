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
    
    # Mock data return
    mock_connector.get_financials.return_value = {
        "income_statement": {"2023": {"Total Revenue": 1000, "EBIT": 100}},
        "balance_sheet": {"2023": {"Total Assets": 2000, "Total Equity": 800, "Total Debt": 500}},
        "cash_flow": {"2023": {"Operating Cash Flow": 150}}
    }
    mock_connector.get_market_data.return_value = {
        "price": 100.0,
        "beta": 1.1,
        "market_cap": 10000.0,
        "risk_free_rate": 0.04
    }
    
    service = ValuationService(mock_connector)
    
    # We expect this to fail until implemented
    # passing a minimal assumption set
    result = service.calculate_valuation("AAPL", assumptions={})
    
    assert result is not None
    assert "value_of_equity" in result
