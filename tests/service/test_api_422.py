from fastapi.testclient import TestClient
from valuation_service.app import app

client = TestClient(app)

def test_api_422():
    response = client.post("/valuation/calculate", json={"wrong_key": "AAPL"})
    assert response.status_code == 422
