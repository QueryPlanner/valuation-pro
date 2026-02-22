"""
Run FCFF Simple Ginzu using pure-Python inputs (no CSV/XLSX).

This is a convenience wrapper around `valuation_engine.compute_ginzu`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

try:
    # Prefer normal imports (works when run as `python -m utils.run_manual_inputs`).
    from valuation_engine.fcff_ginzu import GinzuOutputs, compute_ginzu
except ModuleNotFoundError:
    # Allow running as a file: `python valuation_engine/fcff_ginzu/utils/archive/run_manual_inputs.py`
    project_root = Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(project_root))
    from valuation_engine.fcff_ginzu import GinzuOutputs, compute_ginzu

from valuation_engine.fcff_ginzu.utils.archive.manual_inputs import GINZU_INPUTS


def _outputs_to_dict(outputs: GinzuOutputs) -> Dict[str, Any]:
    """
    Produce a JSON-friendly dict for inspection or downstream tooling.
    """
    return {
        "pv_10y": outputs.pv_10y,
        "pv_terminal_value": outputs.pv_terminal_value,
        "pv_sum": outputs.pv_sum,
        "value_of_operating_assets": outputs.value_of_operating_assets,
        "value_of_equity_common": outputs.value_of_equity_common,
        "estimated_value_per_share": outputs.estimated_value_per_share,
        "price_as_percent_of_value": outputs.price_as_percent_of_value,
        "series": {
            "growth_rates_year1_to_10": outputs.growth_rates,
            "revenues_base_to_year10": outputs.revenues,
            "margins_base_to_year10": outputs.margins,
            "ebit_base_to_year10": outputs.ebit,
            "tax_rates_base_to_year10": outputs.tax_rates,
            "nol_base_to_year10": outputs.nol,
            "ebit_after_tax_base_to_year10": outputs.ebit_after_tax,
            "reinvestment_year1_to_10_and_terminal": outputs.reinvestment,
            "fcff_year1_to_10_and_terminal": outputs.fcff,
            "wacc_year1_to_10_and_stable": outputs.wacc,
            "discount_factors_year1_to_10": outputs.discount_factors,
            "pv_fcff_year1_to_10": outputs.pv_fcff,
        },
    }


def _print_human_summary(outputs: GinzuOutputs) -> None:
    print("FCFF Simple Ginzu — Key Outputs (manual inputs)")
    print(f"- PV (CF over next 10 years): {outputs.pv_10y:,.2f}")
    print(f"- PV(Terminal value): {outputs.pv_terminal_value:,.2f}")
    print(f"- Sum of PV: {outputs.pv_sum:,.2f}")
    print(f"- Value of operating assets: {outputs.value_of_operating_assets:,.2f}")
    print(f"- Value of equity in common stock: {outputs.value_of_equity_common:,.2f}")
    print(f"- Estimated value /share: {outputs.estimated_value_per_share:,.4f}")
    print(f"- Price as % of value: {outputs.price_as_percent_of_value:.6f}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run FCFF Simple Ginzu using utils/archive/manual_inputs.py")
    parser.add_argument(
        "--output-json",
        type=Path,
        help="Optional path to write full outputs as JSON.",
    )
    args = parser.parse_args(argv)

    outputs = compute_ginzu(GINZU_INPUTS)
    _print_human_summary(outputs)

    if args.output_json is not None:
        payload = _outputs_to_dict(outputs)
        args.output_json.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        print(f"\nWrote JSON outputs to: {args.output_json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


