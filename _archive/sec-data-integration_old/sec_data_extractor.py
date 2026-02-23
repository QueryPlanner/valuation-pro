import csv
import datetime
import io
import json
import os
import subprocess
import sys
from pathlib import Path

_DEFAULT_EXTERNAL_DB_PATH = "/Volumes/lord-ssd/data/sec-data/sec-notes.duckdb"
_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_LOCAL_DB_PATH = _REPO_ROOT / "sec_fsn.duckdb"

# Data Source configuration
DATA_ROOT = os.environ.get("SEC_DATA_ROOT", "/Volumes/lord-ssd/data/sec-data")
SUB_PATTERN = os.path.join(DATA_ROOT, "*", "sub.parquet")
NUM_PATTERN = os.path.join(DATA_ROOT, "*", "num.parquet")

# Allow callers/runners to override the DB path without editing this file:
DB_PATH = os.environ.get("SEC_DUCKDB_PATH") or os.environ.get("SEC_DB_PATH") or (
    str(_DEFAULT_LOCAL_DB_PATH) if _DEFAULT_LOCAL_DB_PATH.exists() else _DEFAULT_EXTERNAL_DB_PATH
)

# Mapping of concepts to list of possible XBRL tags (priority order)
TAGS = {
    "revenues": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
        "SalesRevenueGoodsNet",
        "TotalRevenuesAndOtherIncome"
    ],
    "ebit": [
        "OperatingIncomeLoss",
        "OperatingProfitLoss",
        "IncomeLossFromContinuingOperationsBeforeInterestAndIncomeTaxes",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest" # EBT Fallback
    ],
    "rnd": ["ResearchAndDevelopmentExpense"],
    "book_equity": [
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"
    ],
    "minority_interest": ["StockholdersEquityAttributableToNoncontrollingInterest", "MinorityInterest"],
    "debt_total": [
        "DebtAndCapitalLeaseObligations"
    ],
    "debt_noncurrent": ["LongTermDebtNoncurrent", "LongTermDebtAndCapitalLeaseObligations"],
    "debt_current": [
        "ShortTermBorrowings",
        "NotesAndLoansPayable",
        "LongTermDebtCurrent",
        "DebtCurrent",
        "CommercialPaper"
    ],
    "cash": ["CashAndCashEquivalentsAtCarryingValue"],
    "marketable_securities": [
        "ShortTermInvestments",
        "MarketableSecuritiesCurrent",
        "MarketableSecurities"
    ],
    "leases_noncurrent": ["OperatingLeaseLiabilityNoncurrent"],
    "leases_current": ["OperatingLeaseLiabilityCurrent"],
    "shares": ["EntityCommonStockSharesOutstanding", "CommonStockSharesOutstanding", "SharesOutstanding"],
    "income_tax_expense": ["IncomeTaxExpenseBenefit"],
    "income_before_tax": [
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxes"
    ],
    "investments_noncurrent": [
        "AvailableForSaleSecuritiesNoncurrent",
        "MarketableSecuritiesNoncurrent",
        "OtherLongTermInvestments",
        "EquityMethodInvestments",
        "EquitySecuritiesFVNINoncurrent",
        "EquitySecuritiesWithoutReadilyDeterminableFairValueAmount"
    ],
    "interest_expense": ["InterestExpense", "InterestExpenseDebt", "InterestExpenseNonoperating"]
}

# Country Tax Rates (Simplified Mock)
TAX_RATES = {
    "US": 0.21,
    "IE": 0.125, # Ireland
    "GB": 0.25,  # UK
    "CN": 0.25,  # China
    "DE": 0.30,  # Germany
    "JP": 0.3062 # Japan
}

def run_query_csv(sql):
    # Use :memory: since we are reading from Parquet files directly
    cmd = ['duckdb', '-csv', ':memory:', '-c', sql]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"DuckDB Error: {result.stderr}")
    return result.stdout

def parse_date(date_str):
    try:
        return datetime.datetime.strptime(str(date_str), "%Y%m%d").date()
    except ValueError:
        return None

