import yfinance as yf
import json
import pandas as pd

ticker = yf.Ticker("WIPRO.NS")
info = ticker.info

inc_stmt = ticker.income_stmt
bal_sheet = ticker.balance_sheet

print("--- INCOME STATEMENT ---")
print(inc_stmt.to_dict())

print("\n--- BALANCE SHEET ---")
print(bal_sheet.to_dict())

print("\n--- INFO ---")
info_keys = ['sector', 'industry', 'fullTimeEmployees', 'country', 'sharesOutstanding']
for k in info_keys:
    print(f"{k}: {info.get(k)}")

