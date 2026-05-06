import os
import csv
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

load_dotenv()

from valuation_service.services.ai_pipeline import extract_ai_inputs
from valuation_engine.inputs_builder import build_ginzu_inputs
from valuation_engine.engine import compute_ginzu
from valuation_service.connectors.yahoo import YahooFinanceConnector

# List of companies provided by the user
COMPANIES = [
    "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "BAJAJ-AUTO", "BPCL", 
    "BHARTIARTL", "BRITANNIA", "CIPLA", "COALINDIA", "DIVISLAB", "DRREDDY", 
    "EICHERMOT", "GRASIM", "HCLTECH", "HEROMOTOCO", "HINDALCO", "HINDUNILVR", 
    "ITC", "INFY", "JSWSTEEL", "LT", "M&M", "MARUTI", "NTPC", "NESTLEIND", 
    "ONGC", "POWERGRID", "RELIANCE", "SHREECEM", "SUNPHARMA", "TCS", 
    "TATACONSUM", "TATASTEEL", "TECHM", "TITAN", "ULTRACEMCO", "UPL", "WIPRO"
]

csv_lock = threading.Lock()

def ensure_xbrl_data(symbol: str):
    """Ensure XBRL data is downloaded for the symbol."""
    metadata_path = Path("valuation_data") / symbol / "valuation_metadata.json"
    if not metadata_path.exists():
        print(f"[{symbol}] Downloading XBRL data...")
        try:
            subprocess.run(["uv", "run", "xbrl-downloader", symbol], check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            print(f"[{symbol}] Failed to download XBRL data.")
            return False
    return True

def process_company(symbol: str, yf_connector: YahooFinanceConnector, csv_file: str, header_written: bool):
    print(f"\n==========================================")
    print(f"Processing {symbol}...")
    print(f"==========================================")
    
    # 1. Download XBRL
    if not ensure_xbrl_data(symbol):
        return None
        
    # 2. Run AI Extraction
    try:
        print(f"[{symbol}] Extracting AI inputs...")
        yf_ticker = f"{symbol}.NS"
        ai_inputs = extract_ai_inputs(symbol, yf_ticker)
        
        rationale = ai_inputs.get("rationale", "")
        if isinstance(rationale, dict):
            import json
            rationale = json.dumps(rationale)
        
        if "rationale" in ai_inputs:
            del ai_inputs["rationale"]
            
    except Exception as e:
        print(f"[{symbol}] AI Extraction failed: {e}")
        return None

    # 3. Fetch Market Data
    print(f"[{symbol}] Fetching Market Data...")
    try:
        market_data = yf_connector.get_valuation_inputs(yf_ticker)
    except Exception as e:
        print(f"[{symbol}] Yahoo Finance extraction failed: {e}")
        return None

    # 4. Compute Valuation
    print(f"[{symbol}] Computing Valuation...")
    try:
        ginzu_inputs = build_ginzu_inputs(data=market_data, assumptions=ai_inputs)
        outputs = compute_ginzu(ginzu_inputs)
        
        val_per_share = outputs.estimated_value_per_share
        current_price = ginzu_inputs.stock_price
        
        diff_pct = ((val_per_share - current_price) / current_price * 100) if current_price else 0
        status = "Undervalued" if diff_pct > 0 else "Overvalued"
        
        result = {
            "Symbol": symbol,
            "Current Market Price": round(current_price, 2),
            "Estimated Value per Share": round(val_per_share, 2),
            "Status": status,
            "Difference %": round(diff_pct, 2),
            "revenues_base": ai_inputs.get("revenues_base"),
            "ebit_reported_base": ai_inputs.get("ebit_reported_base"),
            "margin_y1": ai_inputs.get("margin_y1"),
            "rev_cagr_y2_5": ai_inputs.get("rev_cagr_y2_5"),
            "sales_to_capital_1_5": ai_inputs.get("sales_to_capital_1_5"),
            "tax_rate_effective": ai_inputs.get("tax_rate_effective"),
            "rationale": rationale.replace('\n', ' ')
        }
        
        # Write to CSV in a thread-safe manner
        with csv_lock:
            file_exists = os.path.exists(csv_file) and os.path.getsize(csv_file) > 0
            with open(csv_file, "a", newline="", encoding="utf-8") as output_file:
                dict_writer = csv.DictWriter(output_file, result.keys())
                if not file_exists and not header_written:
                    dict_writer.writeheader()
                dict_writer.writerow(result)
                
        print(f"[{symbol}] Success! Value: {val_per_share:.2f} | Price: {current_price:.2f} | Diff: {diff_pct:.2f}%")
        return result
    except Exception as e:
        print(f"[{symbol}] Valuation computation failed: {e}")
        return None

def main():
    results = []
    yf_connector = YahooFinanceConnector()
    csv_file = "nifty_valuation_results.csv"
    
    processed_symbols = set()
    header_written = False

    if os.path.exists(csv_file):
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if "Symbol" in row:
                    processed_symbols.add(row["Symbol"])
        if len(processed_symbols) > 0:
            header_written = True

    symbols_to_process = [s for s in COMPANIES if s not in processed_symbols]

    print(f"Symbols to process: {symbols_to_process}")

    # Use ThreadPoolExecutor to parallelize
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_symbol = {
            executor.submit(process_company, symbol, yf_connector, csv_file, header_written): symbol
            for symbol in symbols_to_process
        }
        
        for future in as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                res = future.result()
                if res:
                    results.append(res)
            except Exception as exc:
                print(f"{symbol} generated an exception: {exc}")

    print(f"\nSuccessfully processed {len(results)} additional companies.")

if __name__ == "__main__":
    main()
