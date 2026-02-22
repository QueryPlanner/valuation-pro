# Valuation Methodology: FCFF Simple Ginzu (Spreadsheet-Accurate Spec)

This document is not a “generic DCF primer”. It is a **precise specification** of how the valuation model in:

- `valuation_engine/fcff_ginzu/spreadsheets/fcffsimpleginzu-formulas/Input sheet.csv`
- `valuation_engine/fcff_ginzu/spreadsheets/fcffsimpleginzu-formulas/Valuation output.csv`

computes value **from raw numbers**, including all switches/overrides. The goal is that a developer can reproduce the spreadsheet outputs *without* Excel by following this spec verbatim.

## Conventions and scope

- **Units**: All currency inputs must be in consistent units (e.g., USD millions) and **must stay consistent** across revenues, EBIT, debt, cash, and non-operating assets. Share count uses share units consistent with per-share outputs.
- **Timeline**: The model forecasts Years \(1..10\) and a **Terminal year** (Year 11 in effect). Many “terminal” formulas use Year 10 discount factors.
- **Source of truth**: When something here differs from a generic finance textbook, the spreadsheet wins.
- **Initial WACC**: In v1 of the Python implementation, **initial cost of capital (WACC)** is treated as a direct input (even though the spreadsheet can derive it via `Cost of capital worksheet.csv`). The full WACC worksheet is still documented separately for a later step.

## Input dictionary (what the model needs)

This section maps “business inputs” to the places they appear in `Input sheet.csv`. The column names in the CSV are not important; what matters are the labelled rows and the logical meaning.

### Company base-year raw numbers (from `Input sheet.csv`)

- **Base revenues** (`revenues_base`): `Revenues` (row label) → value in column “Most Recent 12 months” (example: 46465).
- **Reported EBIT** (`ebit_reported_base`): `Operating income or EBIT` (example: 13815).
- **Interest expense** (`interest_expense_base`): used for the *WACC worksheet* and synthetic rating; not directly used in FCFF.
- **Book equity** (`book_equity`): used for invested capital and (optionally) distress proceeds.
- **Book debt** (`book_debt`): used in equity bridge (adjusted if leases are capitalized).
- **Cash** (`cash`): `Cash and Marketable Securities`.
- **Non-operating assets** (`non_operating_assets`): `Cross holdings and other non-operating assets`.
- **Minority interests** (`minority_interests`): used in equity bridge.
- **Shares outstanding** (`shares_outstanding`): used to compute value per share.
- **Current price** (`stock_price`): only used for “Price as % of value” and option pricing input.

### Value driver inputs (from `Input sheet.csv`)

- **Year 1 revenue growth** (`rev_growth_y1`): `Revenue growth rate for next year`.
- **CAGR Years 2–5** (`rev_cagr_y2_5`): `Compounded annual revenue growth rate - years 2-5`.
  - In many examples this is set equal to Year 1 growth, but it is conceptually distinct.
- **Operating margin Year 1** (`margin_y1`): `Operating Margin for next year`.
- **Target operating margin** (`margin_target`): `Target pre-tax operating margin`.
- **Margin convergence year** (`margin_convergence_year`): `Year of convergence for margin` (integer, typically 5).
- **Sales-to-capital Years 1–5** (`sales_to_capital_1_5`): `Sales to capital ratio (for years 1-5)`.
- **Sales-to-capital Years 6–10** (`sales_to_capital_6_10`): `Sales to capital ratio (for years 6-10)`.
- **Riskfree rate “today”** (`riskfree_rate_now`): `Riskfree rate`.
- **Initial cost of capital (WACC)** (`wacc_initial`): spreadsheet links this from `Cost of capital worksheet`, but the valuation math just needs the number.
- **Effective tax rate (base)** (`tax_rate_effective`): `Effective tax rate`.
- **Marginal tax rate (terminal)** (`tax_rate_marginal`): `Marginal tax rate`.

### Switches / overrides (from `Input sheet.csv`)

These switches materially change formulas; implement them as explicit branches.

