import pytest
from unittest.mock import MagicMock
from valuation_service.service import ValuationService
from valuation_service.connectors import BaseConnector
from valuation_engine.fcff_ginzu.engine import GinzuInputs

def test_default_assumptions_logic():
    mock_connector = MagicMock(spec=BaseConnector)
    
    # Mock Market Data (Minimal)
    mock_connector.get_market_data.return_value = {
        "price": 100.0,
        "beta": 1.0,
        "market_cap": 1000.0,
        "shares_outstanding": 10.0,
        "risk_free_rate": 0.05
    }

    # Mock Financials: Scenario where Invested Capital is Negative (Book Equity + Debt < Cash)
    # Book Equity = 100, Debt = 0, Cash = 200 => InvCap = -100
    mock_connector.get_financials.return_value = {
        "income_statement": {
            "2023-12-31": {
                "Total Revenue": 1000.0,
                "EBIT": 100.0,
                "Pretax Income": -50.0, # Negative Pretax
                "Tax Provision": 0.0
            }
        },
        "balance_sheet": {
            "2023-12-31": {
                "Total Equity Gross Minority Interest": 100.0,
                "Total Debt": 0.0,
                "Cash And Cash Equivalents": 200.0
            }
        },
        "cash_flow": {}
    }
    
    service = ValuationService(mock_connector)
    inputs = service._map_data_to_inputs("TEST", mock_connector.get_financials(), mock_connector.get_market_data(), {})
    
    # 1. Sales to Capital Fallback check
    # InvCap is -100. Should default to 1.5
    assert inputs.sales_to_capital_1_5 == 1.5
    
    # 2. Tax Rate Fallback check
    # Pretax Income is -50. Should default to 0.20
    assert inputs.tax_rate_effective == 0.20
    
    # 3. Growth Rate Default
    # Should default to Risk Free Rate (0.05)
    assert inputs.rev_growth_y1 == 0.05
    
    # 4. WACC Initial Default
    # We set a placeholder 0.08 in previous step, checking it here
    assert inputs.wacc_initial == 0.08
