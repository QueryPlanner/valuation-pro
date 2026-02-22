# Valuation Service

This module provides a FastAPI-based REST API for the **Valuation Engine**, allowing users to fetch financial data and calculate company valuations programmatically.

## Overview

The `valuation_service` bridges the gap between raw data sources (like Yahoo Finance) and the core mathematical logic in `valuation_engine`. It handles:
1.  **Data Ingestion:** Fetching raw financial statements and market data via modular connectors.
2.  **Data Mapping:** Normalizing external data structures into the strict `GinzuInputs` format required by the engine.
3.  **Valuation Execution:** Running the `fcff_ginzu` model with user-provided assumptions or intelligent defaults.

## Project Structure

-   `api/`: Contains the FastAPI router and endpoint definitions (`endpoints.py`).
-   `connectors/`: Implements the "Simple Factory" pattern for data sources.
    -   `base.py`: Abstract base class defining the connector interface.
    -   `yahoo.py`: Concrete implementation using `yfinance`.
    -   `sec.py`: Placeholder for future SEC EDGAR integration.
-   `tests/`: Comprehensive unit and integration tests ensuring 98%+ code coverage.
-   `service.py`: Domain logic orchestration (Data -> Map -> Engine -> Result).
-   `main.py`: Application entry point and middleware configuration.

## Getting Started

### Prerequisites
Ensure you have the dependencies installed:
```bash
pip install -r requirements.txt
```

### Running the API
Start the server using `uvicorn`:
```bash
uvicorn valuation_service.main:app --reload
```
The API will be available at `http://127.0.0.1:8000`.

### Documentation
Interactive API documentation (Swagger UI) is automatically generated at:
-   `http://127.0.0.1:8000/docs`

## Key Endpoints

### Data Retrieval
-   `GET /data/financials/{ticker}`: Returns raw Income Statement, Balance Sheet, and Cash Flow data.
-   `GET /data/market/{ticker}`: Returns current Price, Beta, Market Cap, and Risk-Free Rate.

### Valuation
-   `POST /valuation/calculate`: Performs a full valuation.
    -   **Body:** JSON object containing `ticker` and optional `assumptions`.
    -   **Example:**
        ```json
        {
          "ticker": "AAPL",
          "source": "yahoo",
          "assumptions": {
            "rev_growth_y1": 0.05,
            "margin_target": 0.25
          }
        }
        ```

## Testing

Run the test suite using `pytest`:
```bash
pytest valuation_service/tests/
```
To check coverage:
```bash
pytest --cov=valuation_service valuation_service/tests/
```
