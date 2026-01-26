import sys
import os
import json

# Add current directory to path so we can import the extractor
sys.path.append(os.getcwd())

from sec_data_extractor import extract_data

COMPANIES = {
    "Meta": "1326801",
    "Amazon": "1018724",
    "Apple": "320193",
    "Netflix": "1065280",
    "Microsoft": "789019",
    "Tesla": "1318605",
    "Coca-Cola": "21344"
}

def run_tests():
    results = {}
    for name, cik in COMPANIES.items():
        print(f"Testing {name} ({cik})...")
        try:
            data = extract_data(cik)
            if "error" in data:
                print(f"  FAILED: {data['error']}")
                continue
                
            # Check key fields for 0.0 which might indicate missing tags
            missing = []
            keys_to_check = ['revenues_base', 'ebit_reported_base', 'book_equity', 'cash', 'book_debt']
            
            summary = []
            for k in keys_to_check:
                val = data.get(k, 0)
                summary.append(f"{k}={val:,.0f}")
                if val == 0:
                    # EBIT might be negative, but exactly 0.0 is suspicious for these giants
                    # Book debt might be 0 for some (like Meta used to be), but rare.
                    missing.append(k)
            
            print(f"  OK. {', '.join(summary)}")
            if missing:
                print(f"  WARNING: Potential missing data for: {missing}")
                
        except Exception as e:
            print(f"  CRASH: {e}")

if __name__ == "__main__":
    run_tests()
