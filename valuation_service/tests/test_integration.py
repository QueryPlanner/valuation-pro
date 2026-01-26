import pytest
from unittest.mock import MagicMock
from valuation_service.service import ValuationService
from valuation_service.connectors import BaseConnector

def test_full_service_integration():
    mock_connector = MagicMock(spec=BaseConnector)
    
    # Provide enough data for a valid valuation
    mock_connector.get_market_data.return_value = {
        "price": 100.0,
        "beta": 1.0,
        "market_cap": 1000.0,
        "shares_outstanding": 10.0,
        "risk_free_rate": 0.04
    }
    
    # Profitable company
    mock_connector.get_financials.return_value = {
        "income_statement": {
            "2023-12-31": {
                "Total Revenue": 1000.0,
                "EBIT": 150.0,
                "Pretax Income": 140.0,
                "Tax Provision": 35.0 # 25% tax
            }
        },
        "balance_sheet": {
            "2023-12-31": {
                "Total Equity Gross Minority Interest": 500.0,
                "Total Debt": 200.0,
                "Cash And Cash Equivalents": 100.0,
                "Minority Interest": 0.0
            }
        },
        "cash_flow": {}
    }
    
    service = ValuationService(mock_connector)
    result = service.calculate_valuation("TEST")
    
    # Check for key outputs from GinzuOutputs
    assert "value_of_equity" in result
    assert "value_of_operating_assets" in result
    assert "wacc" in result
    assert isinstance(result["wacc"], list)
    assert len(result["wacc"]) == 11 # 10 years + stable
    
    # Basic sanity check on value
    # Equity Value should be positive for a profitable company
    assert result["value_of_equity"] > 0
