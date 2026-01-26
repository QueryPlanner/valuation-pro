"""
Valuation Engine (CSV/XLSX independent)
======================================

This module contains the *pure* FCFF "Simple Ginzu" valuation engine:

- No CSV reading
- No XLSX reading
- No CLI / argparse

It is intentionally designed to be used by:
- a future SEC-data ingestion pipeline
- a future API layer (e.g. FastAPI) without any coupling to spreadsheets

API surface area (stable):
- `GinzuInputs` (all inputs required to value a company)
- `GinzuOutputs` (all computed outputs, including intermediate series)
- `compute_ginzu(inputs)`
- Optional: `compute_dilution_adjusted_black_scholes_option_value(...)` for employee options
"""

from __future__ import annotations

from dataclasses import dataclass
from math import erf, exp, log, sqrt
from typing import Iterable, List, Optional, Tuple


FORECAST_YEARS: int = 10
STABLE_TRANSITION_YEARS: int = 5


class InputError(ValueError):
    pass


@dataclass(frozen=True)
class RnDCapitalizationInputs:
    """
    Minimal, framework-agnostic representation of the R&D capitalization worksheet inputs.

    This is meant for your future SEC ingestion pipeline:
    you can feed historical R&D expenses directly, without any dependency on CSV/XLSX.
    """

    amortization_years: int
    current_year_rnd_expense: float
    past_year_rnd_expenses: List[float]


def compute_rnd_capitalization_adjustments(inputs: RnDCapitalizationInputs) -> Tuple[float, float]:
    """
    Compute the two values the FCFF engine needs when `capitalize_rnd=True`:

    Returns:
    - rnd_asset: "Value of Research Asset" (asset-like unamortized R&D)
    - rnd_ebit_adjustment: "Adjustment to Operating Income" (add to reported EBIT)

    This mirrors the logic of `R& D converter.csv`:
    - Amortization period = N years
    - Current year R&D = R0
    - Past years list is ordered [R(-1), R(-2), ..., R(-N)]
    - Research asset = R0 + sum_{k=1..N} R(-k) * (N-k)/N
    - Current-year amortization = sum_{k=1..N} R(-k) / N
    - EBIT adjustment = R0 - amortization
    """
    n = inputs.amortization_years
    if n <= 0:
        raise InputError("amortization_years must be > 0")
    if n > 10:
        # Matches the spreadsheet's guardrail.
        raise InputError("amortization_years must be <= 10")
    if inputs.current_year_rnd_expense < 0:
        raise InputError("current_year_rnd_expense must be >= 0")

    expected_past_years = n
    if len(inputs.past_year_rnd_expenses) != expected_past_years:
        raise InputError(
            "past_year_rnd_expenses length mismatch: "
            f"expected {expected_past_years} (for amortization_years={n}), got {len(inputs.past_year_rnd_expenses)}"
        )
    if any(x < 0 for x in inputs.past_year_rnd_expenses):
        raise InputError("past_year_rnd_expenses must all be >= 0")

    n_float = float(n)
    rnd_asset = float(inputs.current_year_rnd_expense)
    amortization_this_year = 0.0

    for k, expense in enumerate(inputs.past_year_rnd_expenses, start=1):
        # Asset: unamortized portion. For k=n, (n-n)/n = 0.
        unamortized_fraction = (n_float - float(k)) / n_float
        rnd_asset += float(expense) * unamortized_fraction
        
        # Amortization: straight line 1/n
        amortization_this_year += float(expense) / n_float

    rnd_ebit_adjustment = float(inputs.current_year_rnd_expense) - amortization_this_year
    return rnd_asset, rnd_ebit_adjustment


def normalize_to_float_list(values: Iterable[float]) -> List[float]:
    """
    Tiny helper for adapter layers: normalize iterables (numpy, pandas, etc.) to plain floats.

    Keep this in the engine so downstream adapters remain trivial and consistent.
    """
    return [float(v) for v in values]


def _norm_cdf(x: float) -> float:
    # Standard normal CDF via error function.
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))


@dataclass(frozen=True)
class OptionInputs:
    stock_price: float
    strike_price: float
    maturity_years: float
    volatility: float
    dividend_yield: float
    riskfree_rate: float
    options_outstanding: float
    shares_outstanding: float


