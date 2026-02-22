"""
Test: Full service integration
==============================

End-to-end test that verifies ValuationService.calculate_valuation()
produces valid results when given a mocked connector.
"""

import pytest
from unittest.mock import MagicMock
from valuation_service.service import ValuationService
from valuation_service.connectors import BaseConnector


def test_full_service_integration():
    mock_connector = MagicMock(spec=BaseConnector)

    # Mock get_valuation_inputs — the normalized data dict
    mock_connector.get_valuation_inputs.return_value = {
        "revenues_base": 1000.0,
        "ebit_reported_base": 150.0,
        "book_equity": 500.0,
        "book_debt": 200.0,
        "cash": 100.0,
        "shares_outstanding": 10.0,
        "stock_price": 100.0,
        "risk_free_rate": 0.04,
        "effective_tax_rate": 0.25,
        "marginal_tax_rate": 0.25,
        "cross_holdings": 0.0,
        "minority_interest": 0.0,
    }

    service = ValuationService(mock_connector)
    result = service.calculate_valuation("TEST")

    # Check for key outputs from GinzuOutputs
    assert "value_of_equity" in result
    assert "value_of_operating_assets" in result
    assert "wacc" in result
    assert isinstance(result["wacc"], list)
    assert len(result["wacc"]) == 11  # 10 years + stable

    # Basic sanity check on value
    # Equity Value should be positive for a profitable company
    assert result["value_of_equity"] > 0

    # Verify the connector method was called
    mock_connector.get_valuation_inputs.assert_called_once_with("TEST")
