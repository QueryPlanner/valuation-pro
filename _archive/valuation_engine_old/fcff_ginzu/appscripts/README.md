# Google Apps Script Verification Tools

These scripts are used to bridge the gap between the Google Sheets reference models and the Python engine.

## Scripts

### 1. `mapping_diagnostic.js`
**Purpose:** Identifies the exact cell addresses for all inputs and outputs in a specific Google Sheet.
**Usage:** Run this if results diverge to ensure the Python engine is "reading" the right cells from the spreadsheet's logic.

### 2. `verifier_scenarios.js`
**Purpose:** Automates multiple valuation scenarios (High Growth, Low Margin, etc.) within the Google Sheet and prints a Markdown table of the results.
**Usage:** Use the output of this script as the `expected` values in `test_extensive_valuations.py`.

## How to Run
1. Open your valuation Google Sheet.
2. Go to `Extensions > Apps Script`.
3. Paste the contents of the desired script.
4. Select the function and click `Run`.