def get_filings(cik, as_of_date=None):
    """
    Returns (latest_10k_row, latest_filing_row, country_code)
    """
    date_filter = ""
    if as_of_date:
        # SEC 'filed' column is YYYYMMDD as INTEGER or STRING
        # as_of_date is expected as YYYY-MM-DD or YYYYMMDD
        as_of_date_str = str(as_of_date)
        clean_date = None

        # Try YYYY-MM-DD
        try:
             dt = datetime.datetime.strptime(as_of_date_str, "%Y-%m-%d")
             clean_date = dt.strftime("%Y%m%d")
        except ValueError:
             # Try YYYYMMDD
             try:
                 dt = datetime.datetime.strptime(as_of_date_str, "%Y%m%d")
                 clean_date = dt.strftime("%Y%m%d")
             except ValueError:
                 raise ValueError("Invalid date format. Expected YYYY-MM-DD or YYYYMMDD.")

        date_filter = f"AND filed <= {clean_date}"

    sql = f"""
    SELECT adsh, form, period, fy, fp, countryba, filed
    FROM read_parquet('{SUB_PATTERN}')
    WHERE CAST(cik AS VARCHAR) = '{str(int(cik))}' 
    AND form IN ('10-K', '10-K/A', '10-Q', '10-Q/A')
    {date_filter}
    ORDER BY period DESC, filed DESC;
    """
    csv_out = run_query_csv(sql)
    reader = csv.DictReader(io.StringIO(csv_out))
    rows = list(reader)

    if not rows:
        return None, None, 'US'

    latest_filing = rows[0]
    latest_10k = None

    # Heuristic: Prefer 10-K over 10-K/A for the same period
    for row in rows:
        if row['form'] == '10-K':
            latest_10k = row
            break
        elif row['form'] == '10-K/A' and not latest_10k:
            latest_10k = row

    return latest_10k, latest_filing, latest_filing.get('countryba', 'US')

def fetch_facts(adsh, tags_list):
    """
    Fetches all numeric facts for the given ADSH and Tags.
    """
    if not adsh: return []

    # Flatten tags list
    all_tags = set()
    for t_list in tags_list:
        all_tags.update(t_list)

    tags_str = "'" + "','".join(all_tags) + "'"

    sql = f"""
    SELECT n.tag, CAST(n.value AS DOUBLE) as value, n.uom, n.qtrs, n.ddate, n.dimh
    FROM read_parquet('{NUM_PATTERN}') n
    WHERE n.adsh = '{adsh}'
    AND n.tag IN ({tags_str})
    ORDER BY CAST(n.value AS DOUBLE) DESC; 
    """

    csv_out = run_query_csv(sql)
    reader = csv.DictReader(io.StringIO(csv_out))
    return list(reader)

def get_fact_value(facts, tag_candidates, qtrs, ddate=None, segment_hash='0x00000000'):
    """
    Finds a value matching criteria.
    If segment_hash='0x00000000' (Consolidated) returns nothing, 
    try to sum values across segments if they appear to be non-overlapping.
    """
    for tag in tag_candidates:
        # First pass: Look for consolidated (dimh=0)
        for f in facts:
            if f['tag'] == tag and int(f['qtrs']) == qtrs:
                if f['dimh'] == segment_hash:
                    if ddate and f['ddate'] != str(ddate).replace('-', ''):
                        continue
                    return float(f['value'])

        # Second pass: If no consolidated value, look for segmented values to sum
        # Group by dimh to avoid double-counting duplicate rows for the same segment
        segment_map = {}
        for f in facts:
            if f['tag'] == tag and int(f['qtrs']) == qtrs:
                if ddate and str(f['ddate']) != str(ddate).replace('-', ''):
                    continue
                if f['dimh'] != segment_hash:
                    # If we see the same segment again, assume it's a duplicate or revision; take max
                    current_val = float(f['value'])
                    if f['dimh'] in segment_map:
                        segment_map[f['dimh']] = max(segment_map[f['dimh']], current_val)
                    else:
                        segment_map[f['dimh']] = current_val

        segmented_values = list(segment_map.values())

        if segmented_values:
            # Heuristic: Sum if few segments (likely Class A + Class B), otherwise take MAX (if many, likely a time series or mess)
            if len(segmented_values) <= 3:
                return sum(segmented_values)
            else:
                return max(segmented_values)

    return None

