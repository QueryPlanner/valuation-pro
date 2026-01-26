# Valuation (FCFF Simple Ginzu)

A **spreadsheet-faithful** implementation of the FCFF "Simple Ginzu" valuation model in Python. This engine is designed for high precision, matching the exact math of the widely used valuation spreadsheets while remaining framework-agnostic and dependency-free for core computations.

## Core Engine: `valuation_engine/fcff_ginzu/engine.py`

The heart of this project is the FCFF Ginzu engine, now located in `valuation_engine/fcff_ginzu/engine.py`. It is a standalone, pure-Python module that contains the entire valuation logic.

- **CSV/XLSX Independent**: No dependency on external spreadsheets for core math.
- **API Friendly**: Designed to be integrated into data pipelines or web APIs (e.g., FastAPI).
- **Comprehensive**: Handles R&D capitalization, lease capitalization, employee options, NOLs, and various growth/WACC overrides.

### Minimal Example

```python
from valuation_engine.fcff_ginzu import GinzuInputs, compute_ginzu

# 1. Define your inputs
inputs = GinzuInputs(
    revenues_base=574785.0,
    ebit_reported_base=36852.0,
    book_equity=201875.0,
    book_debt=161574.0,
    cash=86780.0,
    non_operating_assets=2954.0,
    minority_interests=0.0,
    shares_outstanding=10492.0,
    stock_price=169.0,
    rev_growth_y1=0.12,
    rev_cagr_y2_5=0.12,
    margin_y1=0.1133,
    margin_target=0.14,
    margin_convergence_year=5,
    sales_to_capital_1_5=1.5,
    sales_to_capital_6_10=1.5,
    riskfree_rate_now=0.0408,
    wacc_initial=0.086,
    tax_rate_effective=0.19,
    tax_rate_marginal=0.25,
)

# 2. Run the valuation
outputs = compute_ginzu(inputs)

# 3. Access results
print(f"Value per share: {outputs.estimated_value_per_share:.2f}")
```

For advanced usage (R&D, leases, etc.), see [valuation_engine/fcff_ginzu/docs/valuation_engine.md](valuation_engine/fcff_ginzu/docs/valuation_engine.md).

## Utilities: `valuation_engine/fcff_ginzu/utils/`

The `utils/` directory provides convenience tools for interacting with the engine without writing Python code for every run.

- **`utils/archive/manual_inputs.py`**: A project-local configuration file where you can plug in company data and assumptions (Archived).
- **`utils/archive/run_manual_inputs.py`**: A CLI wrapper that reads from `manual_inputs.py`, runs the engine, and prints a human-readable summary (Archived).

### Running with manual inputs (Archived)

1. Edit `valuation_engine/fcff_ginzu/utils/archive/manual_inputs.py` with your data.
2. Run the CLI:
   ```bash
   python valuation_engine/fcff_ginzu/utils/archive/run_manual_inputs.py
   ```

## Setup & Requirements

- **Python 3.10+** (3.9+ also supported).
- **No third-party dependencies** required for the core engine.

```bash
# Optional: create a virtual environment
uv venv .venv
source .venv/bin/activate
```

## Advanced & Legacy Features

### Spreadsheet Parity & Archive
The `valuation_engine/fcff_ginzu/archive/` folder contains scripts for running the engine against original spreadsheet CSV exports to verify parity. See `valuation_engine/fcff_ginzu/archive/fcff_simple_ginzu.py` for details.

### Methodology
For a deep dive into the exact formulas and how they map to the spreadsheet model, see [valuation_engine/fcff_ginzu/METHODOLOGY.md](valuation_engine/fcff_ginzu/METHODOLOGY.md).

---
*Maintained by: [Chirag Patil](mailto:chiragnpatil@gmail.com)*