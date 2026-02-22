## `engine.py` — Comprehensive Usage Guide

This document describes how to use the **CSV/XLSX-independent valuation engine** in `engine.py`.

The engine is designed to be the long-term core for:
- An SEC-derived data pipeline (your database → normalized inputs)
- An API layer (later FastAPI) that calls the engine with JSON payloads

It intentionally **does not** read CSV/XLSX and **does not** fetch data. Those concerns belong in adapter layers.

---

## Core idea (Ports & Adapters)

- **Engine (this repo)**: deterministic pure functions
  - Input: a fully-specified `GinzuInputs`
  - Output: a `GinzuOutputs` with both headline values and intermediate series

- **Adapters (you will build)**: everything that turns raw data into `GinzuInputs`
  - SEC facts → normalized financials → `GinzuInputs`
  - Your assumptions UI/API → `GinzuInputs` overrides

This keeps the core model stable, testable, and easy to evolve.

---

## Quick start

### Minimal valuation

```python
from valuation_engine.fcff_ginzu import GinzuInputs, compute_ginzu

inputs = GinzuInputs(
    # Base-year raw numbers
    revenues_base=574785.0,
    ebit_reported_base=36852.0,
    book_equity=201875.0,
    book_debt=161574.0,
    cash=86780.0,
    non_operating_assets=2954.0,
    minority_interests=0.0,
    shares_outstanding=10492.0,
    stock_price=169.0,
    # Value drivers
    rev_growth_y1=0.12,
    rev_cagr_y2_5=0.12,
    margin_y1=0.14,
    margin_target=0.14,
    margin_convergence_year=5,
    sales_to_capital_1_5=1.5,
    sales_to_capital_6_10=1.5,
    riskfree_rate_now=0.0408,
    wacc_initial=0.086,
    tax_rate_effective=0.19,
    tax_rate_marginal=0.25,
)

outputs = compute_ginzu(inputs)
print("Estimated value/share:", outputs.estimated_value_per_share)
```

### What you get back (`GinzuOutputs`)

`GinzuOutputs` includes:
- Key headline values: `pv_10y`, `pv_terminal_value`, `value_of_operating_assets`, `value_of_equity_common`, `estimated_value_per_share`
- Full intermediate series: revenues, margins, EBIT, tax rates, reinvestment, FCFF, discount factors, PV by year

These series are especially useful in an API: you can return “debug mode” outputs for explainability.

---

## Required inputs (what the engine needs)

`GinzuInputs` is split into:

- **Base year (company snapshot)**
  - `revenues_base`, `ebit_reported_base`
  - `book_equity`, `book_debt`, `cash`
  - `non_operating_assets`, `minority_interests`
  - `shares_outstanding`, `stock_price`

- **Value drivers**
  - Growth: `rev_growth_y1`, `rev_cagr_y2_5`
  - Profitability: `margin_y1`, `margin_target`, `margin_convergence_year`
  - Reinvestment efficiency: `sales_to_capital_1_5`, `sales_to_capital_6_10`
  - Discounting/taxes: `riskfree_rate_now`, `wacc_initial`, `tax_rate_effective`, `tax_rate_marginal`

---

## Default assumptions & how to override them (engine-first)

The “default assumptions” in the spreadsheet correspond to **explicit fields** on `GinzuInputs`.

### Stable WACC (mature-company assumption)

- Default behavior: stable WACC is computed as:
  - \( stable\_wacc = riskfree + mature\_market\_erp \)
- Override:
  - `override_stable_wacc=True`
  - `stable_wacc=<your number>`

### Tax rate convergence (effective → marginal)

- Default behavior: terminal tax uses `tax_rate_marginal`
- Override (disable convergence):
  - `override_tax_rate_convergence=True` (terminal tax stays at `tax_rate_effective`)

### Riskfree after year 10

- Default behavior: perpetual settings use `riskfree_rate_now`
- Override:
  - `override_riskfree_after_year10=True`
  - `riskfree_rate_after10=<your number>`

