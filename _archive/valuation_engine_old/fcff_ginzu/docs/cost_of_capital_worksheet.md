# Cost of Capital Worksheet (Documentation Only; Not Implemented in v1 Script)

This document explains how the spreadsheet computes **Initial cost of capital (WACC)** in:

- `/Users/lordpatil-air/Projects/apps/Valuation/fcffsimpleginzu-formulas/Cost of capital worksheet.csv`

The FCFF valuation itself (documented in `METHODOLOGY.md`) only needs the **final numeric WACC**. For the first Python implementation, you told me to **provide initial WACC directly** as an input. This doc exists so we can implement WACC derivation as a later follow-up without reverse-engineering again.

## What this worksheet is doing (high-level)

The sheet supports multiple “approaches” to arrive at a current WACC:

- **Direct input**: you type WACC and the worksheet uses it.
- **Detailed**: compute cost of equity and cost of debt from:
  - business risk (beta),
  - geographic risk (ERP via country/region mix),
  - default spread (synthetic rating or actual rating),
  - capital structure (market value weights),
  - plus tax rate.
- **Industry average**: pick WACC from an industry table and adjust for riskfree-rate differences.
- **Distribution**: pick a percentile from a histogram-like distribution.

The final output is always a single number: **Cost of capital based upon approach** (WACC).

## Key external data sources used

- `/Users/lordpatil-air/Projects/apps/Valuation/fcffsimpleginzu-formulas/Country equity risk premiums.csv`
  - Contains a **Mature Market ERP** in cell `B1` (e.g., 0.0433).
  - Contains country/region default spreads and country risk premia used to build ERPs.
- `/Users/lordpatil-air/Projects/apps/Valuation/fcffsimpleginzu-formulas/Industry Averages(US).csv`
- `/Users/lordpatil-air/Projects/apps/Valuation/fcffsimpleginzu-formulas/Industry Average Beta (Global).csv`
- `/Users/lordpatil-air/Projects/apps/Valuation/fcffsimpleginzu-formulas/Synthetic rating.csv`
  - Contains the interest-coverage-to-rating-to-default-spread mapping.

## Inputs (pulled from `Input sheet.csv`)

These are referenced directly from the input page:

- **Shares outstanding** and **stock price**: used to compute market value of equity.
- **Book value of debt** and **interest expense**: used in debt valuation (if needed) and synthetic rating.
- **Riskfree rate**: base for cost of equity and cost of debt.
- **Tax rate**: used to convert pre-tax cost of debt to after-tax, and also in levered beta formula.
- **Country** and sometimes **industry classification**: used for ERP and beta lookups.

## Output (the one number the FCFF model needs)

In `Input sheet.csv`, the valuation references:

- `Initial cost of capital` = `='Cost of capital worksheet'!B13`

So the “output cell” for WACC is **B13** in this worksheet:

- `Cost of capital based upon approach`

It selects the WACC depending on the “Which approach will you be using?” cell (also in this sheet).

## Detailed approach (how WACC is computed)

When approach is **Detailed**, WACC is computed as:

\[
WACC = w_E \cdot r_E + w_D \cdot r_D + w_P \cdot r_P
\]

Where:
- \(w_E, w_D, w_P\) are market-value weights of equity, debt, and preferred stock.
- \(r_E\) is the cost of equity.
- \(r_D\) is the after-tax cost of debt.
- \(r_P\) is preferred stock cost (dividend yield).

### Step A — Cost of equity

1. **Unlevered beta**:
   - Chosen from an industry table (US or Global), or directly input.
2. **Levered beta**:
   - Uses a standard unlevering/relevering relationship with the debt/equity ratio and tax rate.
3. **Equity Risk Premium (ERP)**:
   - Can be input directly, or derived from:
     - country of incorporation,
     - operating countries mix,
     - operating regions mix.
4. **Cost of equity**:

\[
r_E = r_f + \beta_L \cdot ERP
\]

### Step B — Cost of debt

1. Start from riskfree rate.
2. Add **company default spread**:
   - from actual rating table, or
   - from synthetic rating (interest coverage → rating → spread).
3. Add **country default spread** (if applicable) based on country.

\[
r_{D,preTax} = r_f + spread_{company} + spread_{country}
\]

Then convert to after-tax:

\[
r_D = r_{D,preTax} \cdot (1 - taxRate)
\]

### Step C — Capital weights

1. **Market value of equity**:
   - shares outstanding × stock price
2. **Market value of debt**:
   - either approximated using bond pricing math, or inferred using simplified assumptions.
3. **Preferred stock**:
   - if provided (often zero).

Weights are computed as each component divided by total capital.

## Industry average approach

The sheet can look up an industry cost of capital and then “currency/time adjust” it by:

- adding the difference between the current riskfree rate and a baseline riskfree used to build the table.

## Distribution approach

The sheet can pick a WACC from a distribution table based on:

- region grouping (US/Global/Europe/etc.)
- percentile (first decile, median, etc.)

## Implementation note for future scripting

When we implement this worksheet in Python, the safest approach is **not** to build a general “Excel formula engine”. Instead:

- implement the **specific** business logic as deterministic Python functions,
- read “configuration choices” (approach selection strings),
- keep lookups (country ERP, industry beta, rating spreads) as explicit tables loaded from the CSVs.


