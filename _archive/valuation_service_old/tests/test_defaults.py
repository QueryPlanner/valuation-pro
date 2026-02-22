"""
Test: Default assumptions and edge-case heuristics
===================================================

Verifies that ``build_ginzu_inputs`` applies correct defaults when e.g.
invested capital is negative, pretax income is negative, etc.
"""

import pytest
from valuation_engine.fcff_ginzu.engine import GinzuInputs
from valuation_engine.fcff_ginzu.inputs_builder import build_ginzu_inputs


def test_negative_invested_capital_fallback():
    """When invested capital < 0, sales-to-capital should use the fallback (1.5)."""
    data = {
        "revenues_base": 1000.0,
        "ebit_reported_base": 100.0,
        "book_equity": 100.0,
        "book_debt": 0.0,
        "cash": 200.0,  # InvCap = 100 + 0 - 200 = -100
        "shares_outstanding": 10.0,
        "stock_price": 100.0,
        "risk_free_rate": 0.05,
        "effective_tax_rate": 0.0,  # Pretax was negative in original scenario
        "marginal_tax_rate": 0.25,
    }

    inputs = build_ginzu_inputs(data, assumptions={})

    assert isinstance(inputs, GinzuInputs)
    # InvCap is -100 → should fall back to 1.5
    assert inputs.sales_to_capital_1_5 == 1.5


def test_effective_tax_rate_from_data():
    """Effective tax rate should come from data when no assumption overrides it."""
    data = {
        "revenues_base": 1000.0,
        "ebit_reported_base": 100.0,
        "book_equity": 500.0,
        "book_debt": 200.0,
        "cash": 50.0,
        "shares_outstanding": 10.0,
        "stock_price": 100.0,
        "risk_free_rate": 0.05,
        "effective_tax_rate": 0.15,
        "marginal_tax_rate": 0.25,
    }

    inputs = build_ginzu_inputs(data, assumptions={})
    assert inputs.tax_rate_effective == 0.15


def test_default_growth_and_wacc():
    """Default rev_growth_y1 should be 0.05 and wacc_initial should be 0.08."""
    data = {
        "revenues_base": 1000.0,
        "ebit_reported_base": 100.0,
        "book_equity": 500.0,
        "book_debt": 200.0,
        "cash": 50.0,
        "shares_outstanding": 10.0,
        "stock_price": 100.0,
        "risk_free_rate": 0.05,
        "effective_tax_rate": 0.20,
        "marginal_tax_rate": 0.25,
    }

    inputs = build_ginzu_inputs(data, assumptions={})
    assert inputs.rev_growth_y1 == 0.05
    assert inputs.wacc_initial == 0.08
