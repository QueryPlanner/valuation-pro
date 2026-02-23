import logging

from fastapi.testclient import TestClient
from valuation_service.main import app

client = TestClient(app)

def test_logging_middleware(caplog):
    """Test that requests are logged."""
    with caplog.at_level(logging.INFO):
        client.get("/")

    found_log = False
    for record in caplog.records:
        # We look for our specific log format
        if "Incoming request: GET /" in record.message:
            found_log = True
            break

    assert found_log, "Request was not logged by middleware"
