from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from typing import Dict, Any, Optional
import logging
from valuation_service.connectors import ConnectorFactory
from valuation_service.service import ValuationService
from valuation_service.utils import sanitize_for_json

logger = logging.getLogger(__name__)
router = APIRouter()

class ValuationRequest(BaseModel):
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
                    "rev_growth_y1": 0.05
                }
            }
        }
    )

@router.get(
    "/data/financials/{ticker}",
    summary="Get Financial Statements",
    description="Fetches raw income statement, balance sheet, and cash flow data from the selected source.",
    response_description="Dictionary containing financial statements keyed by date."
)
def get_financials(ticker: str, source: str = Query("yahoo", description="Data source connector")):
    try:
        connector = ConnectorFactory.get_connector(source)
        data = connector.get_financials(ticker)
        return sanitize_for_json(data)
    except ValueError as e:
        logger.warning(f"Bad Request for {ticker}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Internal Error fetching financials for {ticker}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get(
    "/data/market/{ticker}",
    summary="Get Market Data",
    description="Fetches current market data including price, beta, market cap, and risk-free rate.",
    response_description="Dictionary containing market metrics."
)
def get_market_data(ticker: str, source: str = Query("yahoo", description="Data source connector")):
    try:
        connector = ConnectorFactory.get_connector(source)
        data = connector.get_market_data(ticker)
        return sanitize_for_json(data)
    except ValueError as e:
        logger.warning(f"Bad Request for {ticker}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Internal Error fetching market data for {ticker}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.post(
    "/valuation/calculate",
    summary="Calculate Valuation",
    description="Performs a full FCFF valuation. Accepts optional assumption overrides.",
    response_description="Detailed valuation outputs including per-share value and intermediate calculations."
)
def calculate_valuation(request: ValuationRequest):
    try:
        connector = ConnectorFactory.get_connector(request.source)
        service = ValuationService(connector)
        
        result = service.calculate_valuation(request.ticker, request.assumptions)
        return sanitize_for_json(result)
    except ValueError as e:
        logger.warning(f"Bad Request for {request.ticker}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Internal Error valuing {request.ticker}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
