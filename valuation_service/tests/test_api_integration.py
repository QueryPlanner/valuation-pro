from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import pandas as pd
from valuation_service.main import app

client = TestClient(app)

def test_api_full_flow_integration():
    """
    Test the full flow from API Request -> Connector -> Service -> Engine -> API Response
    Mocking only the lowest level (yfinance calls)
    """
    
    # Mock yfinance Ticker and download
    with patch("valuation_service.connectors.yahoo.yf.Ticker") as mock_ticker_cls, \
         patch("valuation_service.connectors.yahoo.yf.download") as mock_download:
        
        # Setup Financials
        instance = mock_ticker_cls.return_value
        instance.income_stmt.to_dict.return_value = {
            "2023-12-31": {"Total Revenue": 1000.0, "EBIT": 150.0, "Pretax Income": 140.0, "Tax Provision": 35.0}
        }
        instance.balance_sheet.to_dict.return_value = {
            "2023-12-31": {
                "Total Equity Gross Minority Interest": 500.0, 
                "Total Debt": 200.0, 
                "Cash And Cash Equivalents": 100.0,
                "Minority Interest": 0.0
            }
        }
        instance.cashflow.to_dict.return_value = {}
        
        # Setup Market Data
        instance.info = {
            "currentPrice": 100.0,
            "beta": 1.0,
            "marketCap": 1000.0,
            "sharesOutstanding": 10.0
        }
        
        # Mock Treasury Yield
        mock_df = pd.DataFrame({'Close': [4.0]}) # 4%
        mock_download.return_value = mock_df
        
        # 1. Test GET /data/financials/AAPL
        resp = client.get("/data/financials/AAPL")
        assert resp.status_code == 200
        data = resp.json()
        assert "income_statement" in data
        assert data["income_statement"]["2023-12-31"]["Total Revenue"] == 1000.0
        
        # 2. Test GET /data/market/AAPL
        resp = client.get("/data/market/AAPL")
        assert resp.status_code == 200
        data = resp.json()
        assert data["price"] == 100.0
        assert data["risk_free_rate"] == 0.04
        
        # 3. Test POST /valuation/calculate (Default Assumptions)
        resp = client.post("/valuation/calculate", json={"ticker": "AAPL"})
        assert resp.status_code == 200
        result = resp.json()
        
        # Verify Engine Output
        assert result["value_of_equity"] > 0
        assert result["estimated_value_per_share"] > 0
        # WACC should be calculated
        assert result["wacc"][0] > 0
        
        # 4. Test POST /valuation/calculate (With Overrides)
        # Override Tax Rate to 0% -> higher value
        assumptions = {"tax_rate_effective": 0.0, "tax_rate_marginal": 0.0}
        resp_override = client.post("/valuation/calculate", json={"ticker": "AAPL", "assumptions": assumptions})
        assert resp_override.status_code == 200
        result_override = resp_override.json()
        
        assert result_override["value_of_equity"] > result["value_of_equity"]