def compute_dilution_adjusted_black_scholes_option_value(inputs: OptionInputs) -> float:
    """
    Mirrors Option value.csv:
    - Uses dilution-adjusted S (adjusted stock price) before applying Black–Scholes.
    - Uses standard normal CDF.
    - Assumes European option.
    """
    if inputs.options_outstanding <= 0:
        return 0.0
    if inputs.maturity_years <= 0:
        return 0.0
    if inputs.volatility <= 0:
        return 0.0
    if inputs.shares_outstanding <= 0:
        raise InputError("shares_outstanding must be > 0 for option valuation")

    # Option sheet uses:
    # adjusted_S = (S * shares + option_value_all * options) / (shares + options)
    # This is circular. Excel resolves it by iteration.
    #
    # For a deterministic implementation, use a stable fixed-point iteration with
    # a low, capped number of iterations. This matches the spreadsheet intent.
    max_iterations = 200
    tolerance = 1e-10

    shares = inputs.shares_outstanding
    warrants = inputs.options_outstanding

    adjusted_s = inputs.stock_price
    for _ in range(max_iterations):
        value_per_option = _black_scholes_call_value(
            stock_price=adjusted_s,
            strike_price=inputs.strike_price,
            maturity_years=inputs.maturity_years,
            volatility=inputs.volatility,
            riskfree_rate=inputs.riskfree_rate,
            dividend_yield=inputs.dividend_yield,
        )
        total_option_value = value_per_option * warrants
        next_adjusted_s = (inputs.stock_price * shares + total_option_value) / (shares + warrants)

        if abs(next_adjusted_s - adjusted_s) <= tolerance:
            adjusted_s = next_adjusted_s
            break
        adjusted_s = next_adjusted_s

    value_per_option = _black_scholes_call_value(
        stock_price=adjusted_s,
        strike_price=inputs.strike_price,
        maturity_years=inputs.maturity_years,
        volatility=inputs.volatility,
        riskfree_rate=inputs.riskfree_rate,
        dividend_yield=inputs.dividend_yield,
    )
    return value_per_option * warrants


def _black_scholes_call_value(
    *,
    stock_price: float,
    strike_price: float,
    maturity_years: float,
    volatility: float,
    riskfree_rate: float,
    dividend_yield: float,
) -> float:
    if stock_price <= 0 or strike_price <= 0:
        return 0.0
    if maturity_years <= 0 or volatility <= 0:
        return max(stock_price - strike_price, 0.0)

    variance = volatility**2
    dividend_adjusted_rate = riskfree_rate - dividend_yield
    time_sqrt = sqrt(maturity_years)

    d1 = (log(stock_price / strike_price) + (dividend_adjusted_rate + 0.5 * variance) * maturity_years) / (
        volatility * time_sqrt
    )
    d2 = d1 - volatility * time_sqrt

    nd1 = _norm_cdf(d1)
    nd2 = _norm_cdf(d2)

    pv_stock = exp(-dividend_yield * maturity_years) * stock_price
    pv_strike = exp(-riskfree_rate * maturity_years) * strike_price

    return pv_stock * nd1 - pv_strike * nd2


@dataclass(frozen=True)
class GinzuInputs:
    # Base-year raw numbers
    revenues_base: float
    ebit_reported_base: float
    book_equity: float
    book_debt: float
    cash: float
    non_operating_assets: float
    minority_interests: float
    shares_outstanding: float
    stock_price: float

    # Core levers
    rev_growth_y1: float
    rev_cagr_y2_5: float
    margin_y1: float
    margin_target: float
    margin_convergence_year: int
    sales_to_capital_1_5: float
    sales_to_capital_6_10: float
    riskfree_rate_now: float
    wacc_initial: float
    tax_rate_effective: float
    tax_rate_marginal: float

    # Switches / optional modules
    capitalize_rnd: bool = False
    capitalize_operating_leases: bool = False
    has_employee_options: bool = False

    # Overrides
    override_stable_wacc: bool = False
    stable_wacc: Optional[float] = None

    override_tax_rate_convergence: bool = False
    override_perpetual_growth: bool = False
    perpetual_growth_rate: Optional[float] = None

    override_riskfree_after_year10: bool = False
    riskfree_rate_after10: Optional[float] = None

    override_stable_roc: bool = False
    stable_roc: Optional[float] = None

    override_failure_probability: bool = False
    probability_of_failure: float = 0.0
    distress_proceeds_tie: str = "B"  # "B" or "V"
    distress_proceeds_percent: float = 0.0

    has_nol_carryforward: bool = False
    nol_start_year1: float = 0.0

    override_reinvestment_lag: bool = False
    reinvestment_lag_years: int = 1  # 0..3

    override_trapped_cash: bool = False
    trapped_cash_amount: float = 0.0
    trapped_cash_foreign_tax_rate: float = 0.0

    # Optional modules (pre-computed adjustment outputs)
    lease_debt: float = 0.0
    lease_ebit_adjustment: float = 0.0
    rnd_asset: float = 0.0
    rnd_ebit_adjustment: float = 0.0
    options_value: float = 0.0

    # Mature market ERP is used to compute stable WACC when not overridden.
    mature_market_erp: float = 0.0433


