import datetime
import json
import sys

import pandas as pd
import yfinance as yf

# Country Tax Rates (Simplified Mock) - Matches sec_data_extractor.py
TAX_RATES = {
    "US": 0.21,
    "United States": 0.21,
    "IE": 0.125, # Ireland
    "GB": 0.25,  # UK
    "CN": 0.25,  # China
    "DE": 0.30,  # Germany
    "JP": 0.3062 # Japan
}

def get_ltm_value(df, row_name, num_quarters=4, offset_quarters=0):
    """
    Sums `num_quarters` values for a given row, starting from `offset_quarters`.
    Assumes df columns are dates in descending order (newest first).
    """
    if row_name not in df.index:
        return 0.0

    # Take slice [offset : offset + num_quarters]
    subset = df.loc[row_name].iloc[offset_quarters : offset_quarters + num_quarters]
    return float(subset.sum())

def get_mrq_value(df, row_name):
    """
    Gets the value from the Most Recent Quarter (first column).
    """
    if row_name not in df.index:
        return 0.0

    # First column is the latest
    val = df.loc[row_name].iloc[0]
    return float(val) if not pd.isna(val) else 0.0

def extract_data(ticker_symbol, as_of_date=None):
    ticker = yf.Ticker(ticker_symbol)

    # Check if data exists
    if not ticker.info or 'regularMarketPrice' not in ticker.info:
        # Sometimes info is empty if ticker is bad or rate limited,
        # but let's try fetching financials to be sure.
        pass

    # Fetch Dataframes
    q_inc = ticker.quarterly_financials
    q_bal = ticker.quarterly_balance_sheet
    ann_inc = ticker.financials

    if q_inc.empty or q_bal.empty:
         return {"error": f"No financial data found for {ticker_symbol}"}

    # --- Date Filtering ---
    if as_of_date:
        # Parse as_of_date if string
        if isinstance(as_of_date, str):
            try:
                dt_limit = datetime.datetime.strptime(as_of_date, "%Y-%m-%d").date()
            except ValueError:
                # Try fallback format if needed or just fail/warn
                dt_limit = datetime.date.today()
        else:
            dt_limit = as_of_date

        # Filter columns: keep only those <= dt_limit
        # Assumes columns are timestamps (datetime.datetime)

        def filter_cols(df):
            if df.empty: return df
            # Convert cols to date for comparison
            valid_cols = [c for c in df.columns if c.date() <= dt_limit]
            # yfinance returns sorted new->old, so we just keep the valid ones
            # The "MRQ" becomes the newest valid column.
            return df[valid_cols]

        q_inc = filter_cols(q_inc)
        q_bal = filter_cols(q_bal)
        ann_inc = filter_cols(ann_inc)

        if q_inc.empty or q_bal.empty:
             return {"error": f"No financial data found for {ticker_symbol} as of {as_of_date}"}

    data = {}
    info = ticker.info

    # --- Flows (LTM) ---
    # Check if we have enough quarterly data for LTM (need 4 quarters)
    use_annual_fallback = False
    if len(q_inc.columns) < 4:
        use_annual_fallback = True
        # If we don't have annual data either, we are in trouble, but loop will handle it (return 0 or partial)
        if ann_inc.empty:
            use_annual_fallback = False # Revert to partial quarterly sum

    if use_annual_fallback:
        # Use Most Recent Annual
        rev_base = get_mrq_value(ann_inc, 'Total Revenue')
        data['ebit_reported_base'] = get_mrq_value(ann_inc, 'Operating Income')
        data['rnd_expense'] = get_mrq_value(ann_inc, 'Research And Development')
        tax_exp = get_mrq_value(ann_inc, 'Tax Provision')
        pre_tax_inc = get_mrq_value(ann_inc, 'Pretax Income')
    else:
        # We sum the last 4 quarters for Current LTM
        rev_base = get_ltm_value(q_inc, 'Total Revenue')
        data['ebit_reported_base'] = get_ltm_value(q_inc, 'Operating Income')
        data['rnd_expense'] = get_ltm_value(q_inc, 'Research And Development')
        tax_exp = get_ltm_value(q_inc, 'Tax Provision')
        pre_tax_inc = get_ltm_value(q_inc, 'Pretax Income')

    if rev_base <= 0:
        rev_base = 1000.0 # Small positive number rule
    data['revenues_base'] = rev_base

    # Calculate Previous LTM Revenue (Quarters 5-8) for Growth
    # Check if we have enough quarterly data (needs 8 cols for 2 full LTM periods)
    if not use_annual_fallback and len(q_inc.columns) >= 8:
        rev_prior = get_ltm_value(q_inc, 'Total Revenue', offset_quarters=4)
        if rev_prior > 0:
            data['revenue_growth_actual'] = (rev_base - rev_prior) / rev_prior
        else:
            data['revenue_growth_actual'] = 0.05
    else:
        # Fallback to Annual Financials (Growth)
        # ann_inc is now filtered too
        if 'Total Revenue' in ann_inc.index and len(ann_inc.columns) >= 2:
            rev_fy0 = ann_inc.loc['Total Revenue'].iloc[0]
            rev_fy1 = ann_inc.loc['Total Revenue'].iloc[1]
            if rev_fy1 > 0:
                 data['revenue_growth_actual'] = (rev_fy0 - rev_fy1) / rev_fy1
            else:
                 data['revenue_growth_actual'] = 0.05
        else:
             data['revenue_growth_actual'] = 0.05

    # Historical R&D for Capitalization
    if 'Research And Development' in ann_inc.index:
        # Get past years excluding the most recent (which might overlap with LTM)
        # Actually, the engine needs [R(-1), R(-2), ... R(-N)]
        # ann_inc columns are usually sorted newest to oldest.
        rnd_vals = ann_inc.loc['Research And Development'].tolist()
        data['rnd_history'] = rnd_vals
    else:
        data['rnd_history'] = []

    tax_exp = get_ltm_value(q_inc, 'Tax Provision')
    pre_tax_inc = get_ltm_value(q_inc, 'Pretax Income')

    # Meta / Flags
    country = info.get('country', 'US')
    marginal_rate = TAX_RATES.get(country, 0.25)
    data['marginal_tax_rate'] = marginal_rate

    if pre_tax_inc != 0:
        eff_rate = tax_exp / pre_tax_inc
        # Rule: No negative tax rates... If > 100%, go with marginal.
        if eff_rate < 0:
            data['effective_tax_rate'] = 0.0
        elif eff_rate > 1.0:
            data['effective_tax_rate'] = marginal_rate
        else:
            data['effective_tax_rate'] = eff_rate
    else:
        data['effective_tax_rate'] = 0.0

    # --- Stocks (Point in Time - MRQ) ---
    # Rule: Book equity... include minority or non-controlling interests listed separately.
    stockholders_equity = get_mrq_value(q_bal, 'Stockholders Equity')
    total_equity_gross_mi = get_mrq_value(q_bal, 'Total Equity Gross Minority Interest')

    # If Total Equity (Gross MI) is available and larger than SE, use it implies MI is there.
    # Otherwise fallback to SE.
    if total_equity_gross_mi > 0:
         data['book_equity'] = total_equity_gross_mi
         data['minority_interest'] = total_equity_gross_mi - stockholders_equity
    else:
         data['book_equity'] = stockholders_equity
         # Try to find MI explicitly if Total Equity Gross MI wasn't the aggregate line
         mi_val = get_mrq_value(q_bal, 'Minority Interest')
         if mi_val > 0:
             data['book_equity'] += mi_val
             data['minority_interest'] = mi_val
         else:
             data['minority_interest'] = 0.0

    # Rule: Book value of interest bearing debt... If capitalizing leases [accountants], include those.
    # YF 'Total Debt' typically includes Capital/Finance Leases and often Operating Leases under new standards.
    data['book_debt'] = get_mrq_value(q_bal, 'Total Debt')

    # Cash & Marketable Securities
    # "Cash Cash Equivalents And Short Term Investments" usually captures both.
    data['cash'] = get_mrq_value(q_bal, 'Cash Cash Equivalents And Short Term Investments')
    if data['cash'] == 0:
        # Fallback if the aggregate row is missing
        c = get_mrq_value(q_bal, 'Cash And Cash Equivalents')
        st = get_mrq_value(q_bal, 'Other Short Term Investments')
        data['cash'] = c + st

    # Operating Leases
    # Rule: If accountants are not treating it as debt... enter yes.
    # We assume YF Total Debt includes it if on BS.
    # To avoid double counting, we set lease liability to 0 for the "extra" add-on unless we explicitly want to decouple.
    data['operating_leases_liability'] = 0.0

    # Cross Holdings
    # Rule: Minority holdings in other companies... Investmentin Financial Assets.
    # We check for "Investmentin Financial Assets" or "Other Non Current Assets" if strict investments are missing.
    # But usually 'Investmentin Financial Assets' is the catch-all in YF for this.
    data['cross_holdings'] = get_mrq_value(q_bal, 'Investmentin Financial Assets')

    # Shares
    # Prefer info, fallback to Balance Sheet
    # If as_of_date is set, we prefer Balance Sheet because 'info' is live.
    shares = None
    if not as_of_date:
        shares = info.get('sharesOutstanding')

    if not shares:
        shares = get_mrq_value(q_bal, 'Ordinary Shares Number')

    # If still nothing and we have no date (or even if we do), try info as fallback if we are desperate?
    # But if as_of_date is set, info is wrong. Better to be 0 than wrong?
    # Let's fallback to info ONLY if as_of_date is NOT set or if we decide live data is better than nothing.
    # User prefers "parity", so accuracy matters.
    if not shares and not as_of_date:
         shares = info.get('sharesOutstanding')

    data['shares_outstanding'] = float(shares) if shares else 0.0


    data['rnd_input_flag'] = 'yes' if data['rnd_expense'] > 0 else 'no'
    data['operating_leases_flag'] = 'no' # Simplified for YF path, assuming included in Debt

    # --- Derived Metrics ---
    # Invested Capital = Book Equity (incl MI) + Book Debt - Cash
    inv_cap = data['book_equity'] + data['book_debt'] - data['cash']
    data['invested_capital'] = inv_cap

    if inv_cap > 0 and data['revenues_base'] > 0:
        data['sales_to_capital'] = data['revenues_base'] / inv_cap
    else:
        data['sales_to_capital'] = 0.0

    # Stock Price (Real time)
    # Note: We don't have historical price in this simple extraction unless we query history.
    # For now, just use current price but note it.
    data['stock_price'] = info.get('currentPrice', 0.0)

    data['metadata'] = {
        'ticker': ticker_symbol,
        'source': 'yahoo_finance',
        'currency': info.get('currency', 'USD')
    }

    if as_of_date:
        data['metadata']['as_of_date'] = str(as_of_date)

    return data

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python yf_data_extractor.py <TICKER> [AS_OF_DATE]")
        sys.exit(1)

    ticker = sys.argv[1]
    as_of_date = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        result = extract_data(ticker, as_of_date=as_of_date)
        print(json.dumps(result, indent=4))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
