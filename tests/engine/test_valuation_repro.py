
import unittest

from valuation_engine import (
    GinzuInputs,
    RnDCapitalizationInputs,
    compute_ginzu,
    compute_rnd_capitalization_adjustments,
)


class TestValuationRepro(unittest.TestCase):
    def test_amazon_valuation_current(self):
        """
        Reproduction of the 'Current' dataset (Amazon) from fcffsimpleginzu-formulas.
        """
        # 1. R&D Calculation
        rnd_inputs = RnDCapitalizationInputs(
            amortization_years=3,
            current_year_rnd_expense=85622.0,
            past_year_rnd_expenses=[73213.0, 56052.0, 42740.0],
        )
        rnd_asset, rnd_adj = compute_rnd_capitalization_adjustments(rnd_inputs)

        # Verify R&D calculations
        expected_asset = 153114.67
        self.assertAlmostEqual(rnd_asset, expected_asset, places=1)

        expected_adj = 28287.0
        self.assertAlmostEqual(rnd_adj, expected_adj, places=0)

        # 2. Main Valuation Inputs
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
            capitalize_operating_leases=False,
            has_employee_options=False,
            mature_market_erp=0.0411,
        )

        outputs = compute_ginzu(inputs)

        # Verify against Excel Truth (103.79)
        self.assertAlmostEqual(outputs.estimated_value_per_share, 103.79, places=1)

    def test_coca_cola_valuation_archive(self):
        """
        Reproduction of the 'Archive' dataset (Coca Cola) from fcffsimpleginzu-formulas/archive.
        """
        inputs = GinzuInputs(
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
            rev_cagr_y2_5=0.05,
            margin_y1=13815.0 / 46465.0,
            margin_target=13815.0 / 46465.0,
            margin_convergence_year=5,
            sales_to_capital_1_5=1.7732,
            sales_to_capital_6_10=5.0,
            riskfree_rate_now=0.0458,
            wacc_initial=0.08,
            tax_rate_effective=0.175,
            tax_rate_marginal=0.25,
            capitalize_rnd=False,
            capitalize_operating_leases=False,
            has_employee_options=False,
            mature_market_erp=0.0411,
        )

        outputs = compute_ginzu(inputs)

        # Verify against Excel Truth (39.94)
        self.assertAlmostEqual(round(outputs.estimated_value_per_share), round(39.94), places=0)


if __name__ == "__main__":
    unittest.main()