def calculate_ltm(concept_tags, latest_10k, latest_filing, facts_10k, facts_latest):
    """
    Calculates LTM value based on filing status.
    LTM = FY + YTD_Current - YTD_Prev
    """
    fy_date = latest_10k['period']
    val_fy = get_fact_value(facts_10k, concept_tags, 4, fy_date)

    if val_fy is None:
        return 0.0

    if latest_filing['adsh'] == latest_10k['adsh']:
        return val_fy

    fp = latest_filing['fp']
    ytd_qtrs = 0
    if fp == 'Q1': ytd_qtrs = 1
    elif fp in ['Q2', 'H1']: ytd_qtrs = 2
    elif fp in ['Q3', 'M9']: ytd_qtrs = 3
    else: return val_fy

    curr_date = latest_filing['period']
    curr_dt_obj = parse_date(curr_date)
    if not curr_dt_obj: return val_fy

    prev_dt_obj = datetime.date(curr_dt_obj.year - 1, curr_dt_obj.month, curr_dt_obj.day)
    prev_date = prev_dt_obj.strftime("%Y%m%d")

    val_curr_ytd = get_fact_value(facts_latest, concept_tags, ytd_qtrs, curr_date)
    val_prev_ytd = get_fact_value(facts_latest, concept_tags, ytd_qtrs, prev_date)

    if val_curr_ytd is not None and val_prev_ytd is not None:
        return val_fy + val_curr_ytd - val_prev_ytd

    return val_fy

