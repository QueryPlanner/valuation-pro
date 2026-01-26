# SEC Data Extraction Methodology for Valuation Engine

## Overview
This document outlines the heuristic and logic used to extract financial inputs from the SEC data (DuckDB) for the FCFF Valuation Engine. The goal is to automate the retrieval of "Last Twelve Months" (LTM) flow data and "Most Recent" stock data.

## Data Source
- **Database**: `sec-notes.duckdb`
- **Tables**: `sub` (submissions), `num` (numeric facts), `dim` (dimensions).
- **Format**: DuckDB.

## Extraction Logic

### 1. Identify Filings
We query the `sub` table for the given CIK to identify:
- **Latest 10-K**: The most recent Annual Report.
- **Latest Filing**: The absolute most recent filing (10-K or 10-Q).

### 2. Time Periods (LTM Calculation)
For "Flow" items (Revenue, EBIT, Tax, R&D), we need LTM.

- **Scenario A: Latest Filing is 10-K**
  - LTM = Value from 10-K (where `qtrs=4`).

- **Scenario B: Latest Filing is 10-Q (e.g., Q1, Q2, Q3)**
  - LTM = (Latest 10-K FY Value) + (Current Year YTD Value) - (Previous Year YTD Value).
  - *Current Year YTD*: From Latest 10-Q (e.g., `qtrs=2` for Q2).
  - *Previous Year YTD*: Also found in Latest 10-Q (comparative column).

### 3. Consolidated Data
We filter for `dimhash = '0x00000000'` or where `segments` IS NULL to ensure we get consolidated numbers, avoiding disaggregated segment data (except for Shares, where we might sum classes if needed).

### 4. Input Mapping

#### A. Revenues (Base)
- **Concept**: Total Revenue.
- **Tags**: `Revenues`, `RevenueFromContractWithCustomerExcludingAssessedTax`, `SalesRevenueNet`.
- **Logic**: LTM.

#### B. EBIT (Base)
- **Concept**: Operating Income.
- **Tags**: `OperatingIncomeLoss`.
- **Logic**: LTM.

#### C. Book Equity
- **Concept**: Total Shareholders' Equity + Minority Interest.
- **Tags**: `StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest` (Priority), or `StockholdersEquity` + `MinorityInterest` / `StockholdersEquityAttributableToNoncontrollingInterest`.
- **Logic**: Point-in-time (`qtrs=0`) from Latest Filing.

#### D. Book Debt
- **Concept**: Interest-bearing debt (Long + Short).
- **Tags**: 
  - `LongTermDebtAndCapitalLeaseObligations`
  - OR Sum of: `LongTermDebtNoncurrent`, `ShortTermBorrowings`, `LongTermDebtCurrent`.
- **Logic**: Point-in-time from Latest Filing.

#### E. Cash & Marketable Securities
- **Concept**: Cash + Liquid Investments.
- **Tags**: 
  - `CashAndCashEquivalentsAtCarryingValue`
  - `MarketableSecuritiesCurrent`
  - `MarketableSecurities`
- **Logic**: Point-in-time from Latest Filing.

#### F. Minority Interest
- **Concept**: Book value of non-controlling interest.
- **Tags**: `StockholdersEquityAttributableToNoncontrollingInterest`, `MinorityInterest`.
- **Logic**: Point-in-time from Latest Filing.

#### G. Cross Holdings (Non-Operating Assets)
- **Concept**: Minority holdings in other companies.
- **Tags**: 
  - `AvailableForSaleSecuritiesNoncurrent`
  - `MarketableSecuritiesNoncurrent`
  - `OtherLongTermInvestments`
  - `EquityMethodInvestments`
- **Logic**: Point-in-time from Latest Filing.

#### H. Shares Outstanding
- **Concept**: Total common shares.
- **Tags**: `CommonStockSharesOutstanding`, `SharesOutstanding`, `EntityCommonStockSharesOutstanding`.
- **Logic**: Point-in-time from Latest Filing.

#### I. R&D Expenses
- **Concept**: Research and development costs.
- **Tags**: `ResearchAndDevelopmentExpense`.
- **Logic**: LTM.

#### J. Operating Leases
- **Concept**: Lease liabilities (if capitalized) or commitments.
- **Tags**: `OperatingLeaseLiabilityNoncurrent`, `OperatingLeaseLiabilityCurrent`.
- **Logic**: Point-in-time (Sum of Current + Noncurrent).

#### K. Effective Tax Rate
- **Concept**: Tax Expense / Pre-tax Income.
- **Tags**:
  - Tax: `IncomeTaxExpenseBenefit`.
  - Income: `IncomeLossFromContinuingOperationsBeforeIncomeTaxes`, `IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest`.
- **Logic**: LTM Ratio.

#### L. Marginal Tax Rate
- **Concept**: Statutory tax rate of domicile country.
- **Logic**: Lookup based on `countryba` (Business Address Country) from `sub` table. Default to 21% (US) if unknown/US.

## Data Filtering
- We prioritize values with `uom='USD'`.
- We select the maximum value if duplicates exist for the same tag/period/dimension (heuristic for revisions/consolidated).

