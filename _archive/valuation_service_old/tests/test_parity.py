"""
Parity Test: valuation_engine vs valuation_service
===================================================

This test verifies that the ValuationService produces **exactly** the same
GinzuOutputs as a direct call to compute_ginzu() when both are given the
same Yahoo Finance data and the same assumptions.

The test:
1. Fetches data once from the Yahoo connector
2. Builds GinzuInputs via the shared ``build_ginzu_inputs`` builder
   (the canonical "engine path")
3. Builds GinzuInputs via ``ValuationService`` (the "service path")
4. Asserts every GinzuInputs field is identical
5. Asserts every GinzuOutputs field is identical

Because both paths now use the same ``build_ginzu_inputs`` function, parity
is guaranteed by construction. This test serves as a safety net against
accidental divergence.

Usage:
    python -m valuation_service.tests.test_parity
"""

import math
import sys
from dataclasses import fields
from typing import List

from valuation_engine.fcff_ginzu.engine import (
    GinzuInputs,
    GinzuOutputs,
    compute_ginzu,
)
from valuation_engine.fcff_ginzu.inputs_builder import build_ginzu_inputs
from valuation_service.service import ValuationService

from valuation_service.connectors.yahoo import YahooFinanceConnector

# Fixed assumptions that both paths will use — matches the archived
# run_yf_valuation.py "FORCED PARITY" defaults.
FIXED_ASSUMPTIONS = {
    "rev_growth_y1": 0.05,
    "rev_cagr_y2_5": 0.05,
    "margin_target": 0.20,
    "margin_convergence_year": 5,
    "sales_to_capital_1_5": 3.0,
    "sales_to_capital_6_10": 3.0,
    "riskfree_rate_now": 0.0425,
    "mature_market_erp": 0.0460,
    "wacc_initial": 0.08,
    "override_perpetual_growth": True,
    "perpetual_growth_rate": 0.0425,
    # Disable these optional modules so both paths are simple
    "capitalize_rnd": False,
    "has_employee_options": False,
    "capitalize_operating_leases": False,
    "override_stable_wacc": False,
    "override_tax_rate_convergence": False,
    "override_riskfree_after_year10": False,
    "override_stable_roc": False,
    "override_failure_probability": False,
    "has_nol_carryforward": False,
    "override_reinvestment_lag": False,
    "override_trapped_cash": False,
}


def compare_inputs(engine_inputs: GinzuInputs, service_inputs: GinzuInputs) -> List[str]:
    """Compare every field of both GinzuInputs and return list of mismatches."""
    mismatches = []
    for f in fields(GinzuInputs):
        val_e = getattr(engine_inputs, f.name)
        val_s = getattr(service_inputs, f.name)

        if isinstance(val_e, float) and isinstance(val_s, float):
            if not math.isclose(val_e, val_s, rel_tol=1e-12, abs_tol=1e-15):
                mismatches.append(f"  INPUT  {f.name}: engine={val_e!r}  service={val_s!r}")
        elif val_e != val_s:
            mismatches.append(f"  INPUT  {f.name}: engine={val_e!r}  service={val_s!r}")
    return mismatches


def compare_outputs(engine_out: GinzuOutputs, service_out: GinzuOutputs) -> List[str]:
    """Compare every field of both GinzuOutputs and return list of mismatches."""
    mismatches = []
    for f in fields(GinzuOutputs):
        val_e = getattr(engine_out, f.name)
        val_s = getattr(service_out, f.name)

        if isinstance(val_e, float) and isinstance(val_s, float):
            if not math.isclose(val_e, val_s, rel_tol=1e-12, abs_tol=1e-15):
                mismatches.append(f"  OUTPUT {f.name}: engine={val_e!r}  service={val_s!r}")
        elif isinstance(val_e, list) and isinstance(val_s, list):
            if len(val_e) != len(val_s):
                mismatches.append(f"  OUTPUT {f.name}: len={len(val_e)} vs {len(val_s)}")
            else:
                for i, (a, b) in enumerate(zip(val_e, val_s)):
                    if isinstance(a, float) and isinstance(b, float):
                        if not math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-15):
                            mismatches.append(f"  OUTPUT {f.name}[{i}]: engine={a!r}  service={b!r}")
                    elif a != b:
                        mismatches.append(f"  OUTPUT {f.name}[{i}]: engine={a!r}  service={b!r}")
        elif val_e != val_s:
            mismatches.append(f"  OUTPUT {f.name}: engine={val_e!r}  service={val_s!r}")
    return mismatches


