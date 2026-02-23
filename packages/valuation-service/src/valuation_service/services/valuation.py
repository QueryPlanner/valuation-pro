"""
Valuation Service
=================

Thin orchestration layer: fetch data via a Connector, prepare inputs via
the shared ``build_ginzu_inputs`` builder, run the engine, and return results.

All input-preparation and computation logic lives in **valuation_engine** so
there is exactly one source of truth.
"""

import logging
from typing import Any, Dict, Optional

from valuation_engine import build_ginzu_inputs, compute_ginzu
from valuation_service.connectors.base import BaseConnector

logger = logging.getLogger(__name__)


class ValuationService:
    def __init__(self, connector: BaseConnector):
        self.connector = connector

    def calculate_valuation(
        self,
        ticker: str,
        assumptions: Optional[Dict[str, Any]] = None,
        as_of_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Orchestrates the valuation process.

        1. Fetch normalized data from the Connector.
        2. Prepare GinzuInputs via the shared builder.
        3. Run the engine.
        4. Return results as a dict (API-friendly).
        """
        # 1. Fetch normalized inputs from Connector
        data = self.connector.get_valuation_inputs(ticker, as_of_date=as_of_date)

        # 2. Build GinzuInputs via canonical builder (single source of truth)
        inputs = build_ginzu_inputs(data, assumptions)

        # 3. Run Engine
        outputs = compute_ginzu(inputs)

        # 4. Return results (Dict for API)
        return outputs.__dict__
