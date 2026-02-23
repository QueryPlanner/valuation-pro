# Role & Goal
You are an expert Financial Analyst AI. I am providing you with the latest 10-K report for Nvidia (NVDA) as a PDF.
Your objective is to read this 10-K report, extract the exact financial figures required for a Free Cash Flow to Firm (FCFF) valuation model, calculate reasonable value drivers based on the Management's Discussion and Analysis (MD&A), and output a single, ready-to-run `curl` command.

This `curl` command will send a JSON payload to our local Valuation Service API to calculate the stock's intrinsic value.

# Context
Today's Date: 2026-02-23
Base URL: http://localhost:8000
Endpoint: POST /valuation/calculate

# Valuation Methodology & Data Mapping
Our engine uses a strict FCFF simple ginzu methodology. Please extract and normalize the following base inputs exactly as they appear in the 10-K. 

**CRITICAL: Ensure all currency inputs are in consistent units (e.g., Millions of USD). If revenues are in millions, debt, cash, and shares outstanding must correspond correctly. For example, if shares are stated in billions, convert them to millions to match the currency units.**

## Base Financials (Extract from 10-K)
- `revenues_base`: Total Revenues for the most recent 12 months.
- `ebit_reported_base`: Operating income (EBIT). Do not include interest or taxes.
- `book_equity`: Total Stockholders' Equity.
- `book_debt`: Total Debt (Short-term + Long-term + Capital Leases if applicable).
- `cash`: Cash, cash equivalents, and marketable securities.
- `non_operating_assets`: Equity investments, cross holdings, or other non-operating assets.
- `minority_interests`: Non-controlling interests (if any).
- `shares_outstanding`: Basic or diluted shares outstanding (ensure units match the currency unit scale).
- `tax_rate_effective`: Effective tax rate (from the income statement / tax footnote).
- `tax_rate_marginal`: Statutory marginal tax rate (typically ~21% for US).

## R&D Capitalization (Highly relevant for Nvidia)
We adjust EBIT and Invested Capital by capitalizing R&D.
- `capitalize_rnd`: Set to `true`.
- `rnd_expense`: Extract the current year's R&D expense.
- `rnd_amortization_years`: Estimate the amortizable life of NVDA's R&D (typically 3-5 years).
- `rnd_history`: Extract the previous years' R&D expenses (newest to oldest) corresponding to the amortization years.

## Value Drivers (Estimate based on MD&A and current market conditions)
Based on Nvidia's historical performance, competitive position, and forward-looking statements in the 10-K, estimate the following:
- `rev_growth_y1`: Expected revenue growth rate for the next year.
- `rev_cagr_y2_5`: Expected compound annual growth rate for years 2-5.
- `margin_y1`: Expected operating margin for next year.
- `margin_target`: Target pre-tax operating margin (Year 5 onwards).
- `margin_convergence_year`: Year of convergence for margin (typically 5).
- `sales_to_capital_1_5`: Sales to capital ratio for years 1-5.
- `sales_to_capital_6_10`: Sales to capital ratio for years 6-10.
- `wacc_initial`: Initial cost of capital (Estimate based on current risk-free rate, NVDA's beta, and ERP).
- `riskfree_rate_now`: Current 10-year US Treasury yield.
- `mature_market_erp`: Use an estimate like 0.0411 (4.11%) or similar current Equity Risk Premium.

## Market Data
- `stock_price`: Provide Nvidia's current stock price as of 2026-02-23 (if you have internet access, look it up; otherwise, use a placeholder like 800.00 and remind me to update it).

# Expected Output Format
Output ONLY the `curl` command block. Do not include markdown explanations outside of the code block. Format it exactly like this:

```bash
curl -X POST "http://localhost:8000/valuation/calculate" 
     -H "Content-Type: application/json" 
     -d '{
           "ticker": "NVDA",
           "source": "yahoo",
           "as_of_date": "2026-02-23",
           "assumptions": {
               "revenues_base": <extracted_value>,
               "ebit_reported_base": <extracted_value>,
               "book_equity": <extracted_value>,
               "book_debt": <extracted_value>,
               "cash": <extracted_value>,
               "non_operating_assets": <extracted_value>,
               "minority_interests": <extracted_value>,
               "shares_outstanding": <extracted_value>,
               "stock_price": <estimated_or_looked_up_value>,
               "tax_rate_effective": <extracted_value>,
               "tax_rate_marginal": 0.21,
               "capitalize_rnd": true,
               "rnd_amortization_years": 3,
               "rnd_expense": <extracted_value>,
               "rnd_history": [<val1>, <val2>],
               "rev_growth_y1": <estimated_value>,
               "rev_cagr_y2_5": <estimated_value>,
               "margin_y1": <estimated_value>,
               "margin_target": <estimated_value>,
               "margin_convergence_year": 5,
               "sales_to_capital_1_5": <estimated_value>,
               "sales_to_capital_6_10": <estimated_value>,
               "wacc_initial": <estimated_value>,
               "riskfree_rate_now": <estimated_value>,
               "mature_market_erp": 0.0411
           }
         }'
```