"""
Pydantic request/response schemas for the Valuation API.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class ValuationRequest(BaseModel):
    """Request body for the valuation calculation endpoint."""

    ticker: str = Field(..., description="Stock ticker symbol (e.g., AAPL)")
    source: str = Field("yahoo", description="Data source connector")
    as_of_date: Optional[str] = Field(None, description="Optional historical date (YYYY-MM-DD) for retrospective testing")
    assumptions: Optional[Dict[str, Any]] = Field(None, description="Optional overrides for valuation assumptions")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ticker": "AAPL",
                "source": "yahoo",
                "as_of_date": "2024-02-05",
                "assumptions": {
                    "wacc_initial": 0.085,
                    "tax_rate_effective": 0.21,
                    "rev_growth_y1": 0.05,
                },
            }
        }
    )
