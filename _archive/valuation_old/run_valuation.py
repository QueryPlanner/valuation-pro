import sys
import os
import json
from dataclasses import asdict

# Add project root to sys.path to allow imports from sibling directories
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# Add sec-data-integration specifically to handle the dash in folder name
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../sec-data-integration')))

try:
    from sec_data_extractor import extract_data
    from valuation_engine.fcff_ginzu.engine import GinzuInputs, compute_ginzu, FORECAST_YEARS
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Please ensure you are running this from the project root or the 'valuation' directory.")
    sys.exit(1)

# --- MOCK DATA SECTION ---
MOCK_DEFAULTS = {
    "stock_price": 150.00,  # Placeholder
    "rev_growth_y1": 0.05,
    "rev_cagr_y2_5": 0.05,
    "margin_target": 0.20,
    "margin_convergence_year": 5,
    "sales_to_capital_1_5": 2.0,
    "sales_to_capital_6_10": 2.0,
    "riskfree_rate_now": 0.0425, # 4.25% (10y Treasury approx)
    "mature_market_erp": 0.0460, # 4.6% (Damodaran)
    "wacc_initial": 0.08, # 8% Initial WACC Guess
    "tax_rate_marginal": 0.25, # 25% Global Avg
    "perpetual_growth_rate": 0.0425, # Matches riskfree
}

def get_user_input_or_mock(prompt, key, cast_type=float):
    """
    Helper to get input or fallback to mock.
    For this CLI, we will just use MOCKs to be automated, but print them.
    """
    val = MOCK_DEFAULTS.get(key)
    print(f"  [MOCK] {key:<25}: {val}")
    return val

