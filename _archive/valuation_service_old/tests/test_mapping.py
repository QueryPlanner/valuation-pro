"""
Test: Input mapping via build_ginzu_inputs
==========================================

Verifies that the shared ``build_ginzu_inputs`` function correctly
maps raw connector data + assumptions into a valid ``GinzuInputs``.
"""

import pytest
from valuation_engine.fcff_ginzu.engine import GinzuInputs
from valuation_engine.fcff_ginzu.inputs_builder import build_ginzu_inputs


def test_input_mapping_from_raw_data():
    """build_ginzu_inputs should produce a valid GinzuInputs from raw data."""
    data = {
        "revenues_base": 1000.0,
        "ebit_reported_base": 200.0,
        "book_equity": 800.0,
        "book_debt": 400.0,
        "cash": 100.0,
        "shares_outstanding": 100.0,
        "stock_price": 150.0,
        "risk_free_rate": 0.045,
        "effective_tax_rate": 0.2,
        "marginal_tax_rate": 0.25,
        "cross_holdings": 0.0,
        "minority_interest": 0.0,
    }

    inputs = build_ginzu_inputs(data, assumptions={})

    assert isinstance(inputs, GinzuInputs)
    assert inputs.revenues_base == 1000.0
    assert inputs.ebit_reported_base == 200.0
    assert inputs.book_equity == 800.0
    assert inputs.book_debt == 400.0
    assert inputs.cash == 100.0
    assert inputs.stock_price == 150.0
    assert inputs.riskfree_rate_now == 0.045
    assert inputs.tax_rate_effective == 0.2
    assert inputs.tax_rate_marginal == 0.25


def test_assumptions_override_data():
    """User assumptions should take precedence over fetched data."""
    data = {
        "revenues_base": 1000.0,
        "ebit_reported_base": 200.0,
        "book_equity": 800.0,
        "book_debt": 400.0,
        "cash": 100.0,
        "shares_outstanding": 100.0,
        "stock_price": 150.0,
        "risk_free_rate": 0.045,
        "effective_tax_rate": 0.2,
        "marginal_tax_rate": 0.25,
    }

    assumptions = {
        "tax_rate_effective": 0.30,
        "wacc_initial": 0.10,
        "rev_growth_y1": 0.08,
    }

    inputs = build_ginzu_inputs(data, assumptions)

    # Assumption overrides data
    assert inputs.tax_rate_effective == 0.30
    assert inputs.wacc_initial == 0.10
    assert inputs.rev_growth_y1 == 0.08

    # Data still used where no assumption
    assert inputs.tax_rate_marginal == 0.25


def test_derived_defaults():
    """Current margin and sales-to-capital should be derived from data."""
    data = {
        "revenues_base": 1000.0,
        "ebit_reported_base": 200.0,
        "book_equity": 500.0,
        "book_debt": 300.0,
        "cash": 100.0,
        "shares_outstanding": 100.0,
        "stock_price": 50.0,
        "risk_free_rate": 0.04,
        "effective_tax_rate": 0.2,
        "marginal_tax_rate": 0.25,
    }

    inputs = build_ginzu_inputs(data)

    # current_margin = 200 / 1000 = 0.20
    assert inputs.margin_y1 == pytest.approx(0.20)
    assert inputs.margin_target == pytest.approx(0.20)

    # invested_capital = 500 + 300 - 100 = 700
    # sales_to_capital = 1000 / 700 ≈ 1.4286
    expected_stc = 1000.0 / 700.0
    assert inputs.sales_to_capital_1_5 == pytest.approx(expected_stc)
    assert inputs.sales_to_capital_6_10 == pytest.approx(expected_stc)
