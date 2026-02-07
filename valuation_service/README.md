# Valuation Service

This module provides a FastAPI-based REST API for the **Valuation Engine**, allowing users to fetch financial data and calculate company valuations programmatically.

> **Note**: This project now uses [uv](https://github.com/astral-sh/uv) for fast, reliable Python package management with lock file support.

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

This project uses [uv](https://github.com/astral-sh/uv) for fast, reliable Python package management.

If you don't have uv installed:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Installation

Install dependencies using uv:
```bash
cd valuation_service
uv sync
```

This creates a virtual environment at `.venv` and installs all dependencies with lock file support via `uv.lock`.

### Running the API

#### Option 1: Using the run script (recommended)
```bash
./run.sh
```

#### Option 2: Manual with PYTHONPATH
```bash
export PYTHONPATH="$(pwd)/..:$PYTHONPATH"
uv run uvicorn valuation_service.main:app --reload
```

#### Option 3: Activate venv manually
```bash
source .venv/bin/activate
export PYTHONPATH="$(pwd)/..:$PYTHONPATH"
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

Run the test suite using uv:
```bash
export PYTHONPATH="$(pwd)/..:$PYTHONPATH"
uv run pytest tests/
```

To check coverage:
```bash
export PYTHONPATH="$(pwd)/..:$PYTHONPATH"
uv run pytest --cov=valuation_service tests/
```

Note: The PYTHONPATH export is required so tests can import the `valuation_engine` module from the parent directory.

## Development

### Adding Dependencies

Add a new dependency:
```bash
uv add <package-name>
```

Add a dev dependency:
```bash
uv add --dev <package-name>
```

### Updating Dependencies

Update all dependencies:
```bash
uv sync --upgrade
```

### Lock File

The `uv.lock` file ensures reproducible installs across environments. Commit this file to version control.