def run_valuation(cik_or_ticker):
    print(f"\n--- Starting Valuation for CIK: {cik_or_ticker} ---")
    
    # 1. Fetch REAL Data
    print("\n[1/3] Fetching SEC Data...")
    try:
        sec_data = extract_data(cik_or_ticker)
        if "error" in sec_data:
            print(f"Error fetching SEC data: {sec_data['error']}")
            return
        print(f"  Successfully fetched data for {sec_data.get('metadata', {}).get('latest_filing_date')}")
    except Exception as e:
        print(f"  CRITICAL ERROR extracting data: {e}")
        return

    # 2. Prepare Inputs (Merge Real + Mock)
    print("\n[2/3] Preparing Valuation Inputs...")
    
    # Calculate some derived mocks if possible
    # e.g. Current Margin
    base_rev = sec_data.get('revenues_base', 0)
    base_ebit = sec_data.get('ebit_reported_base', 0)
    current_margin = base_ebit / base_rev if base_rev else 0.10
    
    # Sales to Capital from Data
    sales_to_cap_actual = sec_data.get('sales_to_capital', 0.0)
    # Heuristic: If actual is reasonable (>0.1), use it. Else mock 2.0.
    # sales_to_cap_default = sales_to_cap_actual if sales_to_cap_actual > 0.1 else 2.0
    sales_to_cap_default = 3.0 # FORCED PARITY

    print(f"  [REAL] Revenues (Base)         : ${base_rev:,.2f}")
    print(f"  [REAL] EBIT (Base)             : ${base_ebit:,.2f} (Margin: {current_margin:.1%})")
    print(f"  [REAL] Book Equity             : ${sec_data.get('book_equity', 0):,.2f}")
    print(f"  [REAL] Book Debt               : ${sec_data.get('book_debt', 0):,.2f}")
    print(f"  [REAL] Cash                    : ${sec_data.get('cash', 0):,.2f}")
    print(f"  [REAL] Invested Capital        : ${sec_data.get('invested_capital', 0):,.2f}")
    print(f"  [REAL] Sales/Capital (Actual)  : {sales_to_cap_actual:.2f}")
    print(f"  [REAL] Shares Outstanding      : {sec_data.get('shares_outstanding', 0):,.0f}")
    print(f"  [REAL] Effective Tax Rate      : {sec_data.get('effective_tax_rate', 0):.1%}")

    # Handling R&D and Leases (Simplified for Prototype)
    # We will treat lease liability as debt but ignore the complex EBIT adjustments for now 
    # unless we want to mock the interest portion.
    lease_debt = sec_data.get('operating_leases_liability', 0)
    # Mocking lease interest adjustment as 4% of debt
    lease_ebit_adj = lease_debt * 0.04 
    
    # Construct Inputs Object
    inputs = GinzuInputs(
        # Real Data
        revenues_base=float(base_rev),
        ebit_reported_base=float(base_ebit),
        book_equity=float(sec_data.get('book_equity', 0)),
        book_debt=float(sec_data.get('book_debt', 0)),
        cash=float(sec_data.get('cash', 0)),
        non_operating_assets=float(sec_data.get('cross_holdings', 0)),
        minority_interests=float(sec_data.get('minority_interest', 0)),
        shares_outstanding=float(sec_data.get('shares_outstanding', 0)),
        tax_rate_effective=float(sec_data.get('effective_tax_rate', 0.21)),
        tax_rate_marginal=float(sec_data.get('marginal_tax_rate', 0.21)),

        # Hybrid / Logic
        # capitalize_operating_leases=(sec_data.get('operating_leases_flag') == 'yes'),
        capitalize_operating_leases=False, # FORCED PARITY
        lease_debt=float(lease_debt),
        lease_ebit_adjustment=lease_ebit_adj if sec_data.get('operating_leases_flag') == 'yes' else 0.0,

        capitalize_rnd=False, # DISABLED for now as we lack historical data for capitalization
        
        # Mock / Assumptions
        stock_price=get_user_input_or_mock("Stock Price", "stock_price"),
        rev_growth_y1=get_user_input_or_mock("Revenue Growth (Y1)", "rev_growth_y1"),
        rev_cagr_y2_5=get_user_input_or_mock("Revenue CAGR (Y2-5)", "rev_cagr_y2_5"),
        margin_y1=current_margin, # Assume flat for Y1 base
        margin_target=get_user_input_or_mock("Target Margin", "margin_target"),
        margin_convergence_year=int(get_user_input_or_mock("Convergence Year", "margin_convergence_year")),
        sales_to_capital_1_5=sales_to_cap_default,
        sales_to_capital_6_10=sales_to_cap_default,
        riskfree_rate_now=get_user_input_or_mock("Riskfree Rate", "riskfree_rate_now"),
        mature_market_erp=get_user_input_or_mock("Equity Risk Premium", "mature_market_erp"),
        wacc_initial=get_user_input_or_mock("Initial WACC", "wacc_initial"),
        
        # Stable phase overrides
        override_perpetual_growth=True,
        perpetual_growth_rate=get_user_input_or_mock("Perpetual Growth", "perpetual_growth_rate"),
        
        # Defaults
        has_employee_options=False,
        override_stable_wacc=False,
        override_tax_rate_convergence=False,
        override_riskfree_after_year10=False,
        override_stable_roc=False,
        override_failure_probability=False,
        has_nol_carryforward=False,
        override_reinvestment_lag=False,
        override_trapped_cash=False
    )

    # 3. Compute
    print("\n[3/3] Running Valuation Engine...")
    try:
        results = compute_ginzu(inputs)
    except Exception as e:
        print(f"  Engine Error: {e}")
        return

    # 4. Output
    print("\n" + "="*40)
    print(f"VALUATION RESULTS (CIK: {cik_or_ticker})")
    print("="*40)
    print(f"Value of Operating Assets : ${results.value_of_operating_assets:,.0f}")
    print(f" - Debt                   : ${results.debt:,.0f}")
    print(f" - Minority Interests     : ${inputs.minority_interests:,.0f}")
    print(f" + Cash                   : ${results.cash_adjusted:,.0f}")
    print(f" + Non-Op Assets          : ${inputs.non_operating_assets:,.0f}")
    print("-" * 40)
    print(f"Value of Equity           : ${results.value_of_equity:,.0f}")
    print(f"Value per Share           : ${results.estimated_value_per_share:,.2f}")
    print(f"Price (Mock)              : ${inputs.stock_price:,.2f}")
    print(f"Upside / (Downside)       : {(results.estimated_value_per_share / inputs.stock_price - 1.0):.1%}")
    print("="*40)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_valuation.py <CIK>")
        sys.exit(1)
    
    run_valuation(sys.argv[1])
