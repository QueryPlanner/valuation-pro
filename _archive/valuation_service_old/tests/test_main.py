from fastapi.testclient import TestClient
from valuation_service.main import app

client = TestClient(app)

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