@dataclass(frozen=True)
class GinzuOutputs:
    revenues: List[float]  # length 11: base + years 1..10
    growth_rates: List[float]  # years 1..10
    margins: List[float]  # base + years 1..10
    ebit: List[float]  # base + years 1..10
    tax_rates: List[float]  # base + years 1..10
    nol: List[float]  # base + years 1..10
    ebit_after_tax: List[float]  # base + years 1..10 (EBIT(1-t) in sheet)
    reinvestment: List[float]  # years 1..10 and terminal
    fcff: List[float]  # years 1..10 and terminal
    wacc: List[float]  # years 1..10 and stable (terminal)
    discount_factors: List[float]  # years 1..10
    pv_fcff: List[float]  # years 1..10

    pv_10y: float
    terminal_cash_flow: float
    terminal_value: float
    pv_terminal_value: float
    pv_sum: float

    probability_of_failure: float
    proceeds_if_failure: float
    value_of_operating_assets: float

    debt: float
    cash_adjusted: float
    value_of_equity: float
    options_value: float
    value_of_equity_common: float
    estimated_value_per_share: float
    price_as_percent_of_value: float


def compute_ginzu(inputs: GinzuInputs) -> GinzuOutputs:
    _validate_inputs(inputs)

    stable_growth_rate = _compute_perpetual_growth_rate(inputs)
    stable_tax_rate = _compute_terminal_tax_rate(inputs)
    stable_wacc = _compute_stable_wacc(inputs)

    base_ebit = inputs.ebit_reported_base + _compute_base_ebit_adjustments(inputs)

    growth_rates = _compute_growth_rates(
        year1_growth=inputs.rev_growth_y1,
        years2_5_growth=inputs.rev_cagr_y2_5,
        stable_growth_rate=stable_growth_rate,
        forecast_years=FORECAST_YEARS,
    )
    revenues = _compute_revenues(inputs.revenues_base, growth_rates)

    margins = _compute_margins(
        base_ebit=base_ebit,
        base_revenues=inputs.revenues_base,
        year1_margin=inputs.margin_y1,
        target_margin=inputs.margin_target,
        convergence_year=inputs.margin_convergence_year,
        forecast_years=FORECAST_YEARS,
    )
    ebit = _compute_ebit(revenues, margins, base_ebit)

    tax_rates, terminal_tax_rate = _compute_tax_rates(
        base_tax_rate=inputs.tax_rate_effective,
        terminal_tax_rate=stable_tax_rate,
        forecast_years=FORECAST_YEARS,
        transition_years=STABLE_TRANSITION_YEARS,
    )

    nol, ebit_after_tax = _compute_ebit_after_tax_with_nol(
        ebit=ebit,
        tax_rates=tax_rates,
        nol_start_year1=inputs.nol_start_year1 if inputs.has_nol_carryforward else 0.0,
    )

    sales_to_capital = _compute_sales_to_capital_series(
        years1_5=inputs.sales_to_capital_1_5,
        years6_10=inputs.sales_to_capital_6_10,
        forecast_years=FORECAST_YEARS,
    )

    reinvestment_years_1_10 = _compute_reinvestment(
        revenues=revenues,
        growth_rates=growth_rates,
        sales_to_capital=sales_to_capital,
        override_reinvestment_lag=inputs.override_reinvestment_lag,
        reinvestment_lag_years=inputs.reinvestment_lag_years,
        stable_growth_rate=stable_growth_rate,
    )

    # Terminal-year (Year 11) values:
    revenue_terminal = revenues[10] * (1.0 + stable_growth_rate)
    margin_terminal = margins[10]  # terminal margin equals year 10 margin in the sheet
    ebit_terminal = revenue_terminal * margin_terminal
    ebit_after_tax_terminal = ebit_terminal * (1.0 - terminal_tax_rate)

    stable_roc = _compute_stable_roc(inputs, wacc_year10=None, stable_wacc=stable_wacc)
    wacc_series, wacc_terminal = _compute_wacc_series(
        wacc_initial=inputs.wacc_initial,
        wacc_stable=stable_wacc,
        forecast_years=FORECAST_YEARS,
        transition_years=STABLE_TRANSITION_YEARS,
    )

    # Stable ROC default depends on Year 10 WACC in the spreadsheet, so we fill it after.
    if not inputs.override_stable_roc:
        stable_roc = wacc_series[9]  # year 10 WACC (0-based index, year10 is position 9)

    reinvestment_terminal = _compute_terminal_reinvestment(
        stable_growth_rate=stable_growth_rate,
        stable_roc=stable_roc,
        ebit_after_tax_terminal=ebit_after_tax_terminal,
    )

    reinvestment = reinvestment_years_1_10 + [reinvestment_terminal]

    fcff_years_1_10 = [ebit_after_tax[t] - reinvestment_years_1_10[t - 1] for t in range(1, 11)]
    fcff_terminal = ebit_after_tax_terminal - reinvestment_terminal
    fcff = fcff_years_1_10 + [fcff_terminal]

    discount_factors = _compute_discount_factors(wacc_series)
    pv_fcff = [fcff_years_1_10[i] * discount_factors[i] for i in range(FORECAST_YEARS)]
    pv_10y = sum(pv_fcff)

    terminal_value = _compute_terminal_value(
        terminal_cash_flow=fcff_terminal,
        stable_wacc=wacc_terminal,
        stable_growth_rate=stable_growth_rate,
    )
    pv_terminal_value = terminal_value * discount_factors[-1]
    pv_sum = pv_10y + pv_terminal_value

    probability_of_failure = inputs.probability_of_failure if inputs.override_failure_probability else 0.0
    proceeds_if_failure = _compute_proceeds_if_failure(
        proceeds_tie=inputs.distress_proceeds_tie,
        book_equity=inputs.book_equity,
        book_debt=inputs.book_debt,
        pv_sum_pre_failure=pv_sum,
        distress_proceeds_percent=inputs.distress_proceeds_percent,
    )
    value_of_operating_assets = pv_sum * (1.0 - probability_of_failure) + proceeds_if_failure * probability_of_failure

    debt = inputs.book_debt + (inputs.lease_debt if inputs.capitalize_operating_leases else 0.0)
    cash_adjusted = _compute_cash_adjusted_for_trapped_cash(inputs)

    value_of_equity = (
        value_of_operating_assets
        - debt
        - inputs.minority_interests
        + cash_adjusted
        + inputs.non_operating_assets
    )

    options_value = inputs.options_value if inputs.has_employee_options else 0.0
    value_of_equity_common = value_of_equity - options_value

    estimated_value_per_share = value_of_equity_common / inputs.shares_outstanding
    price_as_percent_of_value = inputs.stock_price / estimated_value_per_share

    return GinzuOutputs(
        revenues=revenues,
        growth_rates=growth_rates,
        margins=margins,
        ebit=ebit,
        tax_rates=tax_rates,
        nol=nol,
        ebit_after_tax=ebit_after_tax,
        reinvestment=reinvestment,
        fcff=fcff,
        wacc=wacc_series + [wacc_terminal],
        discount_factors=discount_factors,
        pv_fcff=pv_fcff,
        pv_10y=pv_10y,
        terminal_cash_flow=fcff_terminal,
        terminal_value=terminal_value,
        pv_terminal_value=pv_terminal_value,
        pv_sum=pv_sum,
        probability_of_failure=probability_of_failure,
        proceeds_if_failure=proceeds_if_failure,
        value_of_operating_assets=value_of_operating_assets,
        debt=debt,
        cash_adjusted=cash_adjusted,
        value_of_equity=value_of_equity,
        options_value=options_value,
        value_of_equity_common=value_of_equity_common,
        estimated_value_per_share=estimated_value_per_share,
        price_as_percent_of_value=price_as_percent_of_value,
    )


