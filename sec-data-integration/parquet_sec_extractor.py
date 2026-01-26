import subprocess
import json
import os
import sys
import csv
import io
import datetime
from pathlib import Path

# --- Configuration ---
DATA_ROOT = os.environ.get("SEC_DATA_ROOT", "/Volumes/lord-ssd/data/sec-data")
SUB_PATTERN = os.path.join(DATA_ROOT, "*", "sub.parquet")
NUM_PATTERN = os.path.join(DATA_ROOT, "*", "num.parquet")

# --- Constants (Copied from sec_data_extractor.py) ---
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
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest"
    ],
    "rnd": ["ResearchAndDevelopmentExpense"],
    "book_equity": [
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        "StockholdersEquity"
    ],
    "minority_interest": ["StockholdersEquityAttributableToNoncontrollingInterest", "MinorityInterest"],
    "debt_total": [
        "LongTermDebtAndCapitalLeaseObligations", 
        "DebtAndCapitalLeaseObligations"
    ],
    "debt_noncurrent": ["LongTermDebtNoncurrent"],
    "debt_current": [
        "ShortTermBorrowings", 
        "LongTermDebtCurrent", 
        "DebtCurrent", 
        "CommercialPaper"
    ],
    "cash": ["CashAndCashEquivalentsAtCarryingValue"],
    "marketable_securities": ["MarketableSecuritiesCurrent", "MarketableSecurities"],
    "leases_noncurrent": ["OperatingLeaseLiabilityNoncurrent"],
    "leases_current": ["OperatingLeaseLiabilityCurrent"],
    "shares": ["CommonStockSharesOutstanding", "SharesOutstanding", "EntityCommonStockSharesOutstanding"],
    "income_tax_expense": ["IncomeTaxExpenseBenefit"],
    "income_before_tax": [
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxes"
    ],
    "investments_noncurrent": [
        "AvailableForSaleSecuritiesNoncurrent",
        "MarketableSecuritiesNoncurrent",
        "OtherLongTermInvestments",
        "EquityMethodInvestments"
    ]
}

TAX_RATES = {
    "US": 0.21, "IE": 0.125, "GB": 0.25, "CN": 0.25, "DE": 0.30, "JP": 0.3062
}

# --- Helper Functions ---

def run_query_csv(sql):
    """Executes a SQL query via DuckDB CLI and returns CSV output."""
    # We use :memory: db but reference external parquet files in the SQL
    cmd = ['duckdb', '-csv', ':memory:', '-c', sql]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"DuckDB Error: {result.stderr}")
        return result.stdout
    except Exception as e:
        raise Exception(f"Failed to execute DuckDB command: {e}")

def parse_date(date_str):
    try:
        return datetime.datetime.strptime(str(date_str), "%Y%m%d").date()
    except ValueError:
        return None

def get_filings(cik):
    """
    Returns (latest_10k_row, latest_filing_row, country_code)
    """
    # Note: CAST(cik as VARCHAR) or just comparing as int depending on parquet schema.
    # Usually cik in sub is integer or string. Let's assume integer or handle string.
    # We cast to string in SQL to be safe if input is string.
    
    sql = f"""
    SELECT adsh, form, period, fy, fp, countryba
    FROM read_parquet('{SUB_PATTERN}')
    WHERE CAST(cik AS VARCHAR) = '{str(int(cik))}' 
    AND form IN ('10-K', '10-K/A', '10-Q', '10-Q/A')
    ORDER BY period DESC, filed DESC;
    """
    csv_out = run_query_csv(sql)
    reader = csv.DictReader(io.StringIO(csv_out))
    rows = list(reader)
    
    if not rows:
        return None, None, 'US'

    latest_filing = rows[0]
    latest_10k = None
    
    for row in rows:
        if row['form'] == '10-K':
            latest_10k = row
            break
        elif row['form'] == '10-K/A' and not latest_10k:
            latest_10k = row
            
    return latest_10k, latest_filing, latest_filing.get('countryba', 'US')