#### R&D capitalization switch
- **capitalize_rnd**: `Do you have R&D expenses to capitalize?` (`Yes`/`No`)
  - If `Yes`, the model uses `R& D converter.csv` outputs for:\n    - **EBIT adjustment** (add to reported EBIT)\n    - **R&D asset** (added to invested capital)\n

#### Operating lease capitalization switch
- **capitalize_operating_leases**: `Do you have operating lease commitments?` (`Yes`/`No`)
  - If `Yes`, the model uses `Operating lease converter.csv` outputs for:\n    - **EBIT adjustment** (add to reported EBIT)\n    - **Lease debt** (added to debt in equity bridge)\n    - **Lease asset** (added to invested capital)\n

#### Options switch
- **has_employee_options**: `Do you have employee options outstanding?` (`Yes`/`No`)
  - If `Yes`, option value is computed via `Option value.csv` dilution-adjusted Black–Scholes and subtracted from equity.

#### Failure / distress switch
- **override_failure_probability**: `Do you want to override this assumption =` (failure) (`Yes`/`No`)
  - If `No`, failure probability = 0.
  - If `Yes`, use:\n    - `probability_of_failure` (`Input sheet` “probability of failure”)\n    - `distress_proceeds_tie` ∈ {`B`,`V`} (“tie proceeds to Book or Value”)\n    - `distress_proceeds_percent` (percentage)\n

#### Reinvestment lag switch
- **override_reinvestment_lag**: `Do you want override this assumption =` (lag) (`Yes`/`No`)
  - If `No`, the model uses a **1-year lag**: reinvestment in Year t funds growth from Year t to t+1.\n  - If `Yes`, `reinvestment_lag_years` is read from the sheet (0..3) and the revenue delta used for reinvestment shifts accordingly.\n

#### Tax-rate convergence override
- **override_tax_rate_convergence**: `Do you want to override this assumption =` (tax convergence) (`Yes`/`No`)
  - If `No`, terminal tax rate = marginal.\n  - If `Yes`, terminal tax rate = effective (no convergence).\n

#### NOL override
- **has_nol_carryforward**: `Do you want to override this assumption =` (NOL) (`Yes`/`No`)
  - If `Yes`, `nol_start_year1` is provided.\n  - If `No`, NOL starts at 0.\n

#### Riskfree-after-year-10 override
- **override_riskfree_after_year10**: `Do you want to override this assumption =` (riskfree after 10) (`Yes`/`No`)
  - If `Yes`, `riskfree_rate_after10` is used in stable-growth computations.\n

#### Perpetual growth override
- **override_perpetual_growth**: `Do you want to override this assumption =` (perpetual growth) (`Yes`/`No`)
  - If `No`, perpetual growth defaults to the relevant riskfree rate.\n  - If `Yes`, `perpetual_growth_rate` can be negative.\n

#### Stable WACC override
- **override_stable_wacc**: `Do you want to override this assumption =` (stable WACC) (`Yes`/`No`)
  - If `No`, stable WACC = \(riskfree + mature_market_ERP\) where mature ERP comes from `Country equity risk premiums.csv` cell `B1`.\n  - If `Yes`, `stable_wacc` is provided.\n

#### Stable ROC override
- **override_stable_roc**: `Do you want to override this assumption =` (stable ROC) (`Yes`/`No`)
  - If `No`, stable ROC is assumed to equal **Year 10 cost of capital**.\n  - If `Yes`, `stable_roc` is provided.\n

#### Trapped cash override
- **override_trapped_cash**: `Do you want to override this assumption` (trapped cash) (`Yes`/`No`)
  - If `Yes`, cash is reduced by an additional tax on trapped cash:\n    - `trapped_cash_amount`\n    - `trapped_cash_foreign_tax_rate`\n    - additional tax = trapped_cash_amount * (marginal_tax_rate - foreign_tax_rate)\n

## Core valuation pipeline (exact spreadsheet math)

All formulas here correspond to rows in `Valuation output.csv`. The following steps are evaluated in order.

### Step 0 — Determine stable-growth parameters

These values are used in years 6–10 transitions and terminal value.

