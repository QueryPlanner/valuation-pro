# Valuation Tool

This directory contains the integration of the **Valuation Engine** with real-time **SEC Data**.

## Usage

To run a valuation for a specific company using its CIK (Central Index Key):

```bash
python3 run_valuation.py <CIK>
```

**Example (Apple):**
```bash
python3 run_valuation.py 320193
```

## Data Sources

1.  **Real Data (SEC Data Integration)**
    *   LTM Revenues
    *   LTM EBIT (Operating Income)
    *   Book Value of Equity & Debt
    *   Cash & Marketable Securities
    *   Shares Outstanding
    *   Effective Tax Rate (Historical)

2.  **Mock Data (Highlighted in Output)**
    *   Market Inputs: Risk-free rate, Equity Risk Premium, Stock Price
    *   Forecast Assumptions: Revenue Growth, Target Margins, Convergence periods, WACC

## Configuration

Default Mock assumptions are defined in `run_valuation.py` under `MOCK_DEFAULTS`.
You can modify these directly in the script to test different scenarios.
