"""
Test: Full API integration flow
================================

End-to-end test going through API → Connector → Service → Engine → API Response.
Mocks only the lowest level (yfinance calls).
"""

from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, PropertyMock
import pandas as pd
import numpy as np
from valuation_service.main import app

client = TestClient(app)

def _build_mock_ticker():
    """Build a properly mocked yfinance Ticker with quarterly + annual data."""
    instance = MagicMock()

    # Annual income statement (used for fallback and R&D history)
    ann_inc = pd.DataFrame(
        {
            pd.Timestamp("2023-12-31"): {
                "Total Revenue": 50000.0,
                "Operating Income": 8000.0,
                "Research And Development": 3000.0,
                "Pretax Income": 7500.0,
                "Tax Provision": 1875.0,
            },
        }
    )
    instance.financials = ann_inc

    # Quarterly income statement (4 quarters for LTM)
    q_inc = pd.DataFrame(
        {
            pd.Timestamp("2023-12-31"): {"Total Revenue": 13000.0, "Operating Income": 2000.0, "Research And Development": 800.0, "Pretax Income": 1900.0, "Tax Provision": 475.0},
            pd.Timestamp("2023-09-30"): {"Total Revenue": 12500.0, "Operating Income": 2000.0, "Research And Development": 750.0, "Pretax Income": 1800.0, "Tax Provision": 450.0},
            pd.Timestamp("2023-06-30"): {"Total Revenue": 12500.0, "Operating Income": 2000.0, "Research And Development": 750.0, "Pretax Income": 1800.0, "Tax Provision": 450.0},
            pd.Timestamp("2023-03-31"): {"Total Revenue": 12000.0, "Operating Income": 2000.0, "Research And Development": 700.0, "Pretax Income": 1800.0, "Tax Provision": 450.0},
        }
    )
    instance.quarterly_financials = q_inc

    # Quarterly balance sheet (MRQ)
    q_bal = pd.DataFrame(
        {
            pd.Timestamp("2023-12-31"): {
                "Stockholders Equity": 30000.0,
                "Total Equity Gross Minority Interest": 30000.0,
                "Total Debt": 10000.0,
                "Cash Cash Equivalents And Short Term Investments": 8000.0,
                "Cash And Cash Equivalents": 5000.0,
                "Other Short Term Investments": 3000.0,
                "Minority Interest": np.nan,
                "Investmentin Financial Assets": 0.0,
                "Ordinary Shares Number": 1000.0,
            },
        }
    )
    instance.quarterly_balance_sheet = q_bal

    # Annual income statement (for get_financials and fallback)
    instance.income_stmt = ann_inc
    instance.balance_sheet = q_bal
    instance.cashflow = pd.DataFrame()

    # Info dict
    instance.info = {
        "currentPrice": 150.0,
        "beta": 1.1,
        "marketCap": 150000.0,
        "sharesOutstanding": 1000.0,
        "country": "US",
    }

    return instance


def test_api_full_flow_integration():
    """
    Test the full flow from API Request -> Connector -> Service -> Engine -> API Response
    Mocking only the lowest level (yfinance calls)
    """
    with patch("valuation_service.connectors.yahoo.yf.Ticker") as mock_ticker_cls, \
         patch("valuation_service.connectors.yahoo.yf.download") as mock_download:

        mock_ticker_cls.return_value = _build_mock_ticker()

        # Mock Treasury Yield (^TNX returns yield in percentage points)
        mock_df = pd.DataFrame({"Close": [4.25]})
        mock_download.return_value = mock_df

        # 1. Test GET /data/financials/AAPL
        resp = client.get("/data/financials/AAPL")
        assert resp.status_code == 200

        # 2. Test GET /data/market/AAPL
        resp = client.get("/data/market/AAPL")
        assert resp.status_code == 200
        data = resp.json()
        assert data["price"] == 150.0
        assert data["risk_free_rate"] == 0.0425

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
