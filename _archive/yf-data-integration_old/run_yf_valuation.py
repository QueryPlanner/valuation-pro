import math
import os
import sys

# Add project root to sys.path to allow imports from sibling directories
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from valuation_engine.fcff_ginzu.engine import (
        GinzuInputs,
        RnDCapitalizationInputs,
        compute_ginzu,
        compute_rnd_capitalization_adjustments,
    )
    from yf_data_extractor import extract_data
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

# --- MOCK DATA SECTION (Same as run_valuation.py) ---
MOCK_DEFAULTS = {
    "rev_growth_y1": 0.05,
    "rev_cagr_y2_5": 0.05,
    "margin_target": 0.20,
    "margin_convergence_year": 5,
    "sales_to_capital_1_5": 2.0,
    "sales_to_capital_6_10": 2.0,
    "riskfree_rate_now": 0.0425, # 4.25% (10y Treasury approx)
    "mature_market_erp": 0.0460, # 4.6% (Damodaran)
    "wacc_initial": 0.08, # 8% Initial WACC Guess
    "perpetual_growth_rate": 0.0425, # Matches riskfree
}

def get_user_input_or_mock(prompt, key, default_val=None):
    """
    Helper to get input or fallback to mock.
    """
    if default_val is not None:
        val = default_val
    else:
        val = MOCK_DEFAULTS.get(key)
    print(f"  [MOCK] {key:<25}: {val}")
    return val

