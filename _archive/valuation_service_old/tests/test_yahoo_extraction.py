from unittest.mock import patch

import pandas as pd
import pytest

from valuation_service.connectors import YahooFinanceConnector


@pytest.fixture
def connector():
    return YahooFinanceConnector()

def test_yahoo_financials_structure(connector):
    """Test that the returned dictionary has the expected keys even if data is empty."""
    with patch("yfinance.Ticker") as mock_ticker:
        instance = mock_ticker.return_value
        instance.income_stmt.to_dict.return_value = {}
        instance.balance_sheet.to_dict.return_value = {}
        instance.cashflow.to_dict.return_value = {}

        data = connector.get_financials("AAPL")
        assert "income_statement" in data
        assert "balance_sheet" in data
        assert "cash_flow" in data
        assert data["income_statement"] == {}

def test_yahoo_market_data_fallback(connector):
    """Test fallback values when data is missing."""
    with patch("yfinance.Ticker") as mock_ticker:
        instance = mock_ticker.return_value
        # Empty info
        instance.info = {}

        with patch("valuation_service.connectors.yahoo.yf.download") as mock_download:
            # Mock empty download for TNX
            mock_download.return_value = pd.DataFrame()

            data = connector.get_market_data("AAPL")

            assert data["price"] is None
            assert data["beta"] is None
            assert data["market_cap"] is None
            assert data["risk_free_rate"] == 0.04  # Fallback

def test_yahoo_market_data_integration(connector):
    """Test with mocked valid data flow."""
    with patch("yfinance.Ticker") as mock_ticker:
        instance = mock_ticker.return_value
        instance.info = {
            "currentPrice": 200.0,
            "beta": 1.0,
            "marketCap": 1000000
        }

        with patch("valuation_service.connectors.yahoo.yf.download") as mock_download:
            mock_df = pd.DataFrame({'Close': [3.5]})
            mock_download.return_value = mock_df

            data = connector.get_market_data("AAPL")

            assert data["price"] == 200.0
            assert data["beta"] == 1.0
            assert data["market_cap"] == 1000000
            assert data["risk_free_rate"] == 0.035

def test_yahoo_tnx_exception(connector):
    """Test fallback when TNX download raises exception."""
    with patch("yfinance.Ticker") as mock_ticker:
        instance = mock_ticker.return_value
        instance.info = {}

        with patch("valuation_service.connectors.yahoo.yf.download") as mock_download:
            mock_download.side_effect = Exception("Network Error")

            data = connector.get_market_data("AAPL")
            assert data["risk_free_rate"] == 0.04
