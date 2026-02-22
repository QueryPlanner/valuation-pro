## What
Enhance API schemas with expanded valuation assumptions and add retrospective historical data fetching.

## Why
To enable fetching historical financial data using an `as_of_date` parameter and to improve the flexibility of the valuation engine through explicit assumption overrides in the API, ensuring alignment with reference Excel models.

## How
- Added `as_of_date` parameter to all data endpoints for retrospective fetches
- Updated `ValuationRequest` schema to explicitly document overrides
- Added missing historical data support for the Yahoo Finance (YF) connector
- Improved inputs builder assumption overrides to support engine parity
- Formatted and linted codebase via `ruff`
- Verified AMZN Excel parity with retrospective support

## Tests
- [x] Verified AMZN Excel parity
- [x] Tested retrospective data fetching via `test_yahoo_connector.py`
- [x] Tested API schemas and responses via `test_api.py` and `test_service.py`