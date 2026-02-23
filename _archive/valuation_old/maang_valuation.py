from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

try:
    import yfinance as yf  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover - depends on local env
    yf = None  # type: ignore[assignment]

# Local imports (repo root + non-package directory)
REPO_ROOT = Path(__file__).resolve().parents[1]
SEC_INTEGRATION_DIR = REPO_ROOT / "sec-data-integration"
sys.path.append(str(REPO_ROOT))
sys.path.append(str(SEC_INTEGRATION_DIR))

import sec_data_extractor as sec_extractor  # type: ignore  # local file module
from valuation_engine.fcff_ginzu.engine import GinzuInputs, compute_ginzu

SEC_DUCKDB_PATH = str(REPO_ROOT / "sec_fsn.duckdb")

MAANG_CIKS: Dict[str, str] = {
    "META": "1326801",
    "AAPL": "320193",
    "AMZN": "1018724",
    "NFLX": "1065280",
    "GOOG": "1652044",
}


RISKFREE_RATE_NOW = 0.0425
MATURE_MARKET_ERP = 0.0460
WACC_INITIAL = 0.085
PERPETUAL_GROWTH_RATE = 0.03
DEFAULT_SALES_TO_CAPITAL = 2.0
DEFAULT_BETA = 1.0
DEFAULT_TAX_RATE = 0.21
MARGIN_CONVERGENCE_YEAR = 5


@dataclass(frozen=True)
class MarketSnapshot:
    stock_price: float
    beta: float


def _configure_sec_extractor_db_path(db_path: str) -> None:
    """
    `sec_data_extractor.py` is written as a script with a global DB_PATH.
    We override it here so the extraction logic stays identical while letting
    this runner point at *our* local DuckDB file.
    """
    sec_extractor.DB_PATH = db_path


def _clamp_rate_0_1(value: Any, *, fallback: float) -> float:
    try:
        rate = float(value)
    except (TypeError, ValueError):
        return fallback
    if rate < 0.0:
        return 0.0
    if rate > 1.0:
        return 1.0
    return rate


def _safe_divide(numerator: float, denominator: float, *, fallback: float) -> float:
    if denominator == 0:
        return fallback
    return numerator / denominator


def _get_price_from_yfinance(ticker_obj: Any) -> float:
    """
    Prefer `fast_info` for speed/robustness, fall back to `info`.

    Context7 references:
    - `Ticker.fast_info` is a smaller/faster info subset than `Ticker.info`.
    """
    fast_info = getattr(ticker_obj, "fast_info", None) or {}
    info = getattr(ticker_obj, "info", None) or {}

    price_candidates = (
        fast_info.get("last_price"),
        fast_info.get("regular_market_price"),
        fast_info.get("previous_close"),
        info.get("currentPrice"),
        info.get("previousClose"),
    )
    for price in price_candidates:
        if price is None:
            continue
        try:
            return float(price)
        except (TypeError, ValueError):
            continue
    return 0.0


def fetch_market_snapshot(ticker: str) -> Optional[MarketSnapshot]:
    print(f"  Fetching Yahoo Finance market snapshot for {ticker}...")
    if yf is None:
        print("    Yahoo Finance unavailable (missing `yfinance`). Proceeding without price/beta.")
        return MarketSnapshot(stock_price=0.0, beta=DEFAULT_BETA)
    try:
        ticker_obj = yf.Ticker(ticker)
        stock_price = _get_price_from_yfinance(ticker_obj)

        info = getattr(ticker_obj, "info", None) or {}
        beta = info.get("beta", DEFAULT_BETA)

        return MarketSnapshot(
            stock_price=float(stock_price or 0.0),
            beta=float(beta or DEFAULT_BETA),
        )
    except Exception as exc:
        print(f"    Yahoo error: {exc}")
        return None


