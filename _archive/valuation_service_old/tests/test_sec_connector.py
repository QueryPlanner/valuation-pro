import pytest

from valuation_service.connectors import ConnectorFactory, SECConnector


def test_sec_connector_registered():
    connector = ConnectorFactory.get_connector("sec")
    assert isinstance(connector, SECConnector)

def test_sec_connector_not_implemented():
    connector = ConnectorFactory.get_connector("sec")

    with pytest.raises(NotImplementedError):
        connector.get_financials("AAPL")

    with pytest.raises(NotImplementedError):
        connector.get_market_data("AAPL")