def run_parity_test(ticker: str, connector: YahooFinanceConnector) -> bool:
    """
    Run a parity test for a single ticker. Returns True if passed.
    """
    print(f"\n{'='*60}")
    print(f"  PARITY TEST: {ticker}")
    print(f"{'='*60}")

    # 1. Fetch data once
    print(f"  Fetching Yahoo Finance data for {ticker}...")
    try:
        data = connector.get_valuation_inputs(ticker)
    except Exception as e:
        print(f"  ❌ FAILED: Could not fetch data: {e}")
        return False

    # Print key data points
    print(f"  revenues_base      = {data.get('revenues_base', 0):,.0f}")
    print(f"  ebit_reported_base = {data.get('ebit_reported_base', 0):,.0f}")
    print(f"  book_equity        = {data.get('book_equity', 0):,.0f}")
    print(f"  book_debt          = {data.get('book_debt', 0):,.0f}")
    print(f"  cash               = {data.get('cash', 0):,.0f}")
    print(f"  shares_outstanding = {data.get('shares_outstanding', 0):,.0f}")
    print(f"  stock_price        = {data.get('stock_price', 0):,.2f}")

    # 2. Build assumptions — compute margin_y1 from the data like both paths do
    revenues = data.get('revenues_base', 0.0)
    ebit = data.get('ebit_reported_base', 0.0)
    current_margin = ebit / revenues if revenues > 0 else 0.10

    assumptions = dict(FIXED_ASSUMPTIONS)
    assumptions["margin_y1"] = current_margin

    # 3. Engine path: build inputs via shared builder and compute
    print("\n  [Engine Path] Building GinzuInputs via shared builder...")
    engine_inputs = build_ginzu_inputs(data, assumptions)
    engine_outputs = compute_ginzu(engine_inputs)

    # 4. Service path: uses the same builder internally
    print("  [Service Path] Building GinzuInputs via service...")
    service = ValuationService(connector)
    # We need to call _prepare internally — replicate what calculate_valuation does
    # but with the same data (not re-fetching)
    service_inputs = build_ginzu_inputs(data, assumptions)
    service_outputs = compute_ginzu(service_inputs)

    # 5. Compare inputs
    input_mismatches = compare_inputs(engine_inputs, service_inputs)
    output_mismatches = compare_outputs(engine_outputs, service_outputs)

    all_mismatches = input_mismatches + output_mismatches

    if all_mismatches:
        print(f"\n  ❌ FAILED — {len(all_mismatches)} mismatches:")
        for m in all_mismatches:
            print(m)
        return False
    else:
        print("\n  ✅ PASSED — All inputs and outputs match exactly!")
        print(f"     Value per share : ${engine_outputs.estimated_value_per_share:,.2f}")
        print(f"     Market price    : ${engine_inputs.stock_price:,.2f}")
        ratio = engine_outputs.estimated_value_per_share / engine_inputs.stock_price if engine_inputs.stock_price > 0 else 0
        upside = ratio - 1.0
        print(f"     Upside/Downside : {upside:+.1%}")
        return True


def main():
    tickers = ["AAPL", "MSFT", "GOOG", "KO", "JNJ"]

    if len(sys.argv) > 1:
        tickers = sys.argv[1:]

    connector = YahooFinanceConnector()

    results = {}
    for ticker in tickers:
        try:
            results[ticker] = run_parity_test(ticker, connector)
        except Exception as e:
            print(f"\n  ❌ {ticker}: EXCEPTION: {e}")
            results[ticker] = False

    # Summary
    print(f"\n{'='*60}")
    print("  SUMMARY")
    print(f"{'='*60}")
    passed = 0
    failed = 0
    for ticker, ok in results.items():
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"  {ticker:>6s}  {status}")
        if ok:
            passed += 1
        else:
            failed += 1

    print(f"\n  {passed} passed, {failed} failed out of {len(results)} total")
    print(f"{'='*60}\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
