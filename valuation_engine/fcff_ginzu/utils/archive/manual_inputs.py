"""
Project-local valuation inputs (NO CSV/XLSX required).

Edit this file to plug in new company data and assumptions.
This is *not* required to use `valuation_engine.py` directly; it is only a convenience.
"""

from __future__ import annotations

from valuation_engine.fcff_ginzu import GinzuInputs


# ---------------------------------------------------------------------------
# Single source of truth for a manual run.
# Replace the values below with your company’s data/assumptions.
# ---------------------------------------------------------------------------

GINZU_INPUTS = GinzuInputs(
    # -----------------------------------------------------------------------
    # Base-year raw numbers (keep currency units consistent everywhere)
    # -----------------------------------------------------------------------
    revenues_base=46465.0,
    ebit_reported_base=13815.0,
    book_equity=25853.0,
    book_debt=45063.0,
    cash=19000.0,
    non_operating_assets=21119.0,
    minority_interests=1558.0,
    shares_outstanding=4315.0,
    stock_price=72.28,
    # -----------------------------------------------------------------------
    # Value drivers
    # -----------------------------------------------------------------------
    rev_growth_y1=0.05,
    rev_cagr_y2_5=0.05,
    margin_y1=13815.0 / 46465.0,  # current margin
    margin_target=13815.0 / 46465.0,  # stay flat by default
    margin_convergence_year=5,
    # In the spreadsheet template, these are often set from global industry averages.
    sales_to_capital_1_5=1.7731795673077668,
    sales_to_capital_6_10=1.7731795673077668,
    riskfree_rate_now=0.0458,
    # Initial WACC used for years 1-5 in the valuation.
    # If you want parity with a specific spreadsheet run, use the same precision.
    wacc_initial=0.0731766923949557,
    tax_rate_effective=0.175,
    tax_rate_marginal=0.25,
    # -----------------------------------------------------------------------
    # Switches / overrides (leave off unless you’re explicitly using them)
    # -----------------------------------------------------------------------
    # --------------------
    # R&D capitalization
    # --------------------
    # If True, you MUST also provide:
    # - rnd_asset: the "Value of Research Asset" from the R&D converter worksheet
    # - rnd_ebit_adjustment: the "Adjustment to Operating Income" from the same worksheet
    capitalize_rnd=False,
    rnd_asset=0.0,
    rnd_ebit_adjustment=0.0,
    # --------------------
    # Operating lease capitalization
    # --------------------
    # If True, you MUST also provide:
    # - lease_debt: PV of operating lease commitments (debt equivalent)
    # - lease_ebit_adjustment: adjustment to EBIT from converting operating leases
    capitalize_operating_leases=False,
    lease_debt=0.0,
    lease_ebit_adjustment=0.0,
    # --------------------
    # Employee options
    # --------------------
    # If True, you MUST also provide:
    # - options_value: total value of employee options (to subtract from equity)
    has_employee_options=False,
    options_value=0.0,
    # Overrides (examples; leave False unless using)
    override_stable_wacc=False,
    override_tax_rate_convergence=False,
    override_perpetual_growth=False,
    override_riskfree_after_year10=False,
    override_stable_roc=False,
    override_failure_probability=False,
    has_nol_carryforward=False,
    override_reinvestment_lag=False,
    override_trapped_cash=False,
    # Mature-market ERP used only when stable WACC is not overridden.
    mature_market_erp=0.0433,
)


