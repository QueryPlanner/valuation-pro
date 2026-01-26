import pytest
from unittest.mock import MagicMock
from valuation_service.service import ValuationService
from valuation_service.connectors import BaseConnector
from valuation_engine.fcff_ginzu.engine import GinzuInputs
import pandas as pd

def test_input_mapping_logic():
    mock_connector = MagicMock(spec=BaseConnector)
    
    # Mock Market Data
    mock_connector.get_market_data.return_value = {
        "price": 150.0,
        "beta": 1.2,
        "market_cap": 2500000000,
        "risk_free_rate": 0.045
    }

    # Mock Financials (simplified yfinance structure)
    # Using string dates for simplicity in mock, though yfinance uses Timestamps
    mock_connector.get_financials.return_value = {
        "income_statement": {
            "2023-12-31": {
                "Total Revenue": 1000.0,
                "EBIT": 200.0,
                "Tax Provision": 50.0,
                "Pretax Income": 250.0
            }
        },
        "balance_sheet": {
            "2023-12-31": {
                "Total Equity Gross Minority Interest": 800.0, # Book Equity
                "Total Debt": 400.0,
                "Cash And Cash Equivalents": 100.0,
                "Minority Interest": 0.0,
                # Non-operating assets not always present
            }
        },
        "cash_flow": {} # Not critical for basic inputs
    }
    
    service = ValuationService(mock_connector)
    
    # We expose a helper method or check via private method/integration
    # For this test, we'll call calculate_valuation and check if it runs without InputError
    # But ideally we want to verify the inputs created.
    
    # Let's subclass to inspect inputs
    class InspectableService(ValuationService):
        def _compute_inputs(self, ticker, assumptions):
            self.last_inputs = super()._map_inputs(ticker, assumptions)
            return super().calculate_valuation(ticker, assumptions)
            
    # Wait, I haven't implemented _map_inputs yet. 
    # The test should just assert that calculate_valuation returns a result 
    # AND that specific inputs match our mock data.
    
    # I will modify Service to expose the mapping logic or test it via private method access if necessary.
    # Better: I will implement a `_map_data_to_inputs` method in the class and test that.
    
    inputs = service._map_data_to_inputs(
        ticker="TEST",
        financials=mock_connector.get_financials.return_value,
        market_data=mock_connector.get_market_data.return_value,
        assumptions={}
    )
    
    assert isinstance(inputs, GinzuInputs)
    assert inputs.revenues_base == 1000.0
    assert inputs.ebit_reported_base == 200.0
    assert inputs.book_equity == 800.0
    assert inputs.book_debt == 400.0
    assert inputs.cash == 100.0
    assert inputs.stock_price == 150.0
    assert inputs.riskfree_rate_now == 0.045
    
    # Derived defaults
    # Effective Tax Rate = 50 / 250 = 0.2
    assert inputs.tax_rate_effective == 0.2
