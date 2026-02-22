"""
Test: Zero-division safeguards
==============================

Verifies that ``build_ginzu_inputs`` handles edge cases like zero revenue
or missing shares without raising ZeroDivisionError.
"""

import pytest
from valuation_engine.fcff_ginzu.engine import GinzuInputs, InputError
from valuation_engine.fcff_ginzu.inputs_builder import build_ginzu_inputs


def test_zero_revenue_margin_fallback():
    """When revenue is 0, margin should fall back to 0.10 (not ZeroDivisionError)."""
    data = {
        "revenues_base": 0.0,
        "ebit_reported_base": 0.0,
        "book_equity": 100.0,
        "book_debt": 50.0,
        "cash": 10.0,
        "shares_outstanding": 10.0,
        "stock_price": 50.0,
        "risk_free_rate": 0.04,
        "effective_tax_rate": 0.20,
        "marginal_tax_rate": 0.25,
    }

    # build_ginzu_inputs should not raise ZeroDivisionError
    inputs = build_ginzu_inputs(data, assumptions={})
    assert inputs.margin_y1 == 0.10
    assert inputs.margin_target == 0.10


def test_zero_invested_capital_stc_fallback():
    """When invested capital ≤ 0, sales-to-capital should use fallback (1.5)."""
    data = {
        "revenues_base": 1000.0,
        "ebit_reported_base": 100.0,
        "book_equity": 50.0,
        "book_debt": 0.0,
        "cash": 100.0,  # InvCap = 50 + 0 - 100 = -50
        "shares_outstanding": 10.0,
        "stock_price": 50.0,
        "risk_free_rate": 0.04,
        "effective_tax_rate": 0.20,
        "marginal_tax_rate": 0.25,
    }

    inputs = build_ginzu_inputs(data, assumptions={})
    assert inputs.sales_to_capital_1_5 == 1.5
    assert inputs.sales_to_capital_6_10 == 1.5


def test_engine_rejects_zero_revenue():
    """compute_ginzu should reject revenues_base=0 via InputError validation."""
    from valuation_engine.fcff_ginzu.engine import compute_ginzu

    data = {
        "revenues_base": 0.0,
        "ebit_reported_base": 0.0,
        "book_equity": 100.0,
        "book_debt": 50.0,
        "cash": 10.0,
        "shares_outstanding": 10.0,
        "stock_price": 50.0,
        "risk_free_rate": 0.04,
        "effective_tax_rate": 0.20,
        "marginal_tax_rate": 0.25,
    }

    inputs = build_ginzu_inputs(data, assumptions={})
    # The engine itself validates revenues_base > 0
    with pytest.raises(InputError, match="revenues_base must be > 0"):
        compute_ginzu(inputs)