def extract_data(cik, as_of_date=None):
    latest_10k, latest_filing, country = get_filings(cik, as_of_date=as_of_date)

    if not latest_10k:
        return {"error": "No 10-K found"}

    all_tags = list(TAGS.values())
    facts_10k = fetch_facts(latest_10k['adsh'], all_tags)

    if latest_filing['adsh'] != latest_10k['adsh']:
        facts_latest = fetch_facts(latest_filing['adsh'], all_tags)
    else:
        facts_latest = facts_10k

    data = {}

    # --- Flows (LTM) ---
    data['revenues_base'] = calculate_ltm(TAGS['revenues'], latest_10k, latest_filing, facts_10k, facts_latest)
    data['ebit_reported_base'] = calculate_ltm(TAGS['ebit'], latest_10k, latest_filing, facts_10k, facts_latest)
    data['rnd_expense'] = calculate_ltm(TAGS['rnd'], latest_10k, latest_filing, facts_10k, facts_latest)
    data['interest_expense'] = calculate_ltm(TAGS['interest_expense'], latest_10k, latest_filing, facts_10k, facts_latest)

    tax_exp = calculate_ltm(TAGS['income_tax_expense'], latest_10k, latest_filing, facts_10k, facts_latest)
    pre_tax_inc = calculate_ltm(TAGS['income_before_tax'], latest_10k, latest_filing, facts_10k, facts_latest)

    if pre_tax_inc != 0:
        data['effective_tax_rate'] = tax_exp / pre_tax_inc
    else:
        data['effective_tax_rate'] = 0.0

    # --- Stocks (Point in Time) ---
    target_date = latest_filing['period']

    equity = get_fact_value(facts_latest, TAGS['book_equity'], 0, target_date)
    if equity is None:
        se = get_fact_value(facts_latest, ["StockholdersEquity"], 0, target_date) or 0
        mi = get_fact_value(facts_latest, TAGS['minority_interest'], 0, target_date) or 0
        equity = se + mi
    data['book_equity'] = equity if equity else 0.0

    data['minority_interest'] = get_fact_value(facts_latest, TAGS['minority_interest'], 0, target_date) or 0.0

    total_debt = get_fact_value(facts_latest, TAGS['debt_total'], 0, target_date)
    if total_debt is None:
        d_long = get_fact_value(facts_latest, TAGS['debt_noncurrent'], 0, target_date) or 0

        # Current Debt Calculation:
        # Instead of picking just one tag from the list, we need to sum distinct components:
        # 1. Short Term Borrowings (or its components like Commercial Paper / Notes)
        # 2. Current Portion of Long Term Debt

        # Try aggregate "DebtCurrent" first
        d_short_agg = get_fact_value(facts_latest, ["DebtCurrent"], 0, target_date)

        if d_short_agg is not None:
            d_short = d_short_agg
        else:
            # Component 1: Short Term Borrowings
            stb = get_fact_value(facts_latest, ["ShortTermBorrowings"], 0, target_date)
            if stb is not None:
                d_short_borrowing = stb
            else:
                # Fallback to components if aggregate STB is missing
                # Sum CommercialPaper + NotesAndLoansPayable
                cp = get_fact_value(facts_latest, ["CommercialPaper"], 0, target_date) or 0
                notes = get_fact_value(facts_latest, ["NotesAndLoansPayable"], 0, target_date) or 0
                d_short_borrowing = cp + notes

            # Component 2: Current Portion of LTD
            ltdc = get_fact_value(facts_latest, ["LongTermDebtCurrent", "LongTermDebtAndCapitalLeaseObligationsCurrent"], 0, target_date) or 0

            d_short = d_short_borrowing + ltdc

        total_debt = d_long + d_short
    data['book_debt'] = total_debt or 0.0

    cash = get_fact_value(facts_latest, TAGS['cash'], 0, target_date) or 0
    mkt = get_fact_value(facts_latest, TAGS['marketable_securities'], 0, target_date) or 0
    data['cash'] = cash + mkt

    l_long = get_fact_value(facts_latest, TAGS['leases_noncurrent'], 0, target_date) or 0
    l_short = get_fact_value(facts_latest, TAGS['leases_current'], 0, target_date) or 0
    data['operating_leases_liability'] = l_long + l_short

    # Cross Holdings
    # We sum up the best available value for each major category in TAGS['investments_noncurrent']
    # But since they might overlap or be mutually exclusive based on taxonomy choice, we should follow the priority list
    # or just try to grab the specific ones we know are additive.
    # The previous manual logic missed 'MarketableSecuritiesNoncurrent'.
    # Let's try to fetch using the specific keys in our list manually to be safe, but include all of them.

    # "AvailableForSaleSecuritiesNoncurrent"
    i_avail = get_fact_value(facts_latest, ["AvailableForSaleSecuritiesNoncurrent"], 0, target_date) or 0
    # "MarketableSecuritiesNoncurrent" - often used instead of AvailableForSale
    i_mkt_nc = get_fact_value(facts_latest, ["MarketableSecuritiesNoncurrent"], 0, target_date) or 0
    # "EquityMethodInvestments"
    i_equity = get_fact_value(facts_latest, ["EquityMethodInvestments"], 0, target_date) or 0
    # "OtherLongTermInvestments"
    i_other = get_fact_value(facts_latest, ["OtherLongTermInvestments"], 0, target_date) or 0

    # "EquitySecuritiesFVNINoncurrent" - Fair Value Net Income (often strategic stakes)
    i_eq_fvni = get_fact_value(facts_latest, ["EquitySecuritiesFVNINoncurrent"], 0, target_date) or 0
    # "EquitySecuritiesWithoutReadilyDeterminableFairValueAmount" - Private stakes
    i_eq_no_fair = get_fact_value(facts_latest, ["EquitySecuritiesWithoutReadilyDeterminableFairValueAmount"], 0, target_date) or 0

    # Basic logic: i_avail and i_mkt_nc are likely mutually exclusive or one is a parent of another.
    # If both exist and are different, it's risky. But usually companies use one or the other.
    # Safe bet: sum them all but watch out for duplicates?
    # Actually, let's just use the robust `get_fact_value` with the whole list if we want the "best one",
    # BUT cross holdings is often a sum of multiple line items (e.g. Equity Method + Available for Sale).
    # So summing the distinct types is correct.

    # If a company has BOTH MarketableSecuritiesNoncurrent AND AvailableForSaleSecuritiesNoncurrent,
    # we might double count if we just sum.
    # However, usually MarketableSecuritiesNoncurrent is the higher level concept or an alternative.
    # Let's take the MAX of (MarketableSecuritiesNoncurrent, AvailableForSaleSecuritiesNoncurrent) to be safe against double counting,
    # OR sum them if they seem distinct.
    # Given the previous bug was missing 77B which was purely MarketableSecuritiesNoncurrent, let's include it.

    # Refined Strategy: Sum (EquityMethod) + (Other) + MAX(AvailableForSale, MarketableSecuritiesNoncurrent)
    # This assumes Marketable and AvailableForSale are likely describing the same pot of money if both appear,
    # or one is a subset.
    # NVDA Case: EquitySecuritiesFVNINoncurrent is distinct.

    inv_securities = max(i_avail, i_mkt_nc)

    # For NVDA, i_eq_fvni and i_eq_no_fair might be duplicates if one is a detail of the other.
    # Checking NVDA: EquitySecuritiesWithoutReadilyDeterminable... has same value as EquitySecuritiesFVNINoncurrent?
    # In my finding_missing_tag, they were both 8.187B.
    # It is likely they are alternative tags for the same concept or one is a roll-up.
    # Let's take MAX of them.
    inv_strategic = max(i_eq_fvni, i_eq_no_fair)

    data['cross_holdings'] = i_equity + inv_securities + i_other + inv_strategic

    # Try EntityCommonStockSharesOutstanding specifically without date constraint first
    # This is usually the most accurate "cover page" count
    shares = get_fact_value(facts_latest, ["EntityCommonStockSharesOutstanding"], 0, ddate=None)

    if not shares:
        # Fallback to standard logic with strict date
        shares = get_fact_value(facts_latest, TAGS['shares'], 0, target_date)

    if not shares:
        # Retry all share tags without date constraint
        shares = get_fact_value(facts_latest, TAGS['shares'], 0, ddate=None)

    if not shares and latest_10k:
        shares = get_fact_value(facts_10k, TAGS['shares'], 0, latest_10k['period'])
        if not shares:
            shares = get_fact_value(facts_10k, TAGS['shares'], 0, ddate=None)

    data['shares_outstanding'] = shares or 0.0

    data['marginal_tax_rate'] = TAX_RATES.get(country, 0.21)
    data['rnd_input_flag'] = 'yes' if data['rnd_expense'] > 0 else 'no'
    data['operating_leases_flag'] = 'yes' if data['operating_leases_liability'] > 0 else 'no'

    # --- Derived Metrics ---
    # Invested Capital = Book Equity + Book Debt - Cash (+ Lease Debt if capitalized)
    # Note: R&D Capitalization is currently disabled in this extractor, so R&D Asset is 0.
    inv_cap = data['book_equity'] + data['book_debt'] - data['cash']
    if data['operating_leases_flag'] == 'yes':
        inv_cap += data['operating_leases_liability']

    data['invested_capital'] = inv_cap

    if inv_cap > 0 and data['revenues_base'] > 0:
        data['sales_to_capital'] = data['revenues_base'] / inv_cap
    else:
        data['sales_to_capital'] = 0.0

    data['metadata'] = {
        'cik': cik,
        'latest_filing_date': latest_filing['period'],
        'latest_filing_form': latest_filing['form'],
        'currency': 'USD'
    }

    return data

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python sec_data_extractor.py <CIK> [as_of_date]")
        sys.exit(1)

    cik = sys.argv[1]
    as_of_date = sys.argv[2] if len(sys.argv) > 2 else None
    try:
        result = extract_data(cik, as_of_date=as_of_date)
        print(json.dumps(result, indent=4))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
