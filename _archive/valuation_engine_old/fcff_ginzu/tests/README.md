# Parity & Unit Tests

This directory contains the suite of tests used to ensure the Python engine matches the reference spreadsheet logic with 1:1 precision.

## Key Tests

- `test_extensive_valuations.py`: The primary parity suite. It runs 20+ scenarios for AMZN and KO, comparing Python outputs against "Truth" data generated via Apps Script.
- `test_engine_units.py`: Low-level unit tests for individual components (WACC, Tax transitions, Growth).
- `test_valuation_repro.py`: Regression tests to ensure valuation results remain stable across code changes.

## Running Tests

From the project root:
```bash
python3 -m unittest valuation_engine/fcff_ginzu/tests/test_extensive_valuations.py
```

## Maintenance
If the spreadsheet logic changes, update the "Truth" tables in `test_extensive_valuations.py` using the values provided by the `verifier_scenarios.js` Apps Script.
