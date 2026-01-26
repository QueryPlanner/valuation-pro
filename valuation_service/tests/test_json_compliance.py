from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from valuation_service.main import app
import math

client = TestClient(app)

def test_get_financials_with_nan_and_inf():
    # Mock data containing NaN and Infinity
    mock_data = {
        "income_statement": {
            "2023": {
                "Revenue": 100.0,
                "Growth": float('nan'),
                "Margin": float('inf'),
                "Loss": float('-inf')
            }
        }
    }
    
    with patch("valuation_service.api.endpoints.ConnectorFactory.get_connector") as mock_factory:
        mock_connector = MagicMock()
        mock_connector.get_financials.return_value = mock_data
        mock_factory.return_value = mock_connector
        
        # Attempt to fetch the data
        # If the bug exists, this might raise a ValueError during serialization 
        # which FastAPI/Starlette catches and converts to 500, or it might just crash.
        try:
            response = client.get("/data/financials/NAN_TEST")
        except ValueError as e:
            # If the test client catches the serialization error directly (depends on test client implementation)
            # We fail the test effectively by re-raising or handling.
            # But usually TestClient returns the 500 response.
            print(f"Caught expected serialization error: {e}")
            raise

        # We EXPECT this to succeed with 200 OK and sanitized data (nulls)
        # So this assertion should FAIL in the Red phase.
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}. Body: {response.text}"
        
        data = response.json()
        # JSON spec doesn't support NaN/Inf, typically mapped to null
        assert data["income_statement"]["2023"]["Growth"] is None
        assert data["income_statement"]["2023"]["Margin"] is None
        assert data["income_statement"]["2023"]["Loss"] is None