- **Perpetual growth rate** \(g\) (row `Revenue growth rate`, `Terminal year`):\n  If `override_perpetual_growth == Yes` then use the explicit perpetual growth input.\n  Else if `override_riskfree_after_year10 == Yes` use `riskfree_rate_after10`.\n  Else use `riskfree_rate_now`.\n
- **Stable cost of capital** \(WACC_{stable}\) (row `Cost of capital`, `Terminal year`):\n  If `override_stable_wacc == Yes` use explicit stable WACC.\n  Else:\n  - pick riskfree = `riskfree_rate_after10` if override is on, else `riskfree_rate_now`\n  - add mature market ERP from `Country equity risk premiums.csv` cell `B1`\n  - \(WACC_{stable} = riskfree + ERP_{mature}\)\n
- **Terminal tax rate** \(t_{terminal}\) (row `Tax rate`, `Terminal year`):\n  If `override_tax_rate_convergence == Yes` then \(t_{terminal} = t_{effective}\).\n  Else \(t_{terminal} = t_{marginal}\).\n
- **Stable ROC** \(ROC_{stable}\) (row `ROIC`, `Terminal year`):\n  If `override_stable_roc == Yes` use explicit stable ROC.\n  Else \(ROC_{stable} = WACC_{10}\) (Year 10 cost of capital).\n

### Step 1 — Build revenue growth rates (Years 1–10)

Let \(g_1 = rev\_growth\_y1\).\n Let \(g_{2..5} = rev\_cagr\_y2\_5\) (constant for Years 2–5).\n
For Years 6–10, growth linearly transitions from Year 5 growth to \(g\) over 5 steps:\n
\n\[\n\Delta_g = \\frac{g_5 - g}{5}\n\]\n\[\n g_{5+k} = g_5 - k\\,\\Delta_g\\quad \\text{for } k \\in \\{1,2,3,4,5\\}\n\]\n

### Step 2 — Forecast revenues (Base + Years 1–10 + Terminal year)

Base revenue \(R_0 = revenues\_base\).\n For \(t \\in 1..10\):\n
\n\[\nR_t = R_{t-1}\\,(1+g_t)\n\]\n
Terminal-year revenue (Year 11) is:\n
\n\[\nR_{terminal} = R_{10}\\,(1+g)\n\]\n

### Step 3 — Determine EBIT margins (Base + Years 1–10)

Base margin:\n
\n\[\nmargin_0 = \\frac{EBIT_0}{R_0}\n\]\n
Year 1 margin is input: \(margin_1 = margin\\_y1\).\n
Years 2..10 linearly converge from Year 1 margin to target margin over `margin_convergence_year` years.\n The spreadsheet reaches the target exactly by that convergence year.\n
For a given year number \(t \\ge 2\):\n
- if \(t > Y_{conv}\) then \(margin_t = margin_{target}\)\n- else:\n
\n\[\nmargin_t = margin_{target} - \\Big(\\frac{margin_{target} - margin_1}{Y_{conv}}\\Big)\\,(Y_{conv} - t)\n\]\n
The terminal-year margin equals Year 10 margin.\n

### Step 4 — Compute adjusted base-year EBIT (lease/R&D adjustments)

The spreadsheet’s base-year EBIT includes optional adjustments:\n
- If leases are capitalized: add the operating lease adjustment from `Operating lease converter.csv`.\n- If R&D is capitalized: add the R&D operating income adjustment from `R& D converter.csv`.\n
Define:\n
\n\[\nEBIT_0 = EBIT_{reported,0} + Adj_{leases} + Adj_{R\\&D}\n\]\n
where each adjustment is 0 if its switch is `No`.\n
For forecast years:\n
\n\[\nEBIT_t = R_t\\,margin_t\n\]\n
Terminal-year EBIT is computed using terminal revenue and margin:\n
\n\[\nEBIT_{terminal} = R_{terminal}\\,margin_{terminal}\n\]\n
where \(margin_{terminal}\) equals Year 10 margin.


### Step 5 — Tax rates over time (Base + Years 1–10 + Terminal)

