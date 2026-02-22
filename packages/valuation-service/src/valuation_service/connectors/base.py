from abc import ABC, abstractmethod
from typing import Any, Dict, Type


class BaseConnector(ABC):
    """Abstract base class for data connectors."""

    @abstractmethod
    def get_financials(self, ticker: str) -> Dict[str, Any]:
        """Fetch financial statements (Income, Balance Sheet, Cash Flow)."""
        pass

    @abstractmethod
    def get_market_data(self, ticker: str) -> Dict[str, Any]:
        """Fetch market data (Price, Beta, Risk Free Rate, etc.)."""
        pass

    @abstractmethod
    def get_valuation_inputs(self, ticker: str) -> Dict[str, Any]:
        """
        Fetch and normalize data specifically for the Valuation Engine.
        Returns a dictionary containing keys like:
        - revenues_base (LTM)
        - ebit_reported_base (LTM)
        - book_equity (MRQ)
        - book_debt (MRQ)
        - rnd_expense (LTM)
        - rnd_history (List[float])
        """
        pass


class ConnectorFactory:
    """Simple factory to manage data connectors (Singleton Pattern)."""

    _connector_classes: Dict[str, Type[BaseConnector]] = {}
    _instances: Dict[str, BaseConnector] = {}

    @classmethod
    def register(cls, name: str, connector_cls: Type[BaseConnector]) -> None:
        cls._connector_classes[name] = connector_cls

    @classmethod
    def get_connector(cls, name: str) -> BaseConnector:
        # Check cache first
        if name in cls._instances:
            return cls._instances[name]

        # Create new instance if registered
        connector_cls = cls._connector_classes.get(name)
        if not connector_cls:
            raise ValueError(f"Connector '{name}' not found.")

        instance = connector_cls()
        cls._instances[name] = instance
        return instance
