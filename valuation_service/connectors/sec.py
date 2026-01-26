from typing import Dict, Any
from .base import BaseConnector, ConnectorFactory

class SECConnector(BaseConnector):
    """Placeholder for SEC EDGAR connector."""

    def get_financials(self, ticker: str) -> Dict[str, Any]:
        """Fetch financial statements from SEC."""
        # Future implementation will go here
        raise NotImplementedError("SEC Connector is not yet implemented.")

    def get_market_data(self, ticker: str) -> Dict[str, Any]:
        """Fetch market data from SEC (or linked source)."""
        # Future implementation will go here
        raise NotImplementedError("SEC Connector is not yet implemented.")

# Register the connector
ConnectorFactory.register("sec", SECConnector)