Base tax rate \(t_0 = tax\\_rate\\_effective\).\n Years 1–5 use the base rate.\n
Years 6–10 linearly transition from Year 5 tax rate to terminal tax rate over 5 steps:\n
\n\[\n t_{5+k} = t_5 + k\\,\\frac{t_{terminal} - t_5}{5}\\quad \\text{for } k \\in \\{1..5\\}\n\]\n

### Step 6 — NOL tracking and EBIT(1–t) with NOL shielding

This model includes **loss carryforward (NOL)** and applies it to reduce taxes.\n
Initial NOL (Year 0 / “Base year” bucket):\n
- if `has_nol_carryforward == Yes`, start with `nol_start_year1`\n- else start with 0\n
Let \(NOL_{t-1}\) be the NOL available entering year \(t\).\n
For each year \(t \\in 1..10\):\n
- If \(EBIT_t \\le 0\):\n  - \(EBIT(1-t)_t = EBIT_t\)\n  - \(NOL_t = NOL_{t-1} - EBIT_t\) (since EBIT is negative, this increases NOL)\n- If \(EBIT_t > 0\):\n  - If \(EBIT_t < NOL_{t-1}\):\n    - \(EBIT(1-t)_t = EBIT_t\) (no taxes paid)\n    - \(NOL_t = NOL_{t-1} - EBIT_t\)\n  - Else (EBIT exceeds NOL):\n    - taxable income = \(EBIT_t - NOL_{t-1}\)\n    - taxes = taxable income * \(t_t\)\n    - \(EBIT(1-t)_t = EBIT_t - taxes\)\n    - \(NOL_t = 0\)\n
Terminal-year after-tax EBIT uses the standard formula without NOL:\n
\n\[\nEBIT(1-t)_{terminal} = EBIT_{terminal}\\,(1 - t_{terminal})\n\]\n

### Step 7 — Sales-to-capital ratio path (Years 1–10)

The model uses two regimes:\n
- Years 1–5: `sales_to_capital_1_5`\n- Years 6–10: `sales_to_capital_6_10`\n
In the spreadsheet output table, the ratio is shown per year, with the switch happening at Year 6.\n

### Step 8 — Reinvestment (with lag options)

Default behavior (if `override_reinvestment_lag == No`) is a **1-year lag**.\n For year \(t\) reinvestment uses the revenue change from \(t \\to t+1\):\n
\n\[\nReinvestment_t = \\frac{R_{t+1} - R_t}{SalesToCapital_t}\n\]\n
Where \(SalesToCapital_t\) is the per-year ratio from Step 7.\n
If `override_reinvestment_lag == Yes`, the revenue delta used shifts according to the lag \(L \\in \\{0,1,2,3\\}\).\n The spreadsheet handles boundary years (near Year 10) by extrapolating using the perpetual growth rate \(g\); the implementation must match this behavior.\n
Terminal-year reinvestment is computed from stable growth consistency:\n
\n\[\nReinvestment_{terminal} = \\begin{cases}\n\\frac{g}{ROC_{stable}}\\,EBIT(1-t)_{terminal} & g > 0 \\\\\n0 & g \\le 0\n\\end{cases}\n\]\n

### Step 9 — FCFF (Years 1–10 + Terminal)

\n\[\nFCFF_t = EBIT(1-t)_t - Reinvestment_t\n\]\n
Terminal cash flow used for terminal value is \(FCFF_{terminal}\).\n

### Step 10 — Cost of capital path and discount factors

Years 1–5 cost of capital is constant at `wacc_initial`.\n
Years 6–10 linearly transition to \(WACC_{stable}\) over 5 steps:\n
\n\[\n WACC_{5+k} = WACC_5 - k\\,\\frac{WACC_5 - WACC_{stable}}{5}\\quad \\text{for } k \\in \\{1..5\\}\n\]\n
Discount factor is cumulative:\n
\n\[\nDF_1 = \\frac{1}{1+WACC_1}\n\]\n\[\nDF_t = DF_{t-1}\\,\\frac{1}{1+WACC_t}\\quad t\\ge2\n\]\n

