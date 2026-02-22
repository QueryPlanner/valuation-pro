"""
Pydantic request/response schemas for the Valuation API.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict


class ValuationRequest(BaseModel):
    """Request body for the valuation calculation endpoint."""

    ticker: str
    source: str = "yahoo"
    assumptions: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ticker": "AAPL",
                "source": "yahoo",
                "assumptions": {
                    "wacc_initial": 0.085,
                    "tax_rate_effective": 0.21,
                    "rev_growth_y1": 0.05,
                },
            }
        }
    )