def fetch_facts(adsh, tags_list):
    """
    Fetches numeric facts for the given ADSH and Tags from parquet files.
    """
    if not adsh: return []
    
    all_tags = set()
    for t_list in tags_list:
        all_tags.update(t_list)
        
    tags_str = "'" + "','".join(all_tags) + "'"
    
    # We optimize by filtering on ADSH. DuckDB pushdown is usually good.
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
    for tag in tag_candidates:
        # First pass: Look for consolidated (dimh=0 or '0x00000000')
        # Parquet might store dimh as string '0x...'
        for f in facts:
            if f['tag'] == tag and int(f['qtrs']) == qtrs:
                # Handle potential nulls or different formats for dimh
                f_dimh = f.get('dimh', '0x00000000') or '0x00000000'
                if f_dimh == segment_hash:
                    if ddate and str(f['ddate']) != str(ddate).replace('-', ''):
                        continue
                    return float(f['value'])
        
        # Second pass: Sum segments
        segmented_values = []
        for f in facts:
            if f['tag'] == tag and int(f['qtrs']) == qtrs:
                if ddate and str(f['ddate']) != str(ddate).replace('-', ''):
                    continue
                f_dimh = f.get('dimh', '0x00000000') or '0x00000000'
                if f_dimh != segment_hash:
                    segmented_values.append(float(f['value']))
        
        if segmented_values:
            if len(segmented_values) <= 3:
                return sum(segmented_values)
            else:
                return max(segmented_values)
    return None

def calculate_ltm(concept_tags, latest_10k, latest_filing, facts_10k, facts_latest):
    if not latest_10k: return 0.0
    
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

def extract_data(cik):
    latest_10k, latest_filing, country = get_filings(cik)
    
    if not latest_10k:
        return {"error": "No 10-K found"}

    all_tags = list(TAGS.values())
    facts_10k = fetch_facts(latest_10k['adsh'], all_tags)
    
    if latest_filing and latest_filing['adsh'] != latest_10k['adsh']:
        facts_latest = fetch_facts(latest_filing['adsh'], all_tags)
    else:
        facts_latest = facts_10k

    data = {}
    
    # --- Flows (LTM) ---
    data['revenues_base'] = calculate_ltm(TAGS['revenues'], latest_10k, latest_filing, facts_10k, facts_latest)
    data['ebit_reported_base'] = calculate_ltm(TAGS['ebit'], latest_10k, latest_filing, facts_10k, facts_latest)
    data['rnd_expense'] = calculate_ltm(TAGS['rnd'], latest_10k, latest_filing, facts_10k, facts_latest)
    
    tax_exp = calculate_ltm(TAGS['income_tax_expense'], latest_10k, latest_filing, facts_10k, facts_latest)
    pre_tax_inc = calculate_ltm(TAGS['income_before_tax'], latest_10k, latest_filing, facts_10k, facts_latest)
    
    if pre_tax_inc != 0 and tax_exp is not None:
        data['effective_tax_rate'] = tax_exp / pre_tax_inc
    else:
        data['effective_tax_rate'] = 0.0

    # --- Stocks (Point in Time) ---
    target_date = latest_filing['period'] if latest_filing else latest_10k['period']
    
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
        d_short = get_fact_value(facts_latest, TAGS['debt_current'], 0, target_date) or 0
        total_debt = d_long + d_short
    data['book_debt'] = total_debt or 0.0

    cash = get_fact_value(facts_latest, TAGS['cash'], 0, target_date) or 0
    mkt = get_fact_value(facts_latest, TAGS['marketable_securities'], 0, target_date) or 0
    data['cash'] = cash + mkt

    l_long = get_fact_value(facts_latest, TAGS['leases_noncurrent'], 0, target_date) or 0
    l_short = get_fact_value(facts_latest, TAGS['leases_current'], 0, target_date) or 0
    data['operating_leases_liability'] = l_long + l_short

    i_equity = get_fact_value(facts_latest, ["EquityMethodInvestments"], 0, target_date) or 0
    i_avail = get_fact_value(facts_latest, ["AvailableForSaleSecuritiesNoncurrent"], 0, target_date) or 0
    i_other = get_fact_value(facts_latest, ["OtherLongTermInvestments"], 0, target_date) or 0
    data['cross_holdings'] = max(i_equity + i_avail, i_other)

    shares = get_fact_value(facts_latest, TAGS['shares'], 0, target_date)
    if not shares and latest_10k:
        shares = get_fact_value(facts_10k, TAGS['shares'], 0, latest_10k['period'])
    data['shares_outstanding'] = shares or 0.0

    data['marginal_tax_rate'] = TAX_RATES.get(country, 0.21)
    data['rnd_input_flag'] = 'yes' if data['rnd_expense'] > 0 else 'no'
    data['operating_leases_flag'] = 'yes' if data['operating_leases_liability'] > 0 else 'no'

    # --- Derived Metrics ---
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
        'latest_filing_date': target_date,
        'latest_filing_form': latest_filing['form'] if latest_filing else '10-K',
        'currency': 'USD' 
    }

    return data

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python parquet_sec_extractor.py <CIK>")
        sys.exit(1)
        
    cik = sys.argv[1]
    try:
        result = extract_data(cik)
        print(json.dumps(result, indent=4))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