def _validate_inputs(inputs: GinzuInputs) -> None:
    if inputs.revenues_base <= 0:
        raise InputError("revenues_base must be > 0")
    if inputs.shares_outstanding <= 0:
        raise InputError("shares_outstanding must be > 0")
    if inputs.margin_convergence_year <= 0:
        raise InputError("margin_convergence_year must be > 0")
    if inputs.sales_to_capital_1_5 <= 0 or inputs.sales_to_capital_6_10 <= 0:
        raise InputError("sales_to_capital ratios must be > 0")
    if inputs.override_reinvestment_lag and inputs.reinvestment_lag_years not in {0, 1, 2, 3}:
        raise InputError("reinvestment_lag_years must be one of {0,1,2,3}")
    if inputs.override_failure_probability and not (0.0 <= inputs.probability_of_failure <= 1.0):
        raise InputError("probability_of_failure must be between 0 and 1")
    if inputs.distress_proceeds_tie not in {"B", "V"}:
        raise InputError("distress_proceeds_tie must be 'B' or 'V'")
    if inputs.override_perpetual_growth and inputs.perpetual_growth_rate is None:
        raise InputError("override_perpetual_growth requires perpetual_growth_rate")
    if inputs.override_riskfree_after_year10 and inputs.riskfree_rate_after10 is None:
        raise InputError("override_riskfree_after_year10 requires riskfree_rate_after10")
    if inputs.override_stable_wacc and inputs.stable_wacc is None:
        raise InputError("override_stable_wacc requires stable_wacc")
    if inputs.override_stable_roc and inputs.stable_roc is None:
        raise InputError("override_stable_roc requires stable_roc")

    if inputs.capitalize_operating_leases:
        if inputs.lease_debt < 0:
            raise InputError("lease_debt must be >= 0")
    if inputs.capitalize_rnd:
        # Allow zero values, but make it explicit when the flag is on.
        if inputs.rnd_asset < 0:
            raise InputError("rnd_asset must be >= 0")
    if inputs.has_employee_options:
        if inputs.options_value < 0:
            raise InputError("options_value must be >= 0")


