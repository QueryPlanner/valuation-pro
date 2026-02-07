from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from valuation_service.main import app

client = TestClient(app)

def test_get_financials():
    mock_data = {
        "income_statement": {"2023": {"Revenue": 100}},
        "balance_sheet": {},
        "cash_flow": {}
    }
    
    with patch("valuation_service.api.endpoints.ConnectorFactory.get_connector") as mock_factory:
        mock_connector = MagicMock()
        mock_connector.get_financials.return_value = mock_data
        mock_factory.return_value = mock_connector
        
        response = client.get("/data/financials/AAPL")
        assert response.status_code == 200
        assert response.json() == mock_data

def test_get_market_data():
    mock_data = {"price": 150.0}
    
    with patch("valuation_service.api.endpoints.ConnectorFactory.get_connector") as mock_factory:
        mock_connector = MagicMock()
        mock_connector.get_market_data.return_value = mock_data
        mock_factory.return_value = mock_connector
        
        response = client.get("/data/market/AAPL")
        assert response.status_code == 200
        assert response.json() == mock_data

def test_data_connector_override():
    with patch("valuation_service.api.endpoints.ConnectorFactory.get_connector") as mock_factory:
        mock_connector = MagicMock()
        mock_connector.get_market_data.return_value = {"mock": "sec"}
        mock_factory.return_value = mock_connector
        
        response = client.get("/data/market/AAPL?source=sec")
        assert response.status_code == 200
        mock_factory.assert_called_with("sec")

def test_calculate_valuation():
    mock_result = {
        "value_of_equity": 1000.0,
        "estimated_value_per_share": 100.0
    }
    
    # We need to patch the ValuationService
    with patch("valuation_service.api.endpoints.ValuationService") as MockService:
        instance = MockService.return_value
        instance.calculate_valuation.return_value = mock_result
        
        # Test basic request
        response = client.post("/valuation/calculate", json={"ticker": "AAPL"})
        assert response.status_code == 200
        assert response.json() == mock_result
        instance.calculate_valuation.assert_called_with("AAPL", None, None)
        
        # Test with assumptions
        assumptions = {"wacc_initial": 0.09}
        response = client.post("/valuation/calculate", json={"ticker": "AAPL", "assumptions": assumptions})
        assert response.status_code == 200
        instance.calculate_valuation.assert_called_with("AAPL", assumptions, None)