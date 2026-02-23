"""
Inputs Builder
==============

Canonical logic for preparing ``GinzuInputs`` from a raw data dictionary
(typically returned by a Connector) and a user-supplied assumptions dictionary.

This module is the **single source of truth** for:
- Deriving default heuristics (current margin, invested capital, sales/capital)
- R&D capitalization pre-computation (delegates to engine helper)
- Employee-options Black–Scholes pre-computation (delegates to engine helper)
- Merging user assumptions with fetched data

Both ``valuation_service`` and direct engine callers (CLI, notebooks, tests)
should use ``build_ginzu_inputs()`` to ensure identical input preparation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from .engine import (
    GinzuInputs,
    OptionInputs,
    RnDCapitalizationInputs,
    compute_dilution_adjusted_black_scholes_option_value,
    compute_rnd_capitalization_adjustments,
)

logger = logging.getLogger(__name__)

# Canonical defaults — keep in one place so they never drift.
DEFAULT_MATURE_MARKET_ERP = 0.0460
DEFAULT_RISK_FREE_RATE = 0.04
DEFAULT_WACC_INITIAL = 0.08
DEFAULT_EFFECTIVE_TAX_RATE = 0.20
DEFAULT_MARGINAL_TAX_RATE = 0.25
DEFAULT_REV_GROWTH = 0.05
DEFAULT_MARGIN_CONVERGENCE_YEAR = 5
DEFAULT_SALES_TO_CAPITAL_FALLBACK = 1.5


def build_ginzu_inputs(
    data: Dict[str, Any],
    assumptions: Dict[str, Any] | None = None,
) -> GinzuInputs:
    """
    Merge fetched data with user assumptions and apply default heuristics.

    Handles complex pre-computation logic:
    - R&D Capitalization (via engine helper)
    - Employee Options / Black-Scholes (via engine helper)
    - Invested capital / sales-to-capital ratio
    - Margin derivation from adjusted EBIT

    Every field of ``GinzuInputs`` is explicitly mapped here so that
    the output is identical regardless of call-site (service, CLI, test).

    Parameters
    ----------
    data : dict
        Normalized financial data, typically from a Connector's
        ``get_valuation_inputs()`` method.  Expected keys include
        ``revenues_base``, ``ebit_reported_base``, ``book_equity``,
        ``book_debt``, ``cash``, ``shares_outstanding``, ``stock_price``,
        ``effective_tax_rate``, ``marginal_tax_rate``, ``risk_free_rate``,
        ``cross_holdings``, ``minority_interest``, etc.
    assumptions : dict, optional
        User-supplied overrides.  Any key present here takes precedence
        over the corresponding value in *data*.

    Returns
    -------
    GinzuInputs
        Fully-populated dataclass ready to pass to ``compute_ginzu()``.
    """
    if assumptions is None:
        assumptions = {}

    # Helper: pick Assumption > Data > Default
    def get_val(assumption_key: str, data_key: str, default: Any) -> Any:
        if assumption_key in assumptions:
            return assumptions[assumption_key]
        if data_key in data:
            return data[data_key]
        return default

    # ------------------------------------------------------------------ #
    # 1. R&D Capitalization
    # ------------------------------------------------------------------ #
    rnd_history = assumptions.get("rnd_history", data.get("rnd_history", []))
    current_rnd = get_val("rnd_expense", "rnd_expense", 0.0)

    capitalize_rnd = assumptions.get("capitalize_rnd", False)

    rnd_asset = 0.0
    rnd_ebit_adj = 0.0

    if capitalize_rnd:
        try:
            amort_years = assumptions.get("rnd_amortization_years", 5)
            past_rnd = []
            for i in range(amort_years):
                val = rnd_history[i + 1] if (i + 1) < len(rnd_history) else 0.0
                past_rnd.append(float(val))

            rnd_inputs = RnDCapitalizationInputs(
                amortization_years=amort_years,
                current_year_rnd_expense=float(current_rnd),
                past_year_rnd_expenses=past_rnd,
            )
            rnd_asset, rnd_ebit_adj = compute_rnd_capitalization_adjustments(rnd_inputs)
        except Exception as e:
            logger.warning(f"R&D Capitalization failed: {e}")
            capitalize_rnd = False

    # ------------------------------------------------------------------ #
    # 2. Base Financials
    # ------------------------------------------------------------------ #
    revenues = get_val("revenues_base", "revenues_base", 0.0)
    ebit = get_val("ebit_reported_base", "ebit_reported_base", 0.0)

    book_equity = get_val("book_equity", "book_equity", 0.0)
    book_debt = get_val("book_debt", "book_debt", 0.0)
    cash = get_val("cash", "cash", 0.0)

    # Adjust Book Equity for R&D if capitalized
    if capitalize_rnd:
        book_equity += rnd_asset

    # Invested Capital for Sales/Capital ratio
    invested_capital = book_equity + book_debt - cash

    sales_to_capital_actual = DEFAULT_SALES_TO_CAPITAL_FALLBACK
    if invested_capital > 0 and revenues > 0:
        sales_to_capital_actual = revenues / invested_capital

    # Margins — if capitalizing R&D, use adjusted EBIT
    base_ebit_adj = ebit + rnd_ebit_adj if capitalize_rnd else ebit
    current_margin = base_ebit_adj / revenues if revenues > 0 else 0.10

    # ------------------------------------------------------------------ #
    # 3. Employee Options (Black-Scholes)
    # ------------------------------------------------------------------ #
    has_employee_options = assumptions.get("has_employee_options", False)
    options_value = 0.0

    if has_employee_options:
        if "options_value" in assumptions:
            # User pre-computed the value
            options_value = assumptions["options_value"]
        else:
            # Compute via engine's dilution-adjusted Black-Scholes
            try:
                option_inputs = OptionInputs(
                    stock_price=get_val("stock_price", "stock_price", 0.0),
                    strike_price=assumptions.get("options_strike_price", 0.0),
                    maturity_years=assumptions.get("options_maturity_years", 0.0),
                    volatility=assumptions.get("options_volatility", 0.0),
                    dividend_yield=assumptions.get("options_dividend_yield", 0.0),
                    riskfree_rate=get_val("riskfree_rate_now", "risk_free_rate", DEFAULT_RISK_FREE_RATE),
                    options_outstanding=assumptions.get("options_outstanding", 0.0),
                    shares_outstanding=get_val("shares_outstanding", "shares_outstanding", 1.0),
                )
                options_value = compute_dilution_adjusted_black_scholes_option_value(option_inputs)
            except Exception as e:
                logger.warning(f"Employee Options valuation failed: {e}")
                options_value = 0.0

    # ------------------------------------------------------------------ #
    # 4. Risk-free rate & perpetual growth
    # ------------------------------------------------------------------ #
    risk_free = data.get("risk_free_rate", DEFAULT_RISK_FREE_RATE)

    override_perpetual_growth = assumptions.get("override_perpetual_growth", True)
    perpetual_growth_rate = assumptions.get("perpetual_growth_rate", risk_free)

    override_riskfree_after_year10 = assumptions.get("override_riskfree_after_year10", False)
    riskfree_rate_after10 = assumptions.get("riskfree_rate_after10", None)

    # ------------------------------------------------------------------ #
    # 5. Leases
    # ------------------------------------------------------------------ #
    capitalize_operating_leases = assumptions.get("capitalize_operating_leases", False)
    lease_debt = assumptions.get("lease_debt", 0.0)
    lease_ebit_adjustment = assumptions.get("lease_ebit_adjustment", 0.0)

    # If capitalizing leases from data (e.g., connector provides it)
    if capitalize_operating_leases and "lease_debt" not in assumptions:
        lease_debt = data.get("operating_leases_liability", 0.0)

    # ------------------------------------------------------------------ #
    # 6. Build GinzuInputs — every field explicitly mapped
    # ------------------------------------------------------------------ #
    return GinzuInputs(
        # Base-year raw numbers
        revenues_base=revenues,
        ebit_reported_base=ebit,
        book_equity=book_equity,
        book_debt=book_debt,
        cash=cash,
        non_operating_assets=get_val("non_operating_assets", "cross_holdings", 0.0),
        minority_interests=get_val("minority_interests", "minority_interest", 0.0),
        shares_outstanding=get_val("shares_outstanding", "shares_outstanding", 1.0),
        stock_price=get_val("stock_price", "stock_price", 0.0),
        # Core levers
        rev_growth_y1=assumptions.get("rev_growth_y1", DEFAULT_REV_GROWTH),
        rev_cagr_y2_5=assumptions.get("rev_cagr_y2_5", DEFAULT_REV_GROWTH),
        margin_y1=assumptions.get("margin_y1", current_margin),
        margin_target=assumptions.get("margin_target", current_margin),
        margin_convergence_year=assumptions.get("margin_convergence_year", DEFAULT_MARGIN_CONVERGENCE_YEAR),
        sales_to_capital_1_5=assumptions.get("sales_to_capital_1_5", sales_to_capital_actual),
        sales_to_capital_6_10=assumptions.get("sales_to_capital_6_10", sales_to_capital_actual),
        riskfree_rate_now=assumptions["riskfree_rate_now"] if "riskfree_rate_now" in assumptions else risk_free,
        wacc_initial=assumptions.get("wacc_initial", DEFAULT_WACC_INITIAL),
        tax_rate_effective=get_val("tax_rate_effective", "effective_tax_rate", DEFAULT_EFFECTIVE_TAX_RATE),
        tax_rate_marginal=get_val("tax_rate_marginal", "marginal_tax_rate", DEFAULT_MARGINAL_TAX_RATE),
        # R&D
        capitalize_rnd=capitalize_rnd,
        rnd_asset=rnd_asset,
        rnd_ebit_adjustment=rnd_ebit_adj,
        # Leases
        capitalize_operating_leases=capitalize_operating_leases,
        lease_debt=lease_debt,
        lease_ebit_adjustment=lease_ebit_adjustment,
        # Employee Options
        has_employee_options=has_employee_options,
        options_value=options_value,
        # Stable WACC
        override_stable_wacc=assumptions.get("override_stable_wacc", False),
        stable_wacc=assumptions.get("stable_wacc", None),
        mature_market_erp=assumptions.get("mature_market_erp", DEFAULT_MATURE_MARKET_ERP),
        # Perpetual Growth
        override_perpetual_growth=override_perpetual_growth,
        perpetual_growth_rate=perpetual_growth_rate,
        # Tax Rate Convergence
        override_tax_rate_convergence=assumptions.get("override_tax_rate_convergence", False),
        # Risk-free after Year 10
        override_riskfree_after_year10=override_riskfree_after_year10,
        riskfree_rate_after10=riskfree_rate_after10,
        # Stable ROC
        override_stable_roc=assumptions.get("override_stable_roc", False),
        stable_roc=assumptions.get("stable_roc", None),
        # Failure Probability / Distress
        override_failure_probability=assumptions.get("override_failure_probability", False),
        probability_of_failure=assumptions.get("probability_of_failure", 0.0),
        distress_proceeds_tie=assumptions.get("distress_proceeds_tie", "B"),
        distress_proceeds_percent=assumptions.get("distress_proceeds_percent", 0.0),
        # NOL Carryforward
        has_nol_carryforward=assumptions.get("has_nol_carryforward", False),
        nol_start_year1=assumptions.get("nol_start_year1", 0.0),
        # Reinvestment Lag
        override_reinvestment_lag=assumptions.get("override_reinvestment_lag", False),
        reinvestment_lag_years=assumptions.get("reinvestment_lag_years", 1),
        # Trapped Cash
        override_trapped_cash=assumptions.get("override_trapped_cash", False),
        trapped_cash_amount=assumptions.get("trapped_cash_amount", 0.0),
        trapped_cash_foreign_tax_rate=assumptions.get("trapped_cash_foreign_tax_rate", 0.0),
    )
