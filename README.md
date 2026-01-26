# Valuation Project

A Python implementation of advanced valuation models, designed for 1:1 mathematical parity with reference Google Sheets models.

## Structure

- `valuation_engine/`: The core Python package containing valuation logic and tests.
  - `fcff_ginzu/`: Implementation of the Free Cash Flow to the Firm (FCFF) "Ginzu" model.
    - `reference_models/`: Reference CSV formulas and Excel spreadsheets used for parity verification.
    - `appscripts/`: Google Apps Script tools for extracting "truth" data from spreadsheets.
    - `tests/`: Extensive unit tests and parity verification suite.

## Getting Started

See [valuation_engine/README.md](valuation_engine/README.md) for detailed documentation on the valuation engine and how to run parity tests.