### Perpetual growth

- Default behavior: perpetual growth equals the riskfree rate used for terminal assumptions
- Override:
  - `override_perpetual_growth=True`
  - `perpetual_growth_rate=<your number>`

### Stable ROC after year 10

- Default behavior: stable ROC defaults to Year 10 WACC (spreadsheet parity)
- Override:
  - `override_stable_roc=True`
  - `stable_roc=<your number>`

### Failure probability and distress proceeds

- Default behavior: no failure (probability 0)
- Override:
  - `override_failure_probability=True`
  - `probability_of_failure` in \([0,1]\)
  - `distress_proceeds_tie="B"` (book) or `"V"` (value)
  - `distress_proceeds_percent` in \([0,1]\)

### NOL carryforward

- Default behavior: no NOL
- Override:
  - `has_nol_carryforward=True`
  - `nol_start_year1=<amount>`

### Reinvestment lag

- Default behavior: 1-year lag (spreadsheet default)
- Override:
  - `override_reinvestment_lag=True`
  - `reinvestment_lag_years` in `{0,1,2,3}`

### Trapped cash

- Default behavior: cash is fully accessible
- Override:
  - `override_trapped_cash=True`
  - `trapped_cash_amount=<amount>`
  - `trapped_cash_foreign_tax_rate=<rate>`

### Mature market ERP

- Used only when `override_stable_wacc=False`
- Override by setting: `mature_market_erp=<rate>`

---

## Optional modules (what the engine supports today)

These modules are **supported by the engine**, but the engine expects either:
- precomputed module outputs, or
- raw module inputs via a dedicated helper function (currently available for R&D)

### R&D capitalization (recommended engine-first approach)

Use the engine helper (no spreadsheets required):

```python
from valuation_engine.fcff_ginzu import RnDCapitalizationInputs, compute_rnd_capitalization_adjustments

rnd_asset, rnd_ebit_adjustment = compute_rnd_capitalization_adjustments(
    RnDCapitalizationInputs(
        amortization_years=3,
        current_year_rnd_expense=85622.0,
        past_year_rnd_expenses=[73213.0, 56052.0],  # ordered [-1, -2, ...]
    )
)
```

Then set on `GinzuInputs`:
- `capitalize_rnd=True`
- `rnd_asset=rnd_asset`
- `rnd_ebit_adjustment=rnd_ebit_adjustment`

### Operating lease capitalization (inputs are precomputed for now)

To include operating leases:
- `capitalize_operating_leases=True`
- provide:
  - `lease_debt` (PV of commitments; debt equivalent)
  - `lease_ebit_adjustment` (EBIT adjustment)

This module is intentionally “adapter-owned”: your SEC pipeline can compute these from lease footnote disclosures.

### Employee options (inputs are precomputed for now)

To subtract employee options from equity:
- `has_employee_options=True`
- provide:
  - `options_value` (total option value)

The engine also includes a Black–Scholes helper for parity:
- `compute_dilution_adjusted_black_scholes_option_value(OptionInputs(...))`

---

## Practical notes for SEC pipelines

### Units and scaling (critical)

All “base year” values must be internally consistent:
- If you use USD **millions** for revenues/debt/cash, shares must also be in **millions**
- If shares are in raw share-count, all currency values must also be in raw dollars

### Suggested mapping discipline

In your adapter layer, build a normalized “company snapshot” object first, then convert to `GinzuInputs`.
Avoid mixing SEC tag parsing with valuation logic.

### Returning results in an API

Use:
- `estimated_value_per_share` for the headline result
- optionally return intermediate series to explain the valuation

---

## Related files in this repo

- `engine.py`: the core engine (this doc)
- `archive/fcff_simple_ginzu.py`: spreadsheet-mode loader + CLI adapter (parity checks)
- `utils/`: convenience wrappers / examples (non-engine)


