import yfinance as yf
from typing import Dict, Any
from .base import BaseConnector, ConnectorFactory

class YahooFinanceConnector(BaseConnector):
    """Connector for fetching data from Yahoo Finance."""

    def get_financials(self, ticker: str) -> Dict[str, Any]:
        """Fetch financial statements from Yahoo Finance."""
        stock = yf.Ticker(ticker)
        
        # yfinance returns DataFrames, convert to dict
        # Using keys 'income_statement', 'balance_sheet', 'cash_flow' to match spec or standard
        return {
            "income_statement": stock.income_stmt.to_dict(),
            "balance_sheet": stock.balance_sheet.to_dict(),
            "cash_flow": stock.cashflow.to_dict()
        }

    def get_market_data(self, ticker: str) -> Dict[str, Any]:
        """Fetch market data from Yahoo Finance."""
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Fetch 10-year Treasury Yield as Risk Free Rate proxy
        # using ticker ^TNX (CBOE Interest Rate 10 Year T No)
        try:
            # TODO: Offload this to a background task or cache the value periodically.
            # Ideally, use an async client or run in executor.
            tnx = yf.download("^TNX", period="1d", progress=False)
            if not tnx.empty:
                # Yahoo returns yield as 4.5 for 4.5%, we need decimal 0.045
                # The column access depends on the DataFrame structure
                # yf.download often returns MultiIndex columns or simple columns depending on version
                # Safest is to access by position if we know it's a single ticker download
                
                # Check if 'Close' is in columns
                if 'Close' in tnx.columns:
                     val = tnx['Close'].iloc[-1]
                else:
                     # Fallback to first column if structure is weird (e.g. just one column)
                     val = tnx.iloc[-1, 0]
                
                # If val is a Series (multi-index), take the first value
                if hasattr(val, 'item'):
                     val = val.item()
                elif hasattr(val, 'values'):
                     val = val.values[0]

                risk_free_rate = float(val) / 100.0
            else:
                risk_free_rate = 0.04 # Fallback
        except Exception:
            risk_free_rate = 0.04 # Fallback

        return {
            "price": info.get("currentPrice") or info.get("regularMarketPrice"),
            "beta": info.get("beta"),
            "market_cap": info.get("marketCap"),
            "risk_free_rate": risk_free_rate
        }

# Register the connector
ConnectorFactory.register("yahoo", YahooFinanceConnector)