# SEC Data Integration for Valuation Engine

This directory contains the tools and scripts to extract financial inputs required for the FCFF Valuation Engine from the SEC Financial Statement Data Sets (DuckDB format).

## Overview

The extraction logic is designed to pull "Recent 12 Months" (R12M) data for flow items (Revenue, EBIT) and the most recent "Point-in-Time" data for stock items (Debt, Cash, Equity).

### Data Source
- **Database**: DuckDB file (`/Volumes/lord-ssd/data/sec-data/sec-notes.duckdb`) containing SEC data sets (`SUB`, `NUM`, `TAG`, `DIM`, `PRE`, `REN`, `TXT`, `CAL`).
- **Tables Used**: 
  - `SUB` (Submissions): To identify filings and dates.
  - `NUM` (Numbers): To extract financial values.
  - `DIM` (Dimensions): To filter for consolidated data vs segments.

## Methodology

### 1. Filing Selection
The script identifies two key filings for a given CIK:
- **Latest 10-K**: The most recent Annual Report. Used for **Flow** items (Revenues, EBIT, R&D, Tax) to ensure a complete 12-month period.
- **Latest Filing (10-K or 10-Q)**: The absolute most recent financial report. Used for **Stock** items (Book Equity, Debt, Cash, Shares) to reflect the current financial position.

### 2. Tag Mapping
The script uses a prioritized list of XBRL tags to find values. Key mappings include:

| Input Field | XBRL Tags (Prioritized) | Source |
|---|---|---|
| **Revenues** | `RevenueFromContractWithCustomerExcludingAssessedTax`, `Revenues`, `SalesRevenueNet` | Latest 10-K |
| **EBIT** | `OperatingIncomeLoss` | Latest 10-K |
| **R&D Expense** | `ResearchAndDevelopmentExpense` | Latest 10-K |
| **Book Equity** | `StockholdersEquity` | Latest Filing |
| **Debt** | `LongTermDebtNoncurrent` + `ShortTermBorrowings` / `LongTermDebtCurrent` | Latest Filing |
| **Cash** | `CashAndCashEquivalentsAtCarryingValue` + `MarketableSecuritiesCurrent` | Latest Filing |
| **Operating Leases** | `OperatingLeaseLiabilityNoncurrent` + `OperatingLeaseLiabilityCurrent` | Latest Filing |
| **Shares** | `CommonStockSharesOutstanding`, `SharesOutstanding` | Latest Filing |

### 3. Extraction Logic
- **Consolidated Data**: The script prioritizes values where `segments` is `NULL` (or empty), representing the consolidated entity.
- **Handling Shares**: If a consolidated share count is not found (often due to multiple share classes), the script sums the values of `CommonStockSharesOutstanding` across all segments (Classes) for the given date.
- **Tax Rate**: `Effective Tax Rate` is calculated as `IncomeTaxExpenseBenefit / IncomeBeforeTax` from the 10-K.
- **Corruption Handling**: The script uses a robust query pattern (`SELECT ... FROM num WHERE adsh = ...`) to avoid hitting corrupted indexes in the DuckDB file.

## Usage

### Prerequisites
- Python 3.x
- `duckdb` CLI installed and accessible in system PATH.
- Access to the SEC DuckDB file.

### Running the Script

```bash
python3 sec_data_extractor.py <CIK>
```

**Example:**
```bash
python3 sec-data-integration/sec_data_extractor.py 1652044
```

### Output
The script outputs a JSON object with the required inputs for the valuation engine:

```json
{
    "revenues_base": 350018000000.0,
    "ebit_reported_base": 112390000000.0,
    "rnd_expense": 49326000000.0,
    "effective_tax_rate": 0.164,
    "book_equity": 362916000000.0,
    "book_debt": 24607000000.0,
    "cash": 95148000000.0,
    "operating_leases_liability": 14959000000.0,
    "shares_outstanding": 12104000000.0,
    ...
}
```

## Caveats & Limitations
1. **LTM Calculation**: Currently, flow items are taken from the last Annual Report (10-K). If the latest filing is a Q2 or Q3 10-Q, the Revenue/EBIT might be "stale" by up to 9 months compared to a true LTM (Last Twelve Months) calculation.
2. **Tag Variations**: While common tags are covered, some companies might use niche or deprecated tags not yet mapped.
3. **Units**: The script assumes values are in the unit reported (usually USD). Shares are in `shares`. No automatic currency conversion is performed.
