"""
Tests for the ValuationService orchestration layer.
"""

from unittest.mock import MagicMock

from valuation_service.connectors import BaseConnector
from valuation_service.services.valuation import ValuationService


def test_valuation_service_initialization():
    mock_connector = MagicMock(spec=BaseConnector)
    service = ValuationService(mock_connector)
    assert service.connector == mock_connector


def test_calculate_valuation_flow():
    mock_connector = MagicMock(spec=BaseConnector)

    mock_connector.get_valuation_inputs.return_value = {
        "revenues_base": 1000.0,
        "ebit_reported_base": 100.0,
        "book_equity": 500.0,
        "book_debt": 200.0,
        "cash": 100.0,
        "shares_outstanding": 10.0,
        "stock_price": 50.0,
        "risk_free_rate": 0.04,
    }

    service = ValuationService(mock_connector)

    result = service.calculate_valuation("AAPL", assumptions={})

    assert result is not None
    assert "value_of_equity" in result
    mock_connector.get_valuation_inputs.assert_called_once_with("AAPL", as_of_date=None)


def test_full_service_integration():
    """End-to-end test: connector → builder → engine → dict output."""
    mock_connector = MagicMock(spec=BaseConnector)

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

    assert "value_of_equity" in result
    assert "value_of_operating_assets" in result
    assert "wacc" in result
    assert isinstance(result["wacc"], list)
    assert len(result["wacc"]) == 11  # 10 years + stable

    assert result["value_of_equity"] > 0

    mock_connector.get_valuation_inputs.assert_called_once_with("TEST", as_of_date=None)
