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

def test_get_valuation_inputs(mock_yfinance_ticker):
    instance = mock_yfinance_ticker.return_value
    
    # Mock Dataframes
    # LTM Logic: 4 quarters sum
    mock_q_inc = pd.DataFrame({
        '2023-09-30': [100.0, 10.0, 2.0, 20.0],
        '2023-06-30': [100.0, 10.0, 2.0, 20.0],
        '2023-03-31': [100.0, 10.0, 2.0, 20.0],
        '2022-12-31': [100.0, 10.0, 2.0, 20.0]
    }, index=['Total Revenue', 'Operating Income', 'Research And Development', 'Pretax Income'])
    
    # Needs to be capable of .loc access
    instance.quarterly_financials = mock_q_inc
    
    # Balance Sheet (MRQ)
    mock_q_bal = pd.DataFrame({
        '2023-09-30': [500.0, 200.0, 50.0]
    }, index=['Stockholders Equity', 'Total Debt', 'Cash Cash Equivalents And Short Term Investments'])
    instance.quarterly_balance_sheet = mock_q_bal
    
    instance.financials = pd.DataFrame() # Annual
    instance.info = {"sharesOutstanding": 100, "currentPrice": 50.0, "country": "US"}
    
    connector = YahooFinanceConnector()
    inputs = connector.get_valuation_inputs("AAPL")
    
    # LTM Revenue = 100 * 4 = 400
    assert inputs["revenues_base"] == 400.0
    # LTM EBIT = 10 * 4 = 40
    assert inputs["ebit_reported_base"] == 40.0
    # LTM R&D = 2 * 4 = 8
    assert inputs["rnd_expense"] == 8.0
    
    # MRQ Balance Sheet
    assert inputs["book_equity"] == 500.0
    assert inputs["book_debt"] == 200.0
    assert inputs["cash"] == 50.0
    
    assert inputs["shares_outstanding"] == 100
