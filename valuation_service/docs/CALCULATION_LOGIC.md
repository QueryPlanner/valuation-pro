# Valuation Service Calculation Logic

This document details how inputs are derived from Yahoo Finance data and how they align with the Aswath Damodaran FCFF (Ginzu) valuation rules.

## 1. Data Ingestion (Yahoo Finance Connector)

The `YahooFinanceConnector` fetches raw data and maps it to the "Base" inputs required by the model.

### Mapping Rules & Logic

| Input Variable | Rule / Logic | Source Field (YF) |
| :--- | :--- | :--- |
| **`revenues_base`** | **LTM Revenue.** If no revenue, defaults to 1000.0 (small positive number). | `Total Revenue` (LTM) |
| **`ebit_reported_base`** | **LTM Operating Income.** Even if negative. Used as the starting point for profitability. | `Operating Income` (LTM) |
| **`book_equity`** | **Total Equity.** Includes paid-in capital, retained earnings, and minority interests. | `Total Equity Gross Minority Interest` (MRQ) or `Stockholders Equity` |
| **`book_debt`** | **Interest Bearing Debt.** Includes short & long term debt. <br> *Note: If capitalizing leases, this is adjusted.* | `Total Debt` (MRQ) |
| **`capital_lease_obligations`** | **Reported Lease Debt.** Extracted for potential subtraction. | `Capital Lease Obligations` or `Long Term Capital Lease Obligation` (MRQ) |
| **`cash`** | **Cash & Marketable Securities.** | `Cash Cash Equivalents And Short Term Investments` (MRQ) |
| **`cross_holdings`** | **Non-operating Assets.** Minority holdings in other companies. | `Investmentin Financial Assets` (MRQ) |
| **`minority_interest`** | **Value of Non-controlling Interests.** | `Total Equity Gross Minority Interest` - `Stockholders Equity` (MRQ) |
| **`shares_outstanding`** | **Current Share Count.** Includes RSUs, excludes options. | `sharesOutstanding` (Info) or `Ordinary Shares Number` (BS) |
| **`stock_price`** | **Current Price.** | `currentPrice` (Info) |
| **`marginal_tax_rate`** | **Statutory Rate.** Based on country of domicile. | Mapped from Country Code (e.g., US=0.21) |
| **`effective_tax_rate`** | **Taxes / Taxable Income.** Clamped between 0.0 and Marginal Rate. | `Tax Provision` / `Pretax Income` (LTM) |
| **`risk_free_rate`** | **10-Year Treasury Yield.** | `^TNX` Close Price / 100 |

---

## 2. Input Preparation (Service Layer)

The `ValuationService` merges fetched data with User Assumptions to prepare `GinzuInputs`.

### Adjustments & Special Logic

#### 1. Operating Leases
*   **Rule:** If `capitalize_operating_leases` is **Yes** (True), we must:
    1.  Treat the user-provided `lease_debt` (converted value) as debt.
    2.  **Subtract** the accounting lease liability already present in `book_debt` to avoid double-counting.
*   **Implementation:**
    *   `book_debt (adjusted) = book_debt (reported) - capital_lease_obligations`
    *   `book_debt` is clamped to 0 if subtraction results in negative value.
    *   The engine separately adds `lease_debt` (from assumptions) to the total debt stack.

#### 2. R&D Capitalization
*   **Rule:** If `capitalize_rnd` is **Yes** (True):
    *   Fetch historical R&D expenses (up to 5 years).
    *   Calculate `rnd_asset` (unamortized portion).
    *   Calculate `rnd_ebit_adjustment` (Current R&D - Amortization).
    *   **Adjustments:**
        *   `book_equity += rnd_asset`
        *   `ebit_reported_base += rnd_ebit_adjustment` (Used for initial margin calculation)

#### 3. Invested Capital & Ratios
*   **Invested Capital:** `Book Equity + Book Debt - Cash`.
*   **Sales to Capital:** `Revenue / Invested Capital`.
    *   If Invested Capital <= 0, defaults to **1.5**.
    *   Used as default for `sales_to_capital_1_5` and `sales_to_capital_6_10`.

#### 4. Growth & Margins (Defaults)
These values are primarily driven by assumptions but have intelligent defaults:
*   **`rev_growth_y1`**: Default **5%**.
*   **`margin_y1`**: Default **Current Margin** (`EBIT / Revenue`).
*   **`margin_target`**: Default **Current Margin**.
*   **`rev_cagr_y2_5`**: Default **5%**.

---

## 3. Assumption Overrides

Users can override almost any input via the `assumptions` dictionary.

| Assumption Key | Description |
| :--- | :--- |
| `rev_growth_y1` | Expected revenue growth in Year 1. |
| `rev_cagr_y2_5` | Compounded Annual Growth Rate for Years 2-5. |
| `margin_target` | Target operating margin (mature phase). |
| `sales_to_capital_1_5` | Reinvestment efficiency (Sales generated per $1 capital). |
| `wacc_initial` | Cost of Capital (initial). Default 8%. |
| `capitalize_operating_leases` | Boolean. Triggers debt adjustment logic. |
| `lease_debt` | Converted value of operating leases (required if capitalizing). |
| `capitalize_rnd` | Boolean. Triggers R&D capitalization. |