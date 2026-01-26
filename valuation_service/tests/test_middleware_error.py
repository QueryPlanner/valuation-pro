from fastapi.testclient import TestClient
from valuation_service.main import app
from unittest.mock import patch

client = TestClient(app)

def test_middleware_internal_error():
    # Force an endpoint to raise an unhandled exception
    # We can patch the root endpoint for this test
    with patch("valuation_service.main.read_root") as mock_root:
        mock_root.side_effect = Exception("Catastrophic Failure")
        
        # We need to re-import or somehow force the app to use the patched function if it's already bound?
        # Actually, standard patching might not work on already decorated route functions.
        # Better approach: Add a temporary route that raises exception.
        
        # But we can't easily modify 'app' in a test without side effects.
        # Instead, let's patch the router handler or the service inside an existing route.
        pass

    # Let's try patching ConnectorFactory in a way that endpoints don't catch?
    # endpoints catch Exception -> 500.
    # Middleware catches Exception -> 500.
    # So if endpoints catch it, middleware sees a normal response (500).
    
    # We need something that runs BEFORE endpoints or a route NOT in endpoints.py?
    # Ah, the middleware wraps EVERYTHING.
    # If endpoints.py catches exceptions, middleware sees a valid Response object (status 500).
    # So middleware's "except Exception" block is ONLY hit if something outside endpoints (or a bug in endpoints exception handler) occurs.
    
    # Or if a middleware BEFORE it crashes?
    
    # Let's try to verify if endpoints.py catches everything.
    # Endpoints.py has `except Exception`. So it never bubbles up to middleware?
    # Wait, `read_root` in `main.py` does NOT have try/except.
    
    with patch("valuation_service.main.app.router.routes") as routes:
        # Modifying routes is hard.
        pass

    # Let's just create a new app instance with the middleware for this test?
    from fastapi import FastAPI, Request
    from valuation_service.main import log_requests
    
    test_app = FastAPI()
    test_app.middleware("http")(log_requests)
    
    @test_app.get("/error")
    def error_route():
        raise RuntimeError("Middleware specific crash")
        
    test_client = TestClient(test_app)
    response = test_client.get("/error")
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal Server Error"}
