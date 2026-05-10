from pydantic import BaseModel, Field


class ValuationAssumptions(BaseModel):
    revenues_base: float = Field(..., description="Revenues from the most recent twelve months. TTM.")
    ebit_reported_base: float = Field(..., description="Operating income or EBIT from the most recent 12 months.")
    book_equity: float = Field(..., description="Book value of equity from the end of the most recent 12 months.")
    book_debt: float = Field(..., description="Book value of interest bearing debt (short and long term).")
    cash: float = Field(..., description="Cash and marketable securities.")
    non_operating_assets: float = Field(..., description="Cross holdings and other non-operating assets.")
    minority_interests: float = Field(..., description="Minority interest.")
    shares_outstanding: float = Field(..., description="Number of shares outstanding.")

    rev_growth_y1: float = Field(..., description="Revenue growth for next year. Derived from recent growth.")
    rev_cagr_y2_5: float = Field(
        ..., description="Revenue CAGR for years 2-5. Should mean-revert towards the risk-free rate."
    )

    margin_y1: float = Field(..., description="Operating margin for next year.")
    margin_target: float = Field(..., description="Target operating margin.")
    margin_convergence_year: int = Field(..., description="Year to converge to target margin (usually 5).")

    sales_to_capital_1_5: float = Field(..., description="Sales to capital ratio for years 1-5.")
    sales_to_capital_6_10: float = Field(..., description="Sales to capital ratio for years 6-10.")

    tax_rate_effective: float = Field(..., description="Effective tax rate.")
    tax_rate_marginal: float = Field(..., description="Marginal tax rate (usually 30% for India).")

    rationale: str = Field(..., description="A comprehensive explanation of how each value was calculated or derived.")
