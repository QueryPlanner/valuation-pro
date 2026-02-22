"""
Tests for the FastAPI application — root, middleware, error handling, JSON compliance.
"""

import logging
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from valuation_service.app import app, create_app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Root & basic endpoints
# ---------------------------------------------------------------------------


def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Valuation Engine API is running"}


def test_404():
    response = client.get("/non-existent")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_docs():
    response = client.get("/docs")
    assert response.status_code == 200


def test_openapi():
    response = client.get("/openapi.json")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Logging middleware
# ---------------------------------------------------------------------------


def test_logging_middleware(caplog):
    """Test that requests are logged."""
    with caplog.at_level(logging.INFO):
        client.get("/")

    found_log = False
    for record in caplog.records:
        if "Incoming request: GET /" in record.message:
            found_log = True
            break

    assert found_log, "Request was not logged by middleware"


# ---------------------------------------------------------------------------
# API endpoint mocking
# ---------------------------------------------------------------------------


def test_get_financials():
    mock_data = {
        "income_statement": {"2023": {"Revenue": 100}},
        "balance_sheet": {},
        "cash_flow": {},
    }

    with patch("valuation_service.api.router.ConnectorFactory.get_connector") as mock_factory:
        mock_connector = MagicMock()
        mock_connector.get_financials.return_value = mock_data
        mock_factory.return_value = mock_connector

        response = client.get("/data/financials/AAPL")
        assert response.status_code == 200
        assert response.json() == mock_data


def test_get_market_data():
    mock_data = {"price": 150.0}

    with patch("valuation_service.api.router.ConnectorFactory.get_connector") as mock_factory:
        mock_connector = MagicMock()
        mock_connector.get_market_data.return_value = mock_data
        mock_factory.return_value = mock_connector

        response = client.get("/data/market/AAPL")
        assert response.status_code == 200
        assert response.json() == mock_data


def test_data_connector_override():
    with patch("valuation_service.api.router.ConnectorFactory.get_connector") as mock_factory:
        mock_connector = MagicMock()
        mock_connector.get_market_data.return_value = {"mock": "sec"}
        mock_factory.return_value = mock_connector

        response = client.get("/data/market/AAPL?source=sec")
        assert response.status_code == 200
        mock_factory.assert_called_with("sec")


def test_calculate_valuation():
    mock_result = {
        "value_of_equity": 1000.0,
        "estimated_value_per_share": 100.0,
    }

    with patch("valuation_service.api.router.ValuationService") as MockService:
        instance = MockService.return_value
        instance.calculate_valuation.return_value = mock_result

        response = client.post("/valuation/calculate", json={"ticker": "AAPL"})
        assert response.status_code == 200
        assert response.json() == mock_result
        instance.calculate_valuation.assert_called_with("AAPL", None)

        assumptions = {"wacc_initial": 0.09}
        response = client.post("/valuation/calculate", json={"ticker": "AAPL", "assumptions": assumptions})
        assert response.status_code == 200
        instance.calculate_valuation.assert_called_with("AAPL", assumptions)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_api_validation_error():
    with patch("valuation_service.api.router.ConnectorFactory.get_connector") as mock_factory:
        mock_factory.side_effect = ValueError("Invalid Source")

        response = client.get("/data/financials/AAPL?source=bad")
        assert response.status_code == 400
        assert "Invalid Source" in response.json()["detail"]

        response = client.get("/data/market/AAPL?source=bad")
        assert response.status_code == 400

        response = client.post("/valuation/calculate", json={"ticker": "AAPL", "source": "bad"})
        assert response.status_code == 400


def test_api_internal_error():
    with patch("valuation_service.api.router.ConnectorFactory.get_connector") as mock_factory:
        mock_factory.side_effect = Exception("Boom")

        response = client.get("/data/financials/AAPL")
        assert response.status_code == 500

        response = client.get("/data/market/AAPL")
        assert response.status_code == 500

        response = client.post("/valuation/calculate", json={"ticker": "AAPL"})
        assert response.status_code == 500


def test_middleware_internal_error():
    """Middleware should catch unhandled exceptions from routes without try/except."""

    test_app = create_app()

    @test_app.get("/error")
    def error_route():
        raise RuntimeError("Middleware specific crash")

    test_client = TestClient(test_app)
    response = test_client.get("/error")
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal Server Error"}


# ---------------------------------------------------------------------------
# JSON compliance (NaN / Infinity sanitization)
# ---------------------------------------------------------------------------


def test_get_financials_with_nan_and_inf():
    mock_data = {
        "income_statement": {
            "2023": {
                "Revenue": 100.0,
                "Growth": float("nan"),
                "Margin": float("inf"),
                "Loss": float("-inf"),
            }
        }
    }

    with patch("valuation_service.api.router.ConnectorFactory.get_connector") as mock_factory:
        mock_connector = MagicMock()
        mock_connector.get_financials.return_value = mock_data
        mock_factory.return_value = mock_connector

        response = client.get("/data/financials/NAN_TEST")

        assert response.status_code == 200
        data = response.json()
        assert data["income_statement"]["2023"]["Growth"] is None
        assert data["income_statement"]["2023"]["Margin"] is None
        assert data["income_statement"]["2023"]["Loss"] is None
