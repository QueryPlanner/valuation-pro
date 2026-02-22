import unittest
from dataclasses import replace

from valuation_engine import (
    GinzuInputs,
    RnDCapitalizationInputs,
    compute_ginzu,
    compute_rnd_capitalization_adjustments,
)


class TestExtensiveValuations(unittest.TestCase):
    def get_amzn_baseline_inputs(self):
        rnd_inputs = RnDCapitalizationInputs(
            amortization_years=3,
            current_year_rnd_expense=85622.0,
            past_year_rnd_expenses=[73213.0, 56052.0, 42740.0],
        )
        rnd_asset, rnd_adj = compute_rnd_capitalization_adjustments(rnd_inputs)

        return GinzuInputs(
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
            rev_cagr_y2_5=0.20,
            margin_y1=0.1133,
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

    def get_ko_baseline_inputs(self):
        return GinzuInputs(
            revenues_base=46465.0,
            ebit_reported_base=13815.0,
            book_equity=25853.0,
            book_debt=45063.0,
            cash=19000.0,
            non_operating_assets=21119.0,
            minority_interests=1558.0,
            shares_outstanding=4315.0,
            stock_price=72.28,
            rev_growth_y1=0.05,
            rev_cagr_y2_5=0.20,
            margin_y1=0.2973,
            margin_target=0.2973,
            margin_convergence_year=5,
            sales_to_capital_1_5=1.7732,
            sales_to_capital_6_10=2.0,
            riskfree_rate_now=0.0458,
            wacc_initial=0.0732,
            tax_rate_effective=0.175,
            tax_rate_marginal=0.25,
            capitalize_rnd=False,
            mature_market_erp=0.0433,
        )

    def run_test_case(self, name, inputs, expected_vps=None, expected_op_assets=None):
        outputs = compute_ginzu(inputs)

        if expected_vps is not None:
            self.assertAlmostEqual(
                outputs.estimated_value_per_share,
                expected_vps,
                delta=0.2,
                msg=f"{name}: Value/Share mismatch",
            )

        if expected_op_assets is not None:
            self.assertAlmostEqual(
                outputs.value_of_operating_assets,
                expected_op_assets,
                delta=expected_op_assets * 0.005,
                msg=f"{name}: Op Assets mismatch",
            )

        return outputs

    # --- AMZN TESTS ---
    def test_amzn_01_baseline(self):
        self.run_test_case(
            "AMZN Baseline", self.get_amzn_baseline_inputs(), expected_vps=134.54, expected_op_assets=1483429
        )

    def test_amzn_02_high_growth(self):
        inputs = replace(self.get_amzn_baseline_inputs(), rev_growth_y1=0.20, rev_cagr_y2_5=0.15)
        self.run_test_case("AMZN High Growth", inputs, expected_vps=122.78, expected_op_assets=1360007)

    def test_amzn_03_low_margin(self):
        inputs = replace(self.get_amzn_baseline_inputs(), margin_target=0.10)
        self.run_test_case("AMZN Low Target Margin", inputs, expected_vps=77.92, expected_op_assets=889411)

    def test_amzn_04_high_wacc(self):
        inputs = replace(self.get_amzn_baseline_inputs(), wacc_initial=0.10)
        self.run_test_case("AMZN High WACC", inputs, expected_vps=122.01, expected_op_assets=1352009)

    def test_amzn_05_no_rnd_cap(self):
        inputs = self.get_amzn_baseline_inputs()
        inputs = replace(
            inputs,
            capitalize_rnd=False,
            rnd_asset=0,
            rnd_ebit_adjustment=0,
            margin_y1=inputs.ebit_reported_base / inputs.revenues_base,
        )
        self.run_test_case("AMZN No R&D Cap", inputs, expected_vps=129.09)

    def test_amzn_06_sales_to_cap(self):
        inputs = replace(self.get_amzn_baseline_inputs(), sales_to_capital_1_5=2.0, sales_to_capital_6_10=2.0)
        self.run_test_case("AMZN High Sales-to-Cap", inputs, expected_vps=151.87, expected_op_assets=1665276)

    def test_amzn_07_fast_convergence(self):
        inputs = replace(self.get_amzn_baseline_inputs(), margin_convergence_year=2)
        self.run_test_case("AMZN Fast Convergence", inputs, expected_vps=136.27, expected_op_assets=1501630)

    def test_amzn_08_with_failure(self):
        inputs = replace(
            self.get_amzn_baseline_inputs(),
            override_failure_probability=True,
            probability_of_failure=0.10,
            distress_proceeds_percent=0.50,
            distress_proceeds_tie="V",
        )
        self.run_test_case("AMZN 10% Failure Prob", inputs, expected_vps=127.47)

    def test_amzn_09_tax_rate(self):
        inputs = replace(self.get_amzn_baseline_inputs(), tax_rate_marginal=0.35)
        self.run_test_case("AMZN High Marginal Tax", inputs, expected_vps=114.15, expected_op_assets=1269522)

    def test_amzn_10_aggressive_combo(self):
        inputs = replace(self.get_amzn_baseline_inputs(), rev_growth_y1=0.25, margin_target=0.18, wacc_initial=0.075)
        self.run_test_case("AMZN Aggressive Growth/Margin", inputs, expected_vps=230.52)

    # --- KO TESTS ---
    def test_ko_01_baseline(self):
        self.run_test_case("KO Baseline", self.get_ko_baseline_inputs(), expected_vps=73.54, expected_op_assets=323815)

    def test_ko_02_high_growth(self):
        inputs = replace(self.get_ko_baseline_inputs(), rev_growth_y1=0.20, rev_cagr_y2_5=0.15)
        self.run_test_case("KO High Growth", inputs, expected_vps=68.75, expected_op_assets=303139)

    def test_ko_03_low_target_margin(self):
        inputs = replace(self.get_ko_baseline_inputs(), margin_target=0.10)
        self.run_test_case("KO Low Target Margin", inputs, expected_vps=20.58, expected_op_assets=95304)

    def test_ko_04_high_wacc(self):
        inputs = replace(self.get_ko_baseline_inputs(), wacc_initial=0.10)
        self.run_test_case("KO High WACC", inputs, expected_vps=62.51, expected_op_assets=276234)

    def test_ko_05_rnd_cap_ko(self):
        inputs = replace(self.get_ko_baseline_inputs(), capitalize_rnd=True, rnd_asset=5000, rnd_ebit_adjustment=500)
        self.run_test_case("KO With R&D Asset", inputs, expected_vps=73.54)

    def test_ko_06_stable_roc_override(self):
        inputs = replace(self.get_ko_baseline_inputs(), override_stable_roc=True, stable_roc=0.15)
        self.run_test_case("KO Stable ROC 15%", inputs, expected_vps=94.19)

    def test_ko_07_perp_growth(self):
        inputs = replace(self.get_ko_baseline_inputs(), override_perpetual_growth=True, perpetual_growth_rate=0.03)
        self.run_test_case("KO 3% Perp Growth", inputs, expected_vps=70.99)

    def test_ko_08_trapped_cash(self):
        inputs = replace(
            self.get_ko_baseline_inputs(),
            override_trapped_cash=True,
            trapped_cash_amount=5000,
            trapped_cash_foreign_tax_rate=0.10,
        )
        self.run_test_case("KO Trapped Cash", inputs, expected_vps=73.36)

    def test_ko_09_high_efficiency(self):
        inputs = replace(self.get_ko_baseline_inputs(), sales_to_capital_1_5=2.0, sales_to_capital_6_10=2.0)
        self.run_test_case("KO High Sales-to-Cap", inputs, expected_vps=74.36, expected_op_assets=327356)

    def test_ko_10_fast_convergence(self):
        inputs = replace(self.get_ko_baseline_inputs(), margin_convergence_year=2)
        self.run_test_case("KO Fast Convergence", inputs, expected_vps=73.54, expected_op_assets=323815)


if __name__ == "__main__":
    unittest.main()
