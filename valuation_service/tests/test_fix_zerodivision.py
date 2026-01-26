import pytest
from unittest.mock import MagicMock
from valuation_service.service import ValuationService
from valuation_service.connectors import BaseConnector

def test_zero_price_derivation_safeguard():
    mock_connector = MagicMock(spec=BaseConnector)
    
    # Mock Market Data with 0 price but valid market cap
    # This would trigger the division logic if shares_outstanding is missing
    mock_connector.get_market_data.return_value = {
        "price": 0.0, 
        "market_cap": 1000000.0,
        # "shares_outstanding": missing
        "risk_free_rate": 0.045
    }

    mock_connector.get_financials.return_value = {
        "income_statement": {"2023": {"Total Revenue": 1000.0}},
        "balance_sheet": {},
        "cash_flow": {}
    }
    
    service = ValuationService(mock_connector)
    
    # Expect ValueError (could not determine shares), NOT ZeroDivisionError
    with pytest.raises(ValueError, match="Could not determine Share Count"):
        service._map_data_to_inputs(
            ticker="TEST",
            financials=mock_connector.get_financials.return_value,
            market_data=mock_connector.get_market_data.return_value,
            assumptions={}
        )
