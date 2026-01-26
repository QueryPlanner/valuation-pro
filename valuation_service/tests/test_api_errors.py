from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from valuation_service.main import app

client = TestClient(app)

def test_api_validation_error():
    with patch("valuation_service.api.endpoints.ConnectorFactory.get_connector") as mock_factory:
        mock_factory.side_effect = ValueError("Invalid Source")
        
        response = client.get("/data/financials/AAPL?source=bad")
        assert response.status_code == 400
        assert "Invalid Source" in response.json()["detail"]

        response = client.get("/data/market/AAPL?source=bad")
        assert response.status_code == 400
        
        response = client.post("/valuation/calculate", json={"ticker": "AAPL", "source": "bad"})
        assert response.status_code == 400

def test_api_internal_error():
    with patch("valuation_service.api.endpoints.ConnectorFactory.get_connector") as mock_factory:
        mock_factory.side_effect = Exception("Boom")
        
        response = client.get("/data/financials/AAPL")
        assert response.status_code == 500
        
        response = client.get("/data/market/AAPL")
        assert response.status_code == 500
        
        response = client.post("/valuation/calculate", json={"ticker": "AAPL"})
        assert response.status_code == 500