def _compute_perpetual_growth_rate(inputs: GinzuInputs) -> float:
    if inputs.override_perpetual_growth and inputs.perpetual_growth_rate is not None:
        return inputs.perpetual_growth_rate
    if inputs.override_riskfree_after_year10 and inputs.riskfree_rate_after10 is not None:
        return inputs.riskfree_rate_after10
    return inputs.riskfree_rate_now


def _compute_terminal_tax_rate(inputs: GinzuInputs) -> float:
    if inputs.override_tax_rate_convergence:
        return inputs.tax_rate_effective
    return inputs.tax_rate_marginal


def _compute_stable_wacc(inputs: GinzuInputs) -> float:
    if inputs.override_stable_wacc and inputs.stable_wacc is not None:
        return inputs.stable_wacc

    if inputs.override_riskfree_after_year10 and inputs.riskfree_rate_after10 is not None:
        riskfree = inputs.riskfree_rate_after10
    else:
        riskfree = inputs.riskfree_rate_now
    return float(riskfree) + inputs.mature_market_erp


def _compute_stable_roc(inputs: GinzuInputs, *, wacc_year10: Optional[float], stable_wacc: float) -> float:
    if inputs.override_stable_roc and inputs.stable_roc is not None:
        return inputs.stable_roc
    if wacc_year10 is not None:
        return wacc_year10
    # Will be filled later once wacc_year10 is known.
    return stable_wacc


def _compute_base_ebit_adjustments(inputs: GinzuInputs) -> float:
    lease_adj = inputs.lease_ebit_adjustment if inputs.capitalize_operating_leases else 0.0
    rnd_adj = inputs.rnd_ebit_adjustment if inputs.capitalize_rnd else 0.0
    return lease_adj + rnd_adj


