# FCFF Ginzu Model

This module implements the Free Cash Flow to the Firm (FCFF) "Ginzu" model, a comprehensive 10-year valuation framework with a 3-stage transition logic.

## Logic Highlights

### 1. Growth Transition (Years 6-10)
The model uses a linear decrement to transition from the Year 5 CAGR to the Terminal Growth Rate:
`Growth_n = Growth_{n-1} - ((Year_5_CAGR - Terminal_Growth) / 5)`

### 2. Tax Rate Convergence
The effective tax rate linearly converges to the marginal tax rate over the 10-year period.

### 3. Reinvestment Lead-Lag
By default, the model assumes a one-year lag between reinvestment and growth generation:
`Reinvestment_n = (Revenue_{n+1} - Revenue_n) / Sales_to_Capital`

## Engine Architecture

- `engine.py`: The core calculation logic.
- `GinzuInputs`: A typed dataclass for all valuation drivers.
- `GinzuOutputs`: A detailed breakdown of the valuation results, including year-by-year cash flows.

## Parity Status
The engine is currently verified to have **1:1 parity** with the reference Google Sheets model for AMZN and KO across baseline and stressed scenarios.
