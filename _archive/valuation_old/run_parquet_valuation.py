import os
import sys

# Add project root to sys.path to allow imports from sibling directories
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# Add sec-data-integration specifically
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../sec-data-integration')))

try:
    # Import from the NEW parquet extractor
    from parquet_sec_extractor import extract_data
    from valuation_engine.fcff_ginzu.engine import FORECAST_YEARS, GinzuInputs, compute_ginzu
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

# --- MOCK DATA SECTION ---
MOCK_DEFAULTS = {
    "stock_price": 150.00,
    "rev_growth_y1": 0.05,
    "rev_cagr_y2_5": 0.05,
    "margin_target": 0.20,
    "margin_convergence_year": 5,
    "sales_to_capital_1_5": 2.0,
    "sales_to_capital_6_10": 2.0,
    "riskfree_rate_now": 0.0425,
    "mature_market_erp": 0.0460,
    "wacc_initial": 0.08,
    "tax_rate_marginal": 0.25,
    "perpetual_growth_rate": 0.0425,
}

def get_user_input_or_mock(prompt, key, cast_type=float):
    val = MOCK_DEFAULTS.get(key)
    print(f"  [MOCK] {key:<25}: {val}")
    return val

def run_valuation(cik_or_ticker):
    print(f"\n--- Starting Parquet-Based Valuation for CIK: {cik_or_ticker} ---")

    # 1. Fetch REAL Data (from Parquet)
    print("\n[1/3] Fetching SEC Data (Local Parquet)...")
    try:
        sec_data = extract_data(cik_or_ticker)
        if "error" in sec_data:
            print(f"Error fetching SEC data: {sec_data['error']}")
            return
        print(f"  Successfully fetched data for {sec_data.get('metadata', {}).get('latest_filing_date')}")
    except Exception as e:
        print(f"  CRITICAL ERROR extracting data: {e}")
        import traceback
        traceback.print_exc()
        return

    # 2. Prepare Inputs (Merge Real + Mock)
    print("\n[2/3] Preparing Valuation Inputs...")

    base_rev = sec_data.get('revenues_base', 0)
    base_ebit = sec_data.get('ebit_reported_base', 0)
    current_margin = base_ebit / base_rev if base_rev else 0.10

    sales_to_cap_actual = sec_data.get('sales_to_capital', 0.0)
    sales_to_cap_default = sales_to_cap_actual if sales_to_cap_actual > 0.1 else 2.0

    print(f"  [REAL] Revenues (Base)         : ${base_rev:,.2f}")
    print(f"  [REAL] EBIT (Base)             : ${base_ebit:,.2f} (Margin: {current_margin:.1%})")
    print(f"  [REAL] Book Equity             : ${sec_data.get('book_equity', 0):,.2f}")
    print(f"  [REAL] Book Debt               : ${sec_data.get('book_debt', 0):,.2f}")
    print(f"  [REAL] Cash                    : ${sec_data.get('cash', 0):,.2f}")
    print(f"  [REAL] Invested Capital        : ${sec_data.get('invested_capital', 0):,.2f}")
    print(f"  [REAL] Sales/Capital (Actual)  : {sales_to_cap_actual:.2f}")

    lease_debt = sec_data.get('operating_leases_liability', 0)
    lease_ebit_adj = lease_debt * 0.04

    inputs = GinzuInputs(
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

        capitalize_operating_leases=(sec_data.get('operating_leases_flag') == 'yes'),
        lease_debt=float(lease_debt),
        lease_ebit_adjustment=lease_ebit_adj if sec_data.get('operating_leases_flag') == 'yes' else 0.0,

        capitalize_rnd=False,

        stock_price=get_user_input_or_mock("Stock Price", "stock_price"),
        rev_growth_y1=get_user_input_or_mock("Revenue Growth (Y1)", "rev_growth_y1"),
        rev_cagr_y2_5=get_user_input_or_mock("Revenue CAGR (Y2-5)", "rev_cagr_y2_5"),
        margin_y1=current_margin,
        margin_target=get_user_input_or_mock("Target Margin", "margin_target"),
        margin_convergence_year=int(get_user_input_or_mock("Convergence Year", "margin_convergence_year")),
        sales_to_capital_1_5=sales_to_cap_default,
        sales_to_capital_6_10=sales_to_cap_default,
        riskfree_rate_now=get_user_input_or_mock("Riskfree Rate", "riskfree_rate_now"),
        mature_market_erp=get_user_input_or_mock("Equity Risk Premium", "mature_market_erp"),
        wacc_initial=get_user_input_or_mock("Initial WACC", "wacc_initial"),

        override_perpetual_growth=True,
        perpetual_growth_rate=get_user_input_or_mock("Perpetual Growth", "perpetual_growth_rate"),

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
    print(f"Value of Equity           : ${results.value_of_equity:,.0f}")
    print(f"Value per Share           : ${results.estimated_value_per_share:,.2f}")
    print(f"Price (Mock)              : ${inputs.stock_price:,.2f}")
    print(f"Upside / (Downside)       : {(results.estimated_value_per_share / inputs.stock_price - 1.0):.1%}")
    print("="*40)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_parquet_valuation.py <CIK>")
        sys.exit(1)

    run_valuation(sys.argv[1])