def _compute_growth_rates(
    *,
    year1_growth: float,
    years2_5_growth: float,
    stable_growth_rate: float,
    forecast_years: int,
) -> List[float]:
    if forecast_years != 10:
        raise InputError("This implementation expects forecast_years=10 (spreadsheet parity)")

    g = [0.0] * forecast_years
    g[0] = year1_growth
    for i in range(1, 5):
        g[i] = years2_5_growth

    year5_growth = g[4]
    decrement = (year5_growth - stable_growth_rate) / STABLE_TRANSITION_YEARS
    for i in range(5, 10):
        step = i - 4  # year6 is step 1
        g[i] = year5_growth - decrement * step
    return g


def _compute_revenues(base_revenue: float, growth_rates: List[float]) -> List[float]:
    revenues = [base_revenue]
    current = base_revenue
    for g in growth_rates:
        current = current * (1.0 + g)
        revenues.append(current)
    # revenues length = 11 (base + years 1..10)
    return revenues


def _compute_margins(
    *,
    base_ebit: float,
    base_revenues: float,
    year1_margin: float,
    target_margin: float,
    convergence_year: int,
    forecast_years: int,
) -> List[float]:
    base_margin = base_ebit / base_revenues
    margins: List[float] = [base_margin]
    margins.append(year1_margin)

    start_margin = year1_margin
    for year in range(2, forecast_years + 1):
        if year > convergence_year:
            margins.append(target_margin)
            continue

        slope = (target_margin - start_margin) / float(convergence_year)
        year_margin = target_margin - slope * float(convergence_year - year)
        margins.append(year_margin)

    return margins  # length 11


def _compute_ebit(revenues: List[float], margins: List[float], base_ebit: float) -> List[float]:
    ebit: List[float] = [base_ebit]
    for year in range(1, 11):
        ebit.append(revenues[year] * margins[year])
    return ebit


def _compute_tax_rates(
    *,
    base_tax_rate: float,
    terminal_tax_rate: float,
    forecast_years: int,
    transition_years: int,
) -> Tuple[List[float], float]:
    tax_rates: List[float] = [base_tax_rate]
    # Years 1..5 use base tax rate.
    for _ in range(1, 6):
        tax_rates.append(base_tax_rate)

    year5_tax_rate = base_tax_rate
    step = (terminal_tax_rate - year5_tax_rate) / float(transition_years)
    # Years 6..10
    for k in range(1, 6):
        tax_rates.append(year5_tax_rate + step * k)

    if len(tax_rates) != forecast_years + 1:
        raise InputError("Internal error: tax rate series length mismatch")
    return tax_rates, terminal_tax_rate


def _compute_ebit_after_tax_with_nol(
    *,
    ebit: List[float],
    tax_rates: List[float],
    nol_start_year1: float,
) -> Tuple[List[float], List[float]]:
    """
    Mirrors rows 7 and 10 in Valuation output.csv.

    Returns:
    - nol series: length 11 (base + years 1..10)
    - ebit_after_tax: length 11 (base + years 1..10)
    """
    nol: List[float] = [nol_start_year1]
    ebit_after_tax: List[float] = []

    # Base-year EBIT(1-t): only applies tax if EBIT > 0.
    base_ebit = ebit[0]
    base_tax_rate = tax_rates[0]
    base_after_tax = base_ebit * (1.0 - base_tax_rate) if base_ebit > 0 else base_ebit
    ebit_after_tax.append(base_after_tax)

    current_nol = nol_start_year1
    for year in range(1, 11):
        year_ebit = ebit[year]
        year_tax = tax_rates[year]

        if year_ebit <= 0:
            ebit_after_tax.append(year_ebit)
            current_nol = current_nol - year_ebit  # subtracting a negative increases NOL
            nol.append(current_nol)
            continue

        if year_ebit < current_nol:
            ebit_after_tax.append(year_ebit)
            current_nol = current_nol - year_ebit
            nol.append(current_nol)
            continue

        taxable_income = year_ebit - current_nol
        taxes = taxable_income * year_tax
        ebit_after_tax.append(year_ebit - taxes)
        current_nol = 0.0
        nol.append(current_nol)

    return nol, ebit_after_tax


