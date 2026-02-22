
import unittest

import openpyxl
from valuation_engine.fcff_ginzu import (
    GinzuInputs,
    RnDCapitalizationInputs,
    compute_ginzu,
    compute_rnd_capitalization_adjustments,
)


class TestDeepLogicAudit(unittest.TestCase):
    def test_audit_amazon_baseline(self):
        # 1. Load Excel Data
        wb = openpyxl.load_workbook("valuation_engine/fcff_ginzu/spreadsheets/fcffsimpleginzu.xlsx", data_only=True)
        ws = wb["Valuation output"]

        def get_row_series(row_idx, start_col=3, length=10):
            return [ws.cell(row=row_idx, column=c).value for c in range(start_col, start_col + length)]

        excel_data = {
            "revenues": get_row_series(3),
            "ebit": get_row_series(5),
            "ebit_after_tax": get_row_series(7),
            "reinvestment": get_row_series(8),
            "fcff": get_row_series(9),
            "wacc": get_row_series(12),
            "discount_factors": get_row_series(13),
        }

        # 2. Run Engine
        rnd_inputs = RnDCapitalizationInputs(
            amortization_years=3,
            current_year_rnd_expense=85622.0,
            past_year_rnd_expenses=[73213.0, 56052.0, 42740.0],
        )
        rnd_asset, rnd_adj = compute_rnd_capitalization_adjustments(rnd_inputs)

        inputs = GinzuInputs(
            revenues_base=574785.0,
            ebit_reported_base=36852.0,
            book_equity=201875.0,
            book_debt=161574.0,
            cash=86780.0,
            non_operating_assets=2954.0,
            minority_interests=0.0,
            shares_outstanding=10492.0,
            stock_price=169.0,
            rev_growth_y1=0.12,
            rev_cagr_y2_5=0.12,
            margin_y1=(36852.0 + rnd_adj) / 574785.0,
            margin_target=0.14,
            margin_convergence_year=5,
            sales_to_capital_1_5=1.5,
            sales_to_capital_6_10=1.5,
            riskfree_rate_now=0.0408,
            wacc_initial=0.0860,
            tax_rate_effective=0.19,
            tax_rate_marginal=0.25,
            capitalize_rnd=True,
            rnd_asset=rnd_asset,
            rnd_ebit_adjustment=rnd_adj,
            mature_market_erp=0.0411,
        )

        outputs = compute_ginzu(inputs)

        # 3. Compare Year-by-Year (Years 1-10)
        print("\n--- DEEP AUDIT: Engine vs Excel (10-Year Forecast) ---")

        metrics = [
            ("Revenues", excel_data["revenues"], outputs.revenues[1:]),
            ("EBIT", excel_data["ebit"], outputs.ebit[1:]),
            ("EBIT(1-t)", excel_data["ebit_after_tax"], outputs.ebit_after_tax[1:]),
            ("Reinvestment", excel_data["reinvestment"], outputs.reinvestment[:10]),
            ("FCFF", excel_data["fcff"], outputs.fcff[:10]),
            ("WACC", excel_data["wacc"], outputs.wacc[:10]),
            ("Disc. Factor", excel_data["discount_factors"], outputs.discount_factors),
        ]

        for label, excel_vals, engine_vals in metrics:
            print(f"\nAuditing {label}...")
            for yr in range(10):
                ex = excel_vals[yr]
                en = engine_vals[yr]
                diff = abs(ex - en)
                # Use a small percentage tolerance (0.01%) for rounding diffs
                tolerance = max(1.0, abs(ex) * 0.0001)

                try:
                    self.assertAlmostEqual(ex, en, delta=tolerance)
                    # print(f"  Year {yr+1}: OK (Diff: {diff:.4f})")
                except AssertionError as e:
                    print(f"  !! Year {yr+1} MISMATCH: Excel={ex:,.2f}, Engine={en:,.2f}, Diff={diff:,.2f}")
                    raise e
            print(f"  {label}: PASSED (All years match Excel logic)")

if __name__ == "__main__":
    unittest.main()
