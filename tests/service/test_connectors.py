"""
Tests for connectors: factory, singleton, base interface, SEC placeholder.
"""

from typing import Any, Dict

import pytest

from valuation_service.connectors import BaseConnector, ConnectorFactory, SECConnector

# ---------------------------------------------------------------------------
# BaseConnector interface
# ---------------------------------------------------------------------------

class MockConnector(BaseConnector):
    def get_financials(self, ticker: str) -> Dict[str, Any]:
        return {"mock": "financials"}

    def get_market_data(self, ticker: str) -> Dict[str, Any]:
        return {"mock": "market"}

    def get_valuation_inputs(self, ticker: str) -> Dict[str, Any]:
        return {"mock": "valuation_inputs"}


def test_connector_interface():
    """Ensure BaseConnector enforces implementation."""
    with pytest.raises(TypeError):

        class IncompleteConnector(BaseConnector):
            pass

        IncompleteConnector()


def test_factory_registration():
    ConnectorFactory.register("mock", MockConnector)
    connector = ConnectorFactory.get_connector("mock")
    assert isinstance(connector, MockConnector)
    assert connector.get_financials("AAPL") == {"mock": "financials"}


def test_factory_invalid_connector():
    with pytest.raises(ValueError):
        ConnectorFactory.get_connector("non_existent")


# ---------------------------------------------------------------------------
# Singleton pattern
# ---------------------------------------------------------------------------

class MockStatefulConnector(BaseConnector):
    def __init__(self):
        self.call_count = 0

    def get_financials(self, ticker: str) -> Dict[str, Any]:
        self.call_count += 1
        return {}

    def get_market_data(self, ticker: str) -> Dict[str, Any]:
        return {}

    def get_valuation_inputs(self, ticker: str) -> Dict[str, Any]:
        return {}


def test_connector_singleton_pattern():
    ConnectorFactory.register("stateful_mock", MockStatefulConnector)

    conn1 = ConnectorFactory.get_connector("stateful_mock")
    conn1.get_financials("AAPL")
    assert conn1.call_count == 1

    conn2 = ConnectorFactory.get_connector("stateful_mock")
    assert conn1 is conn2

    conn2.get_financials("AAPL")
    assert conn1.call_count == 2
    assert conn2.call_count == 2


# ---------------------------------------------------------------------------
# SEC connector placeholder
# ---------------------------------------------------------------------------

def test_sec_connector_registered():
    connector = ConnectorFactory.get_connector("sec")
    assert isinstance(connector, SECConnector)


def test_sec_connector_not_implemented():
    connector = ConnectorFactory.get_connector("sec")

    with pytest.raises(NotImplementedError):
        connector.get_financials("AAPL")

    with pytest.raises(NotImplementedError):
        connector.get_market_data("AAPL")
