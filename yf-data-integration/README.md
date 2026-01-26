# Yahoo Finance Data Integration

This module provides tools to extract financial data from Yahoo Finance and run valuations using the core valuation engine. It serves as an alternative data source to the SEC-based extraction pipeline.

## Overview

The `yf-data-integration` module consists of two main components:

1.  **`yf_data_extractor.py`**: A standalone script and library to fetch, clean, and normalize financial data from Yahoo Finance using the `yfinance` library. It calculates derived metrics required for valuation, such as Last Twelve Months (LTM) figures, Invested Capital, and Sales-to-Capital ratios.
2.  **`run_yf_valuation.py`**: A workflow script that bridges the extracted Yahoo Finance data with the `valuation_engine`. It takes a ticker symbol, fetches the data, applies valuation assumptions (with support for overrides and mock defaults), and outputs a DCF valuation summary.

## Prerequisites

Ensure you have the required dependencies installed. The primary external dependency is `yfinance`.

```bash
pip install -r ../requirements.txt
# OR specifically
pip install yfinance pandas
```

## Usage

### 1. Data Extraction Only

To simply fetch and inspect the JSON data structure for a specific company:

```bash
# Usage: python yf_data_extractor.py <TICKER> [AS_OF_DATE]
python yf-data-integration/yf_data_extractor.py AAPL
```

**Output:** A JSON object containing:
*   **Financials**: Base Revenues, Reported EBIT, R&D Expenses, Tax metrics.
*   **Balance Sheet Items**: Book Equity, Debt, Cash, Minority Interests.
*   **Derived Metrics**: Invested Capital, Sales/Capital Ratio, Effective Tax Rate.
*   **Metadata**: Source, Currency, Ticker.

### 2. Running a Valuation

To perform a full valuation using the extracted data:

```bash
# Usage: python run_yf_valuation.py <TICKER>
python yf-data-integration/run_yf_valuation.py MSFT
```

**Process:**
1.  **Fetch Data**: Scrapes real-time/latest available data from Yahoo Finance.
2.  **Prepare Inputs**: Maps the raw data to the `GinzuInputs` schema required by the valuation engine. It fills in missing assumptions with configurable mock defaults (e.g., WACC, Growth Rates) defined in the script.
3.  **Compute**: Runs the `compute_ginzu` function from `valuation_engine`.
4.  **Result**: Prints a detailed summary of Operating Assets, Equity Value, and per-share Intrinsic Value vs. Market Price.

## Key Logic & Assumptions

*   **LTM Calculation**: The extractor sums the last 4 quarters of data for Income Statement items to get a "Trailing 12 Months" view.
*   **Invested Capital**: Calculated as `Book Equity + Book Debt - Cash`.
*   **R&D Capitalization**: The codebase contains logic to capitalize R&D expenses (converting them from operating expenses to assets), improving valuation accuracy for tech/pharma companies. *Note: This feature may be toggled via flags in the script.*
*   **Fallback Logic**: If quarterly data is insufficient, it falls back to Annual reports or Mock defaults to ensure the pipeline doesn't crash on thinner datasets.

## Project Structure

*   `yf_data_extractor.py`: Core extraction logic.
*   `run_yf_valuation.py`: Integration script connecting data to the valuation engine.
