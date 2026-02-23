from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ValuationAssumptions(BaseModel):
    """Optional overrides for valuation assumptions and base financials."""

    # R&D Capitalization
    capitalize_rnd: Optional[bool] = Field(None, description="Whether to capitalize R&D expenses")
    rnd_amortization_years: Optional[int] = Field(None, description="Amortization period for R&D")
    rnd_expense: Optional[float] = Field(None, description="Current year R&D expense")
    rnd_history: Optional[List[float]] = Field(None, description="Historical R&D expenses (newest to oldest)")

    # Base Financials Overrides
    revenues_base: Optional[float] = Field(None, description="Base year revenues")
    ebit_reported_base: Optional[float] = Field(None, description="Base year reported EBIT")
    book_equity: Optional[float] = Field(None, description="Book value of equity")
    book_debt: Optional[float] = Field(None, description="Book value of debt")
    cash: Optional[float] = Field(None, description="Cash and marketable securities")
    non_operating_assets: Optional[float] = Field(None, description="Cross holdings and other non-operating assets")
    minority_interests: Optional[float] = Field(None, description="Minority interests")

    # Core Levers
    rev_growth_y1: Optional[float] = Field(None, description="Revenue growth rate for next year")
    rev_cagr_y2_5: Optional[float] = Field(None, description="Compounded annual revenue growth rate for years 2-5")
    margin_y1: Optional[float] = Field(None, description="Operating margin for next year")
    margin_target: Optional[float] = Field(None, description="Target pre-tax operating margin")
    margin_convergence_year: Optional[int] = Field(None, description="Year of convergence for margin")
    sales_to_capital_1_5: Optional[float] = Field(None, description="Sales to capital ratio for years 1-5")
    sales_to_capital_6_10: Optional[float] = Field(None, description="Sales to capital ratio for years 6-10")

    # Rates & Taxes
    riskfree_rate_now: Optional[float] = Field(None, description="Current risk-free rate")
    wacc_initial: Optional[float] = Field(None, description="Initial cost of capital (WACC)")
    tax_rate_effective: Optional[float] = Field(None, description="Effective tax rate")
    tax_rate_marginal: Optional[float] = Field(None, description="Marginal tax rate")
    mature_market_erp: Optional[float] = Field(None, description="Mature market equity risk premium")

    # Leases
    capitalize_operating_leases: Optional[bool] = Field(None, description="Whether to capitalize operating leases")
    lease_debt: Optional[float] = Field(None, description="Lease debt value")
    lease_ebit_adjustment: Optional[float] = Field(None, description="Lease EBIT adjustment")

    # Employee Options
    has_employee_options: Optional[bool] = Field(None, description="Whether the firm has employee options outstanding")
    options_value: Optional[float] = Field(None, description="Pre-computed value of options")
    options_strike_price: Optional[float] = Field(None, description="Average strike price of options")
    options_maturity_years: Optional[float] = Field(None, description="Average maturity of options")
    options_volatility: Optional[float] = Field(None, description="Standard deviation on stock price")
    options_dividend_yield: Optional[float] = Field(None, description="Dividend yield for options pricing")
    options_outstanding: Optional[float] = Field(None, description="Number of options outstanding")

    # Advanced / Terminal Assumptions
    override_stable_wacc: Optional[bool] = Field(None, description="Override default stable WACC assumption")
    stable_wacc: Optional[float] = Field(None, description="Cost of capital after year 10")
    override_perpetual_growth: Optional[bool] = Field(None, description="Override default perpetual growth rate")
    perpetual_growth_rate: Optional[float] = Field(None, description="Growth rate in perpetuity")
    override_tax_rate_convergence: Optional[bool] = Field(None, description="Override default tax rate convergence")
    override_riskfree_after_year10: Optional[bool] = Field(None, description="Override risk-free rate after year 10")
    riskfree_rate_after10: Optional[float] = Field(None, description="Risk-free rate after year 10")
    override_stable_roc: Optional[bool] = Field(None, description="Override stable Return on Capital assumption")
    stable_roc: Optional[float] = Field(None, description="Expected return on capital after year 10")

    # Failure / Distress
    override_failure_probability: Optional[bool] = Field(None, description="Override failure probability")
    probability_of_failure: Optional[float] = Field(None, description="Probability of failure")
    distress_proceeds_tie: Optional[str] = Field(None, description="Tie distress proceeds to 'B' (Book) or 'V' (Value)")
    distress_proceeds_percent: Optional[float] = Field(None, description="Distress proceeds as percent of book/value")

    # NOL & Reinvestment
    has_nol_carryforward: Optional[bool] = Field(None, description="Has Net Operating Loss carryforward")
    nol_start_year1: Optional[float] = Field(None, description="NOL carried over into year 1")
    override_reinvestment_lag: Optional[bool] = Field(None, description="Override reinvestment lag")
    reinvestment_lag_years: Optional[int] = Field(None, description="Reinvestment lag years (0-3)")

    # Trapped Cash
    override_trapped_cash: Optional[bool] = Field(None, description="Override trapped cash assumptions")
    trapped_cash_amount: Optional[float] = Field(None, description="Amount of trapped cash")
    trapped_cash_foreign_tax_rate: Optional[float] = Field(None, description="Foreign tax rate on trapped cash")

    model_config = ConfigDict(extra="allow")


class ValuationRequest(BaseModel):
    """Request body for the valuation calculation endpoint."""

    ticker: str = Field(..., description="Stock ticker symbol (e.g., AAPL)")
    source: str = Field("yahoo", description="Data source connector")
    as_of_date: Optional[str] = Field(
        None, description="Optional historical date (YYYY-MM-DD) for retrospective testing"
    )
    assumptions: Optional[ValuationAssumptions] = Field(
        None, description="Optional overrides for valuation assumptions"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ticker": "AMZN",
                "source": "yahoo",
                "as_of_date": "2024-02-05",
                "assumptions": {
                    "rev_growth_y1": 0.12,
                    "rev_cagr_y2_5": 0.12,
                    "tax_rate_effective": 0.19,
                    "tax_rate_marginal": 0.25,
                    "wacc_initial": 0.086,
                    "margin_target": 0.14,
                    "sales_to_capital_1_5": 1.5,
                    "sales_to_capital_6_10": 1.5,
                    "mature_market_erp": 0.0411,
                },
            }
        }
    )

class CompanyItem(BaseModel):
    symbol: Optional[str] = None
    shortname: Optional[str] = None
    longname: Optional[str] = None
    exchange: Optional[str] = None
    quoteType: Optional[str] = None

class CompanySearchResponse(BaseModel):
    results: List[CompanyItem]