def run_valuation(ticker):
    print(f"\n--- Starting Valuation for Ticker: {ticker} (Source: Yahoo Finance) ---")

    # 1. Fetch REAL Data
    print("\n[1/3] Fetching Yahoo Finance Data...")
    try:
        yf_data = extract_data(ticker)
        if "error" in yf_data:
            print(f"Error fetching data: {yf_data['error']}")
            return
        print(f"  Successfully fetched data for {ticker}")
    except Exception as e:
        print(f"  CRITICAL ERROR extracting data: {e}")
        return

    # 2. Prepare Inputs (Merge Real + Mock)
    print("\n[2/3] Preparing Valuation Inputs...")

    base_rev = yf_data.get('revenues_base', 0)
    reported_ebit = yf_data.get('ebit_reported_base', 0)

    # Sales to Capital from Data
    sales_to_cap_actual = yf_data.get('sales_to_capital', 0.0)
    # Heuristic: If actual is reasonable (>0.1), use it. Else mock 2.0.
    # sales_to_cap_default = sales_to_cap_actual if sales_to_cap_actual > 0.1 else 2.0
    sales_to_cap_default = 3.0 # FORCED PARITY

    # Stock Price from YF
    stock_price = yf_data.get('stock_price', 100.0)

    print(f"  [REAL] Revenues (Base)         : ${base_rev:,.2f}")
    print(f"  [REAL] EBIT (Reported)         : ${reported_ebit:,.2f}")
    print(f"  [REAL] Book Equity             : ${yf_data.get('book_equity', 0):,.2f}")
    print(f"  [REAL] Book Debt               : ${yf_data.get('book_debt', 0):,.2f}")
    print(f"  [REAL] Cash                    : ${yf_data.get('cash', 0):,.2f}")
    print(f"  [REAL] Invested Capital        : ${yf_data.get('invested_capital', 0):,.2f}")
    print(f"  [REAL] Sales/Capital (Actual)  : {sales_to_cap_actual:.2f}")
    print(f"  [REAL] Shares Outstanding      : {yf_data.get('shares_outstanding', 0):,.0f}")
    print(f"  [REAL] Effective Tax Rate      : {yf_data.get('effective_tax_rate', 0):.1%}")
    print(f"  [REAL] Stock Price             : ${stock_price:,.2f}")

    # R&D Capitalization Logic
    rnd_asset = 0.0
    rnd_ebit_adj = 0.0
    capitalize_rnd = False

    # FORCED PARITY: Disable R&D Capitalization for comparison
    # if yf_data.get('rnd_history') and len(yf_data['rnd_history']) > 0:
    if False:
        print("\n[2.1] Capitalizing R&D...")
        amort_years = 5
        history = yf_data['rnd_history']
        current_rnd = yf_data.get('rnd_expense', 0)

        past_rnd = []
        for i in range(amort_years):
            if i < len(history):
                val = float(history[i])
                if math.isnan(val):
                    val = 0.0
                past_rnd.append(val)
            else:
                past_rnd.append(0.0)

        try:
            rnd_inputs = RnDCapitalizationInputs(
                amortization_years=amort_years,
                current_year_rnd_expense=float(current_rnd),
                past_year_rnd_expenses=past_rnd
            )
            rnd_asset, rnd_ebit_adj = compute_rnd_capitalization_adjustments(rnd_inputs)
            capitalize_rnd = True
            print(f"  [ADJ] R&D Asset Value        : ${rnd_asset:,.2f}")
            print(f"  [ADJ] EBIT Adjustment        : ${rnd_ebit_adj:,.2f}")
        except Exception as e:
            print(f"  Warning: R&D Capitalization failed: {e}")

    # Adjusted Base Metrics for Guidance
    adjusted_ebit = reported_ebit + rnd_ebit_adj
    adjusted_margin = adjusted_ebit / base_rev if base_rev > 0 else 0.10
    print(f"  [ADJ] Adjusted EBIT          : ${adjusted_ebit:,.2f} (Margin: {adjusted_margin:.1%})")

    # Guidance Defaults
    # default_rev_growth = yf_data.get('revenue_growth_actual', 0.05)
    default_rev_growth = 0.05 # FORCED PARITY
    default_sales_to_cap = sales_to_cap_default # Already computed above as actual or heuristic fallback

    # Construct Inputs Object
    inputs = GinzuInputs(
        # Real Data
        revenues_base=float(base_rev),
        ebit_reported_base=float(reported_ebit),
        book_equity=float(yf_data.get('book_equity', 0)) + rnd_asset, # Add R&D asset to book equity
        book_debt=float(yf_data.get('book_debt', 0)),
        cash=float(yf_data.get('cash', 0)),
        non_operating_assets=float(yf_data.get('cross_holdings', 0)),
        minority_interests=float(yf_data.get('minority_interest', 0)),
        shares_outstanding=float(yf_data.get('shares_outstanding', 0)),
        tax_rate_effective=float(yf_data.get('effective_tax_rate', 0.21)),
        tax_rate_marginal=float(yf_data.get('marginal_tax_rate', 0.21)),

        # Hybrid / Logic
        capitalize_operating_leases=(yf_data.get('operating_leases_flag') == 'yes'),
        lease_debt=float(yf_data.get('operating_leases_liability', 0)),
        lease_ebit_adjustment=0.0, # Simplified for YF

        capitalize_rnd=capitalize_rnd,
        rnd_asset=rnd_asset,
        rnd_ebit_adjustment=rnd_ebit_adj,

        # Mock / Assumptions
        stock_price=stock_price,
        rev_growth_y1=get_user_input_or_mock("Revenue Growth (Y1)", "rev_growth_y1", default_val=default_rev_growth),
        rev_cagr_y2_5=get_user_input_or_mock("Revenue CAGR (Y2-5)", "rev_cagr_y2_5", default_val=default_rev_growth),
        margin_y1=get_user_input_or_mock("Margin (Y1)", "margin_y1", default_val=adjusted_margin),
        margin_target=get_user_input_or_mock("Target Margin", "margin_target"),
        margin_convergence_year=int(get_user_input_or_mock("Convergence Year", "margin_convergence_year")),
        sales_to_capital_1_5=get_user_input_or_mock("Sales/Capital (1-5)", "sales_to_capital_1_5", default_val=default_sales_to_cap),
        sales_to_capital_6_10=get_user_input_or_mock("Sales/Capital (6-10)", "sales_to_capital_6_10", default_val=default_sales_to_cap),
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
    print(f"VALUATION RESULTS (Ticker: {ticker})")
    print("="*40)
    print(f"Value of Operating Assets : ${results.value_of_operating_assets:,.0f}")
    print(f" - Debt                   : ${results.debt:,.0f}")
    print(f" - Minority Interests     : ${inputs.minority_interests:,.0f}")
    print(f" + Cash                   : ${results.cash_adjusted:,.0f}")
    print(f" + Non-Op Assets          : ${inputs.non_operating_assets:,.0f}")
    print("----------------------------------------")
    print(f"Value of Equity           : ${results.value_of_equity:,.0f}")
    print(f"Value per Share           : ${results.estimated_value_per_share:,.2f}")
    print(f"Price (Market)            : ${inputs.stock_price:,.2f}")
    print(f"Upside / (Downside)       : {(results.estimated_value_per_share / inputs.stock_price - 1.0):.1%}")
    print("="*40)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_yf_valuation.py <TICKER>")
        sys.exit(1)

    run_valuation(sys.argv[1])
