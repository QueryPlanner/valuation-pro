import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
import datetime
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

def test_get_valuation_inputs_annual_fallback(mock_yfinance_ticker):
    """Test fallback to annual data when quarterly data is insufficient."""
    instance = mock_yfinance_ticker.return_value
    
    # Insufficient Quarterly Data (only 1 column)
    mock_q_inc = pd.DataFrame({
        '2023-09-30': [10.0] 
    }, index=['Total Revenue'])
    instance.quarterly_financials = mock_q_inc
    
    # Annual Data
    mock_ann_inc = pd.DataFrame({
        '2022-12-31': [1000.0, 100.0, 50.0, 20.0, 150.0],
        '2021-12-31': [900.0, 90.0, 45.0, 18.0, 140.0]
    }, index=['Total Revenue', 'Operating Income', 'Research And Development', 'Tax Provision', 'Pretax Income'])
    instance.financials = mock_ann_inc
    
    instance.quarterly_balance_sheet = pd.DataFrame() # Empty BS
    instance.info = {"sharesOutstanding": 100, "currentPrice": 50.0}
    
    connector = YahooFinanceConnector()
    inputs = connector.get_valuation_inputs("AAPL")
    
    # Should use Annual MRQ (first column of annual)
    assert inputs["revenues_base"] == 1000.0
    assert inputs["ebit_reported_base"] == 100.0
    assert inputs["rnd_expense"] == 50.0

def test_get_valuation_inputs_retrospective_shares_fallback(mock_yfinance_ticker):
    """Test fallback to annual balance sheet when quarterly balance sheet is empty for retrospective date."""
    instance = mock_yfinance_ticker.return_value
    
    # Valuation Date: 2024-02-01
    as_of_date = datetime.date(2024, 2, 1)

    # Quarterly Balance Sheet: Only future data (e.g. 2024-06-30) relative to valuation date
    # Or just mock it such that filtering by date returns empty.
    # The connector logic filters columns <= as_of_date.
    # So if we provide only dates > 2024-02-01, it will be empty after filtering.
    mock_q_bal = pd.DataFrame({
        '2024-06-30': [1200.0],
    }, index=['Ordinary Shares Number'])
    # Need to ensure columns are datetime-like for the filter logic to work
    mock_q_bal.columns = pd.to_datetime(mock_q_bal.columns)
    instance.quarterly_balance_sheet = mock_q_bal
    
    # Annual Balance Sheet: Has data for 2023-12-31 (valid for 2024-02-01)
    mock_ann_bal = pd.DataFrame({
        '2023-12-31': [1000.0],
        '2022-12-31': [900.0]
    }, index=['Ordinary Shares Number'])
    mock_ann_bal.columns = pd.to_datetime(mock_ann_bal.columns)
    instance.balance_sheet = mock_ann_bal
    
    # Other Dataframes (can be minimal)
    instance.quarterly_financials = pd.DataFrame()
    instance.financials = pd.DataFrame()
    instance.info = {"currentPrice": 50.0} # Used if historical price fails, though historical price logic is mocked separately usually
    
    with patch("valuation_service.connectors.yahoo.yf.download") as mock_download:
        # Mock historical price
        mock_df = pd.DataFrame({'Close': [45.0]}, index=[pd.Timestamp('2024-01-31')])
        mock_download.return_value = mock_df

        connector = YahooFinanceConnector()
        inputs = connector.get_valuation_inputs("AAPL", as_of_date=as_of_date)
        
        # Should pick up 1000.0 from annual 2023-12-31
        assert inputs["shares_outstanding"] == 1000.0
