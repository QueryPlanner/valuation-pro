from typing import Any, Dict

import datetime
import pandas as pd
import yfinance as yf

from .base import BaseConnector, ConnectorFactory

# Country Tax Rates (Simplified Mock)
TAX_RATES = {"US": 0.21, "United States": 0.21, "IE": 0.125, "GB": 0.25, "CN": 0.25, "DE": 0.30, "JP": 0.3062}


class YahooFinanceConnector(BaseConnector):
    """Connector for fetching data from Yahoo Finance."""

    def get_financials(self, ticker: str, as_of_date: str = None) -> Dict[str, Any]:
        """Fetch raw financial statements from Yahoo Finance."""
        stock = yf.Ticker(ticker)
        inc = stock.income_stmt
        bal = stock.balance_sheet
        cf = stock.cashflow
        
        if as_of_date:
            inc = self._filter_cols_by_date(inc, as_of_date)
            bal = self._filter_cols_by_date(bal, as_of_date)
            cf = self._filter_cols_by_date(cf, as_of_date)

        return {
            "income_statement": inc.to_dict() if not inc.empty else {},
            "balance_sheet": bal.to_dict() if not bal.empty else {},
            "cash_flow": cf.to_dict() if not cf.empty else {},
        }

    def get_market_data(self, ticker: str, as_of_date: str = None) -> Dict[str, Any]:
        """Fetch market data from Yahoo Finance."""
        stock = yf.Ticker(ticker)
        info = stock.info

        risk_free_rate = self._get_risk_free_rate()
        
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        
        if as_of_date:
            try:
                # fetch historical price
                end_dt = datetime.datetime.strptime(as_of_date, "%Y-%m-%d") + datetime.timedelta(days=1)
                hist = stock.history(end=end_dt.strftime("%Y-%m-%d"))
                if not hist.empty:
                    price = float(hist["Close"].iloc[-1])
            except Exception:
                pass

        return {
            "price": price,
            "beta": info.get("beta"),
            "market_cap": info.get("marketCap"),
            "shares_outstanding": info.get("sharesOutstanding"),
            "risk_free_rate": risk_free_rate,
        }

    def get_valuation_inputs(self, ticker: str, as_of_date: str = None) -> Dict[str, Any]:
        """
        Fetch and normalize data specifically for the Valuation Engine.
        Implements LTM calculations and fallback logic.
        """
        stock = yf.Ticker(ticker)

        # 1. Fetch Dataframes
        q_inc = stock.quarterly_financials
        q_bal = stock.quarterly_balance_sheet
        ann_inc = stock.financials
        info = stock.info


        # --- Date Filtering ---
        if as_of_date:
            q_inc = self._filter_cols_by_date(q_inc, as_of_date)
            q_bal = self._filter_cols_by_date(q_bal, as_of_date)
            ann_inc = self._filter_cols_by_date(ann_inc, as_of_date)

            # Fallback to annual balance sheet if quarterly is empty after filtering
            if q_bal.empty:
                ann_bal = stock.balance_sheet
                q_bal = self._filter_cols_by_date(ann_bal, as_of_date)


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
            rev_base = self._get_mrq_value(ann_inc, "Total Revenue")
            data["ebit_reported_base"] = self._get_mrq_value(ann_inc, "Operating Income")
            data["rnd_expense"] = self._get_mrq_value(ann_inc, "Research And Development")
            tax_exp = self._get_mrq_value(ann_inc, "Tax Provision")
            pre_tax_inc = self._get_mrq_value(ann_inc, "Pretax Income")
        else:
            rev_base = self._get_ltm_value(q_inc, "Total Revenue")
            data["ebit_reported_base"] = self._get_ltm_value(q_inc, "Operating Income")
            data["rnd_expense"] = self._get_ltm_value(q_inc, "Research And Development")
            tax_exp = self._get_ltm_value(q_inc, "Tax Provision")
            pre_tax_inc = self._get_ltm_value(q_inc, "Pretax Income")

        # Heuristic: Small positive number for pre-revenue
        data["revenues_base"] = rev_base if rev_base > 0 else 1000.0

        # 3. R&D History (for capitalization)
        if not ann_inc.empty and "Research And Development" in ann_inc.index:
            # Get historical values sorted newest to oldest
            rnd_vals = ann_inc.loc["Research And Development"].tolist()
            # Replace NaNs with 0.0
            data["rnd_history"] = [float(x) if pd.notna(x) else 0.0 for x in rnd_vals]
        else:
            data["rnd_history"] = []

        # 4. Stocks (Point in Time - MRQ)
        if not q_bal.empty:
            # Book Equity: Include minority interest if consolidated
            stockholders_equity = self._get_mrq_value(q_bal, "Stockholders Equity")
            total_equity_gross_mi = self._get_mrq_value(q_bal, "Total Equity Gross Minority Interest")

            if total_equity_gross_mi > 0:
                data["book_equity"] = total_equity_gross_mi
                data["minority_interest"] = total_equity_gross_mi - stockholders_equity
            else:
                data["book_equity"] = stockholders_equity
                mi_val = self._get_mrq_value(q_bal, "Minority Interest")
                data["minority_interest"] = mi_val if mi_val > 0 else 0.0

            # Debt & Cash
            data["book_debt"] = self._get_mrq_value(q_bal, "Total Debt")

            cash_equiv = self._get_mrq_value(q_bal, "Cash Cash Equivalents And Short Term Investments")
            if cash_equiv == 0:
                c = self._get_mrq_value(q_bal, "Cash And Cash Equivalents")
                st = self._get_mrq_value(q_bal, "Other Short Term Investments")
                cash_equiv = c + st
            data["cash"] = cash_equiv

            data["cross_holdings"] = self._get_mrq_value(q_bal, "Investmentin Financial Assets")
        else:
            # Fallback if BS is empty
            data["book_equity"] = 0.0
            data["book_debt"] = 0.0
            data["cash"] = 0.0
            data["minority_interest"] = 0.0
            data["cross_holdings"] = 0.0

        # 5. Shares & Price
        shares = info.get("sharesOutstanding")
        if not shares and not q_bal.empty:
            shares = self._get_mrq_value(q_bal, "Ordinary Shares Number")
        data["shares_outstanding"] = float(shares) if shares else 0.0
        data["stock_price"] = info.get("currentPrice", 0.0)

        # 6. Tax Rates
        country = info.get("country", "US")
        marginal_rate = TAX_RATES.get(country, 0.25)
        data["marginal_tax_rate"] = marginal_rate

        if pre_tax_inc != 0:
            eff_rate = tax_exp / pre_tax_inc
            if eff_rate < 0:
                data["effective_tax_rate"] = 0.0
            elif eff_rate > 1.0:
                data["effective_tax_rate"] = marginal_rate
            else:
                data["effective_tax_rate"] = eff_rate
        else:
            data["effective_tax_rate"] = 0.0

        # 7. Metadata / Flags
        data["operating_leases_flag"] = "no"  # YF simplifies this into Debt usually
        data["risk_free_rate"] = self._get_risk_free_rate()

        return data

    # --- Helpers ---
    def _filter_cols_by_date(self, df: pd.DataFrame, as_of_date: str) -> pd.DataFrame:
        if df.empty or not as_of_date: return df
        try:
            dt_limit = datetime.datetime.strptime(as_of_date, "%Y-%m-%d").date()
        except ValueError:
            return df
        
        valid_cols = [c for c in df.columns if hasattr(c, 'date') and c.date() <= dt_limit]
        if not valid_cols:
            valid_cols = []
            for c in df.columns:
                try:
                    if isinstance(c, str):
                        c_date = datetime.datetime.strptime(c, "%Y-%m-%d").date()
                        if c_date <= dt_limit: valid_cols.append(c)
                    elif hasattr(c, 'date') and c.date() <= dt_limit:
                        valid_cols.append(c)
                except: pass
        return df[valid_cols]


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

    def _get_risk_free_rate(self) -> float:
        try:
            tnx = yf.download("^TNX", period="1d", progress=False)
            if not tnx.empty:
                if "Close" in tnx.columns:
                    val = tnx["Close"].iloc[-1]
                else:
                    val = tnx.iloc[-1, 0]

                if hasattr(val, "item"):
                    val = val.item()
                elif hasattr(val, "values"):
                    val = val.values[0]
                return float(val) / 100.0
        except Exception:
            pass
        return 0.04  # Fallback


# Register the connector
ConnectorFactory.register("yahoo", YahooFinanceConnector)
