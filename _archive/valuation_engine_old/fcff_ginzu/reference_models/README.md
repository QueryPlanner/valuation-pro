# Reference Models

This directory contains the "source of truth" formulas and spreadsheets used to verify the Python engine.

## Structure

- `amzn/`: CSV formulas and the original `amzn_valuation.xlsx` for Amazon.
- `ko/`: CSV formulas and the original `ko_valuation.xlsx` for Coca-Cola.

## Parity Auditing

The CSV files in `amzn/` and `ko/` were exported using Google Sheets to allow for programmatic auditing of the underlying logic (e.g., linear growth transitions, reinvestment lead-lags). The Python engine's outputs are verified against these models using the scripts in the `appscripts/` directory.
