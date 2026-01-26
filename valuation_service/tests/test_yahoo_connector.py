import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from valuation_service.connectors import YahooFinanceConnector

@pytest.fixture
def mock_yfinance_ticker():
    with patch("yfinance.Ticker") as mock_ticker:
        yield mock_ticker

def test_yahoo_financials(mock_yfinance_ticker):
    # Setup mock return values
    instance = mock_yfinance_ticker.return_value
    instance.income_stmt.to_dict.return_value = {"2023": {"Revenue": 100}}
    instance.balance_sheet.to_dict.return_value = {"2023": {"Assets": 500}}
    instance.cashflow.to_dict.return_value = {"2023": {"OperatingCashFlow": 50}}

    connector = YahooFinanceConnector()
    data = connector.get_financials("AAPL")

    assert "income_statement" in data
    assert "balance_sheet" in data
    assert "cash_flow" in data
    assert data["income_statement"] == {"2023": {"Revenue": 100}}

def test_yahoo_market_data(mock_yfinance_ticker):
    # Setup mock return values
    instance = mock_yfinance_ticker.return_value
    instance.info = {
        "currentPrice": 150.0,
        "beta": 1.2,
        "marketCap": 2000000000
    }
    
    with patch("valuation_service.connectors.yahoo.yf.download") as mock_download:
        # Create a proper DataFrame for the mock to avoid indexing errors
        mock_df = pd.DataFrame({'Close': [4.5]})
        mock_download.return_value = mock_df

        connector = YahooFinanceConnector()
        data = connector.get_market_data("AAPL")

        assert data["price"] == 150.0
        assert data["beta"] == 1.2
        assert data["risk_free_rate"] == 0.045