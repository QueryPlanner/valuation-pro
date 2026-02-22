"""
Tests for the inputs_builder module.

Covers: default heuristics, assumption overrides, edge cases,
zero-division safeguards, and input mapping.
"""

import pytest

from valuation_engine import GinzuInputs, InputError, build_ginzu_inputs, compute_ginzu

# ---------------------------------------------------------------------------
# Input mapping from raw data
# ---------------------------------------------------------------------------

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

    assert inputs.tax_rate_effective == 0.30
    assert inputs.wacc_initial == 0.10
    assert inputs.rev_growth_y1 == 0.08
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


# ---------------------------------------------------------------------------
# Default assumptions and edge-case heuristics
# ---------------------------------------------------------------------------

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
        "effective_tax_rate": 0.0,
        "marginal_tax_rate": 0.25,
    }

    inputs = build_ginzu_inputs(data, assumptions={})

    assert isinstance(inputs, GinzuInputs)
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


# ---------------------------------------------------------------------------
# Zero-division safeguards
# ---------------------------------------------------------------------------

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
    with pytest.raises(InputError, match="revenues_base must be > 0"):
        compute_ginzu(inputs)