def _compute_sales_to_capital_series(*, years1_5: float, years6_10: float, forecast_years: int) -> List[float]:
    series: List[float] = []
    for year in range(1, forecast_years + 1):
        if year <= 5:
            series.append(years1_5)
        else:
            series.append(years6_10)
    return series


def _compute_reinvestment(
    *,
    revenues: List[float],
    growth_rates: List[float],
    sales_to_capital: List[float],
    override_reinvestment_lag: bool,
    reinvestment_lag_years: int,
    stable_growth_rate: float,
) -> List[float]:
    """
    Mirrors row 8 in Valuation output.csv (years 1..10).

    Default (override_reinvestment_lag == False): one-year lag.
    """
    _ = growth_rates  # kept for parity with spreadsheet naming; deltas come from revenue series
    lag = reinvestment_lag_years if override_reinvestment_lag else 1

    def revenue_delta_for_year(year: int) -> float:
        """
        year is 1..10. Spreadsheet uses different revenue deltas depending on lag.
        For boundary years where future revenues beyond year 10 are required, Excel
        extrapolates using stable growth rate g.
        """
        left_index = year + lag - 1
        right_index = year + lag

        max_known_index = len(revenues) - 1

        def revenue_at(index: int) -> float:
            if index <= max_known_index:
                return revenues[index]
            steps_beyond = index - max_known_index
            return revenues[max_known_index] * (1.0 + stable_growth_rate) ** steps_beyond

        return revenue_at(right_index) - revenue_at(left_index)

    reinvestment: List[float] = []
    for year in range(1, 11):
        delta = revenue_delta_for_year(year)
        ratio = sales_to_capital[year - 1]
        reinvestment.append(delta / ratio)

    return reinvestment


def _compute_wacc_series(
    *,
    wacc_initial: float,
    wacc_stable: float,
    forecast_years: int,
    transition_years: int,
) -> Tuple[List[float], float]:
    # Years 1..5
    wacc = [wacc_initial] * 5
    year5 = wacc_initial
    step = (year5 - wacc_stable) / float(transition_years)
    for k in range(1, 6):
        wacc.append(year5 - step * k)
    if len(wacc) != forecast_years:
        raise InputError("Internal error: wacc series length mismatch")
    return wacc, wacc_stable


def _compute_discount_factors(wacc_years_1_10: List[float]) -> List[float]:
    discount_factors: List[float] = []
    cumulative = 1.0
    for i, year_wacc in enumerate(wacc_years_1_10):
        if i == 0:
            cumulative = 1.0 / (1.0 + year_wacc)
        else:
            cumulative = cumulative / (1.0 + year_wacc)
        discount_factors.append(cumulative)
    return discount_factors


def _compute_terminal_reinvestment(*, stable_growth_rate: float, stable_roc: float, ebit_after_tax_terminal: float) -> float:
    if stable_growth_rate <= 0:
        return 0.0
    if stable_roc <= 0:
        raise InputError("stable_roc must be > 0 when stable_growth_rate > 0")
    return (stable_growth_rate / stable_roc) * ebit_after_tax_terminal


def _compute_terminal_value(*, terminal_cash_flow: float, stable_wacc: float, stable_growth_rate: float) -> float:
    denominator = stable_wacc - stable_growth_rate
    if denominator <= 0:
        raise InputError("stable_wacc must be > stable_growth_rate for terminal value")
    return terminal_cash_flow / denominator


def _compute_proceeds_if_failure(
    *,
    proceeds_tie: str,
    book_equity: float,
    book_debt: float,
    pv_sum_pre_failure: float,
    distress_proceeds_percent: float,
) -> float:
    if distress_proceeds_percent <= 0:
        return 0.0
    if proceeds_tie == "B":
        return (book_equity + book_debt) * distress_proceeds_percent
    if proceeds_tie == "V":
        return pv_sum_pre_failure * distress_proceeds_percent
    raise InputError(f"Unknown proceeds_tie: {proceeds_tie!r}")


def _compute_cash_adjusted_for_trapped_cash(inputs: GinzuInputs) -> float:
    if not inputs.override_trapped_cash:
        return inputs.cash
    additional_tax = inputs.trapped_cash_amount * (inputs.tax_rate_marginal - inputs.trapped_cash_foreign_tax_rate)
    return inputs.cash - additional_tax


