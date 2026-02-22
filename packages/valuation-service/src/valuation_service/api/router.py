"""
API Router — all endpoint definitions for the valuation service.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from valuation_service.api.schemas import ValuationRequest
from valuation_service.connectors import ConnectorFactory
from valuation_service.services.valuation import ValuationService
from valuation_service.utils.json import sanitize_for_json

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/data/financials/{ticker}",
    summary="Get Financial Statements",
    description="Fetches raw income statement, balance sheet, and cash flow data from the selected source.",
    response_description="Dictionary containing financial statements keyed by date.",
)
def get_financials(ticker: str, source: str = Query("yahoo", description="Data source connector"), as_of_date: Optional[str] = Query(None, description="Optional historical date (YYYY-MM-DD)")):
    try:
        connector = ConnectorFactory.get_connector(source)
        data = connector.get_financials(ticker, as_of_date=as_of_date)
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
    response_description="Dictionary containing market metrics.",
)
def get_market_data(ticker: str, source: str = Query("yahoo", description="Data source connector"), as_of_date: Optional[str] = Query(None, description="Optional historical date (YYYY-MM-DD)")):
    try:
        connector = ConnectorFactory.get_connector(source)
        data = connector.get_market_data(ticker, as_of_date=as_of_date)
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
    response_description="Detailed valuation outputs including per-share value and intermediate calculations.",
)
def calculate_valuation(request: ValuationRequest):
    try:
        connector = ConnectorFactory.get_connector(request.source)
        service = ValuationService(connector)

        assumptions_dict = request.assumptions.model_dump(exclude_unset=True) if request.assumptions else None
        result = service.calculate_valuation(request.ticker, assumptions_dict, request.as_of_date)
        return sanitize_for_json(result)
    except ValueError as e:
        logger.warning(f"Bad Request for {request.ticker}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Internal Error valuing {request.ticker}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
