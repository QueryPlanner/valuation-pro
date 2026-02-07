import yfinance as yf
import pandas as pd
import datetime
from typing import Dict, Any, List, Optional
from .base import BaseConnector, ConnectorFactory

# Country Tax Rates (Simplified Mock)
TAX_RATES = {
    "US": 0.21, "United States": 0.21,
    "IE": 0.125, "GB": 0.25, "CN": 0.25, "DE": 0.30, "JP": 0.3062
}

class YahooFinanceConnector(BaseConnector):
    """Connector for fetching data from Yahoo Finance."""

    def get_financials(self, ticker: str) -> Dict[str, Any]:
        """Fetch raw financial statements from Yahoo Finance."""
        stock = yf.Ticker(ticker)
        return {
            "income_statement": stock.income_stmt.to_dict(),
            "balance_sheet": stock.balance_sheet.to_dict(),
            "cash_flow": stock.cashflow.to_dict()
        }

    def get_market_data(self, ticker: str) -> Dict[str, Any]:
        """Fetch market data from Yahoo Finance."""
        stock = yf.Ticker(ticker)
        info = stock.info
        
        risk_free_rate = self._get_risk_free_rate()

        return {
            "price": info.get("currentPrice") or info.get("regularMarketPrice"),
            "beta": info.get("beta"),
            "market_cap": info.get("marketCap"),
            "shares_outstanding": info.get("sharesOutstanding"),
            "risk_free_rate": risk_free_rate
        }

    def get_valuation_inputs(self, ticker: str, as_of_date: Optional[datetime.date] = None) -> Dict[str, Any]:
        """
        Fetch and normalize data specifically for the Valuation Engine.
        Implements LTM calculations and fallback logic.
        
        :param as_of_date: If provided, fetches data as if it were this date.
        """
        stock = yf.Ticker(ticker)
        
        # 1. Fetch Dataframes
        q_inc = stock.quarterly_financials
        q_bal = stock.quarterly_balance_sheet
        ann_inc = stock.financials
        ann_bal = stock.balance_sheet
        info = stock.info

        # Filter for retrospective valuation
        if as_of_date:
            q_inc = self._filter_dataframe_by_date(q_inc, as_of_date)
            q_bal = self._filter_dataframe_by_date(q_bal, as_of_date)
            ann_inc = self._filter_dataframe_by_date(ann_inc, as_of_date)
            ann_bal = self._filter_dataframe_by_date(ann_bal, as_of_date)

        data = {}

        # 2. Flows (LTM Calculation)
        # Check if we have enough quarterly data for LTM (need 4 quarters)
        use_annual_fallback = False
        if q_inc.empty or len(q_inc.columns) < 4:
            use_annual_fallback = True
            if ann_inc.empty:
                # Critical failure if neither exists, but we return 0s to let upper layers handle
                pass

        if use_annual_fallback:
            rev_base = self._get_mrq_value(ann_inc, 'Total Revenue')
            data['ebit_reported_base'] = self._get_mrq_value(ann_inc, 'Operating Income')
            data['rnd_expense'] = self._get_mrq_value(ann_inc, 'Research And Development')
            tax_exp = self._get_mrq_value(ann_inc, 'Tax Provision')
            pre_tax_inc = self._get_mrq_value(ann_inc, 'Pretax Income')
        else:
            rev_base = self._get_ltm_value(q_inc, 'Total Revenue')
            data['ebit_reported_base'] = self._get_ltm_value(q_inc, 'Operating Income')
            data['rnd_expense'] = self._get_ltm_value(q_inc, 'Research And Development')
            tax_exp = self._get_ltm_value(q_inc, 'Tax Provision')
            pre_tax_inc = self._get_ltm_value(q_inc, 'Pretax Income')

        # Heuristic: Small positive number for pre-revenue
        data['revenues_base'] = rev_base if rev_base > 0 else 1000.0

        # 3. R&D History (for capitalization)
        if not ann_inc.empty and 'Research And Development' in ann_inc.index:
            # Get historical values sorted newest to oldest
            rnd_vals = ann_inc.loc['Research And Development'].tolist()
            # Replace NaNs with 0.0
            data['rnd_history'] = [float(x) if pd.notna(x) else 0.0 for x in rnd_vals]
        else:
            data['rnd_history'] = []

        # 4. Stocks (Point in Time - MRQ)
        # Use Quarterly Balance Sheet if available, else Annual
        bs_df = q_bal if not q_bal.empty else ann_bal

        if not bs_df.empty:
            # Book Equity: Include minority interest if consolidated
            stockholders_equity = self._get_mrq_value(bs_df, 'Stockholders Equity')
            total_equity_gross_mi = self._get_mrq_value(bs_df, 'Total Equity Gross Minority Interest')
            
            if total_equity_gross_mi > 0:
                data['book_equity'] = total_equity_gross_mi
                data['minority_interest'] = total_equity_gross_mi - stockholders_equity
            else:
                data['book_equity'] = stockholders_equity
                mi_val = self._get_mrq_value(bs_df, 'Minority Interest')
                data['minority_interest'] = mi_val if mi_val > 0 else 0.0

            # Debt & Cash
            data['book_debt'] = self._get_mrq_value(bs_df, 'Total Debt')
            
            # Try to fetch Capital Lease Obligations for potential adjustment later
            leases = self._get_mrq_value(bs_df, 'Capital Lease Obligations')
            if leases == 0:
                leases = self._get_mrq_value(bs_df, 'Long Term Capital Lease Obligation')
            data['capital_lease_obligations'] = leases
            
            cash_equiv = self._get_mrq_value(bs_df, 'Cash Cash Equivalents And Short Term Investments')
            if cash_equiv == 0:
                c = self._get_mrq_value(bs_df, 'Cash And Cash Equivalents')
                st = self._get_mrq_value(bs_df, 'Other Short Term Investments')
                cash_equiv = c + st
            data['cash'] = cash_equiv
            
            data['cross_holdings'] = self._get_mrq_value(bs_df, 'Investmentin Financial Assets')
        else:
            # Fallback if BS is empty
            data['book_equity'] = 0.0
            data['book_debt'] = 0.0
            data['cash'] = 0.0
            data['minority_interest'] = 0.0
            data['cross_holdings'] = 0.0

        # 5. Shares & Price
        shares = None
        price = 0.0
        
        if as_of_date:
            # Retrospective: Use Balance Sheet shares + Historical Price
            if not bs_df.empty:
                shares = self._get_mrq_value(bs_df, 'Ordinary Shares Number')
            price = self._get_historical_price(ticker, as_of_date)
        else:
            # Current: Use Info
            shares = info.get('sharesOutstanding')
            if not shares and not bs_df.empty:
                shares = self._get_mrq_value(bs_df, 'Ordinary Shares Number')
            price = info.get('currentPrice', 0.0)

        data['shares_outstanding'] = float(shares) if shares else 0.0
        data['stock_price'] = price

        # 6. Tax Rates
        country = info.get('country', 'US')
        marginal_rate = TAX_RATES.get(country, 0.25)
        data['marginal_tax_rate'] = marginal_rate

        if pre_tax_inc != 0:
            eff_rate = tax_exp / pre_tax_inc
            if eff_rate < 0:
                data['effective_tax_rate'] = 0.0
            elif eff_rate > 1.0:
                data['effective_tax_rate'] = marginal_rate
            else:
                data['effective_tax_rate'] = eff_rate
        else:
            data['effective_tax_rate'] = 0.0
            
        # 7. Metadata / Flags
        data['operating_leases_flag'] = 'no' # YF simplifies this into Debt usually
        data['risk_free_rate'] = self._get_risk_free_rate(as_of_date)
        
        return data

    # --- Helpers ---
    
    def _filter_dataframe_by_date(self, df: pd.DataFrame, cutoff_date: datetime.date) -> pd.DataFrame:
        """Keeps columns where date <= cutoff_date."""
        if df.empty:
            return df
        # Ensure columns are datetime objects
        # YF columns are usually Timestamps.
        # We need to iterate and filter.
        valid_cols = []
        for col in df.columns:
            try:
                col_date = pd.to_datetime(col).date()
                if col_date <= cutoff_date:
                    valid_cols.append(col)
            except:
                pass # Ignore non-date columns if any
        
        return df[valid_cols]

    def _get_historical_price(self, ticker: str, date: datetime.date) -> float:
        """Fetches closing price for a specific date (or nearest previous trading day)."""
        # Fetch a small window around the date
        start = date - datetime.timedelta(days=5)
        end = date + datetime.timedelta(days=1)
        try:
            hist = yf.download(ticker, start=start, end=end, progress=False)
            if not hist.empty:
                # Get the last available close up to the date
                # hist index is DatetimeIndex
                # filter rows <= date
                mask = hist.index.date <= date
                filtered = hist[mask]
                if not filtered.empty:
                    val = filtered['Close'].iloc[-1]
                    if hasattr(val, 'item'): val = val.item()
                    elif hasattr(val, 'values'): val = val.values[0]
                    return float(val)
        except Exception:
            pass
        return 0.0

    def _get_ltm_value(self, df: pd.DataFrame, row_name: str, num_quarters: int = 4) -> float:
        """Sums `num_quarters` values for a given row."""
        if row_name not in df.index:
            return 0.0
        # Columns are usually dates descending (Newest -> Oldest)
        # Take first N columns
        subset = df.loc[row_name].iloc[0:num_quarters]
        return float(subset.sum())

    def _get_mrq_value(self, df: pd.DataFrame, row_name: str) -> float:
        """Gets the value from the Most Recent Quarter (first column)."""
        if row_name not in df.index:
            return 0.0
        val = df.loc[row_name].iloc[0]
        return float(val) if pd.notna(val) else 0.0

    def _get_risk_free_rate(self, as_of_date: Optional[datetime.date] = None) -> float:
        try:
            end_date = None
            if as_of_date:
                start = as_of_date - datetime.timedelta(days=5)
                end = as_of_date + datetime.timedelta(days=1)
                tnx = yf.download("^TNX", start=start, end=end, progress=False)
            else:
                tnx = yf.download("^TNX", period="1d", progress=False)
                
            if not tnx.empty:
                # If historical, filter up to date
                if as_of_date:
                    mask = tnx.index.date <= as_of_date
                    tnx = tnx[mask]
                
                if not tnx.empty:
                    if 'Close' in tnx.columns:
                         val = tnx['Close'].iloc[-1]
                    else:
                         val = tnx.iloc[-1, 0]
                    
                    if hasattr(val, 'item'): val = val.item()
                    elif hasattr(val, 'values'): val = val.values[0]
                    return float(val) / 100.0
        except Exception:
            pass
        return 0.04  # Fallback

# Register the connector
ConnectorFactory.register("yahoo", YahooFinanceConnector)