def fetch_sec_inputs(cik: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Use the *same* extraction logic as `sec_data_extractor.extract_data`.
    """
    sec_data: Dict[str, Any] = sec_extractor.extract_data(cik)
    if "error" in sec_data:
        return None, str(sec_data["error"])
    return sec_data, None

def main():
    print("--- MAANG Valuation Runner ---")
    print("Sources: Yahoo Finance (Market Price/Beta) + SEC DuckDB (sec_data_extractor logic)")
    print(f"SEC DuckDB: {SEC_DUCKDB_PATH}")

    _configure_sec_extractor_db_path(SEC_DUCKDB_PATH)

    for ticker, cik in MAANG_CIKS.items():
        print(f"\nProcessing {ticker} (CIK: {cik})...")

        market = fetch_market_snapshot(ticker)
        if market is None:
            print("Skipping - Yahoo market data failed.")
            continue

        sec_data, sec_error = fetch_sec_inputs(cik)
        if sec_data is None:
            print(f"Skipping - SEC extraction failed: {sec_error}")
            continue

        revenues_base = float(sec_data.get("revenues_base") or 0.0)
        ebit_reported_base = float(sec_data.get("ebit_reported_base") or 0.0)
        if revenues_base <= 0:
            print("Skipping - SEC revenues_base is missing/zero.")
            continue

        book_equity = float(sec_data.get("book_equity") or 0.0)
        book_debt = float(sec_data.get("book_debt") or 0.0)
        cash = float(sec_data.get("cash") or 0.0)
        shares_outstanding = float(sec_data.get("shares_outstanding") or 0.0)
        if shares_outstanding <= 0:
            print("Skipping - SEC shares_outstanding is missing/zero.")
            continue

        base_margin = _safe_divide(ebit_reported_base, revenues_base, fallback=0.0)

        sales_to_capital_from_sec = float(sec_data.get("sales_to_capital") or 0.0)
        invested_capital = book_equity + book_debt - cash
        has_valid_invested_capital = invested_capital > 0
        sales_to_capital_fallback = (
            _safe_divide(revenues_base, invested_capital, fallback=DEFAULT_SALES_TO_CAPITAL)
            if has_valid_invested_capital
            else DEFAULT_SALES_TO_CAPITAL
        )
        sales_to_capital = sales_to_capital_from_sec if sales_to_capital_from_sec > 0 else sales_to_capital_fallback

        non_operating_assets = float(sec_data.get("cross_holdings") or 0.0)
        minority_interests = float(sec_data.get("minority_interest") or 0.0)

        tax_rate_effective = _clamp_rate_0_1(sec_data.get("effective_tax_rate"), fallback=DEFAULT_TAX_RATE)
        tax_rate_marginal = _clamp_rate_0_1(sec_data.get("marginal_tax_rate"), fallback=DEFAULT_TAX_RATE)

        assumptions = [
            "Revenues/EBIT: SEC (LTM logic from sec_data_extractor)",
            "Book equity/debt/cash/shares: SEC (point-in-time from latest filing)",
            "Stock price/beta: Yahoo Finance",
            f"Sales-to-capital: {'SEC derived' if sales_to_capital_from_sec > 0 else 'computed fallback'}",
            f"WACC (fixed initial): {WACC_INITIAL:.1%}",
            f"Terminal growth (override): {PERPETUAL_GROWTH_RATE:.1%}",
        ]

        ginzu_inputs = GinzuInputs(
            revenues_base=revenues_base,
            ebit_reported_base=ebit_reported_base,
            book_equity=book_equity,
            book_debt=book_debt,
            cash=cash,
            non_operating_assets=non_operating_assets,
            minority_interests=minority_interests,
            shares_outstanding=shares_outstanding,
            stock_price=float(market.stock_price),

            tax_rate_effective=tax_rate_effective,
            tax_rate_marginal=tax_rate_marginal,
            capitalize_operating_leases=False,
            lease_debt=0.0,
            lease_ebit_adjustment=0.0,
            capitalize_rnd=False,

            rev_growth_y1=0.12,
            rev_cagr_y2_5=0.08,
            margin_y1=base_margin,
            margin_target=base_margin,  # default: sustain current margin
            margin_convergence_year=MARGIN_CONVERGENCE_YEAR,
            sales_to_capital_1_5=float(sales_to_capital),
            sales_to_capital_6_10=float(sales_to_capital),
            riskfree_rate_now=RISKFREE_RATE_NOW,
            mature_market_erp=MATURE_MARKET_ERP,
            wacc_initial=WACC_INITIAL,  # fixed assumption
            override_perpetual_growth=True,
            perpetual_growth_rate=PERPETUAL_GROWTH_RATE,
        )

        # Compute
        try:
            res = compute_ginzu(ginzu_inputs)

            print("\n  --- Valuation Results ---")
            print(f"  Current Price: ${market.stock_price:.2f}")
            print(f"  Estimated Value: ${res.estimated_value_per_share:.2f}")
            if market.stock_price > 0:
                upside = (res.estimated_value_per_share / market.stock_price) - 1
                print(f"  Upside: {upside:.1%}")

            print("\n  --- Key Assumptions ---")
            for a in assumptions:
                print(f"  - {a}")
            print(f"  - Sales/Capital used: {sales_to_capital:.2f}")
            print(f"  - Effective tax rate (base): {tax_rate_effective:.1%}")
            print(f"  - Marginal tax rate (terminal): {tax_rate_marginal:.1%}")

        except Exception as e:
            print(f"  Valuation Error: {e}")

if __name__ == "__main__":
    main()
