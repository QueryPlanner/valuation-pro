import yfinance as yf
import json

ticker = yf.Ticker("WIPRO.NS")
info = ticker.info

inc_stmt = ticker.income_stmt
bal_sheet = ticker.balance_sheet

print("Income Statement:")
print(inc_stmt.iloc[:, 0:2])

print("\nBalance Sheet:")
print(bal_sheet.iloc[:, 0:2])

print(f"\nShares Outstanding: {info.get('sharesOutstanding')}")