### Step 11 — Present value of FCFF (Years 1–10)

\n\[\nPV(FCFF)_t = FCFF_t\\,DF_t\n\]\n
\n\[\nPV_{10y} = \\sum_{t=1}^{10} PV(FCFF)_t\n\]\n

### Step 12 — Terminal value and PV(Terminal value)

Terminal value is computed as a growing perpetuity using terminal cash flow:\n
\n\[\nTV = \\frac{FCFF_{terminal}}{WACC_{stable} - g}\n\]\n
Present value of terminal value uses the Year 10 discount factor:\n
\n\[\nPV(TV) = TV\\,DF_{10}\n\]\n
Sum of PVs (this is the “pre-failure-adjustment” operating asset value):\n
\n\[\nPV_{sum} = PV_{10y} + PV(TV)\n\]\n

### Step 13 — Failure probability adjustment (optional)

Let \(p_f\) be the probability of failure.\n If failure override is not enabled, \(p_f = 0\).\n
Distress proceeds depend on what you “tie” proceeds to:\n
- If tie = `B`: proceeds = \((book\\_equity + book\\_debt) \\times distress\\_proceeds\\_percent\)\n- If tie = `V`: proceeds = \(PV_{sum} \\times distress\\_proceeds\\_percent\)\n
Operating asset value is the expected value:\n
\n\[\nValue_{operating} = PV_{sum}(1-p_f) + Proceeds\\,p_f\n\]\n

### Step 14 — Equity bridge (operating assets → equity → per share)

Compute debt used in the bridge:\n
- If leases are capitalized: \(Debt = book\\_debt + LeaseDebt\)\n- Else \(Debt = book\\_debt\)\n
Cash adjustment for trapped cash (if enabled):\n
- additional tax = trapped_cash_amount * (tax_rate_marginal - trapped_cash_foreign_tax_rate)\n- adjusted cash = cash - additional tax\n
Equity value:\n
\n\[\nEquity = Value_{operating} - Debt - minority\\_interests + Cash_{adj} + non\\_operating\\_assets\n\]\n
Subtract option value if options are enabled:\n
\n\[\nEquity_{common} = Equity - OptionsValue\n\]\n
Per-share value:\n
\n\[\nValuePerShare = \\frac{Equity_{common}}{shares\\_outstanding}\n\]\n

## Optional modules: how their outputs plug into the core model

### Operating lease converter (`Operating lease converter.csv`)

If `capitalize_operating_leases == Yes`, you must compute:\n
- **Lease debt**: PV of future commitments discounted at pre-tax cost of debt\n- **Depreciation on lease asset**: straight-line over (5 + embedded years)\n- **Adjustment to operating earnings**: lease expense - depreciation\n
These feed:\n
- Base-year EBIT adjustment (`Adj_leases`)\n- Debt in equity bridge (`LeaseDebt`)\n- Invested capital adjustment (`LeaseAsset`)\n

### R&D converter (`R& D converter.csv`)

If `capitalize_rnd == Yes`, you must compute:\n
- **R&D asset**: sum of unamortized portions of R&D\n- **Current amortization**\n- **Adjustment to operating income**: current R&D - amortization\n
These feed:\n
- Base-year EBIT adjustment (`Adj_R&D`)\n- Invested capital adjustment (`R&D asset`)\n

### Option value (`Option value.csv`)

If `has_employee_options == Yes`, compute option value using dilution-adjusted Black–Scholes:\n
- Adjusted stock price \(S^*\) based on dilution\n- Standard Black–Scholes \(d1, d2\)\n- Total option value = value per option × number of options\n
Subtract total option value from equity.\n

## Notes for implementers

- The reinvestment lag override includes edge-case extrapolations beyond Year 10; if you implement that switch, mirror the spreadsheet behavior rather than inventing a new one.\n- Because the CSV exports store **formulas**, not evaluated results, validation is best done by reading the cached values from `valuation_engine/fcff_ginzu/spreadsheets/fcffsimpleginzu.xlsx` using `openpyxl` with `data_only=True`.\n*** End Patch}/>Json to=functions.apply_patch code>>()}>
