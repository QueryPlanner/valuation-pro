
import unittest

from valuation_engine.fcff_ginzu import (
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
        # Inputs from R& D converter.csv (Truth from check_excel_truth.py)
        # Amort Years = 3
        # Current = 85622
        # Past: 73213 (-1), 56052 (-2), 42740 (-3)
        rnd_inputs = RnDCapitalizationInputs(
            amortization_years=3,
            current_year_rnd_expense=85622.0,
            past_year_rnd_expenses=[73213.0, 56052.0, 42740.0],  # Year -1, -2, -3
        )
        rnd_asset, rnd_adj = compute_rnd_capitalization_adjustments(rnd_inputs)

        # Verify R&D calculations
        # Asset = 85622 + 73213*(2/3) + 56052*(1/3) + 42740*(0/3) = 153114.66...
        expected_asset = 153114.67
        self.assertAlmostEqual(rnd_asset, expected_asset, places=1)

        # Amort = (73213 + 56052 + 42740) / 3 = 57335
        # Adj = 85622 - 57335 = 28287
        expected_adj = 28287.0
        self.assertAlmostEqual(rnd_adj, expected_adj, places=0)

        # 2. Main Valuation Inputs
        # Inputs from Input sheet.csv (Current)
        inputs = GinzuInputs(
            # Base Year
            revenues_base=574785.0,
            ebit_reported_base=36852.0,
            book_equity=201875.0,
            book_debt=161574.0,
            cash=86780.0,
            non_operating_assets=2954.0,
            minority_interests=0.0,
            shares_outstanding=10492.0,
            stock_price=169.0,

            # Drivers
            rev_growth_y1=0.12,
            rev_cagr_y2_5=0.12,

            # Margin Y1 is base margin (implied from Input sheet formula pointing to Valuation Output B4)
            # Base Margin (Adjusted) = (36852 + 28287) / 574785 = 11.33%
            margin_y1=(36852.0 + rnd_adj) / 574785.0,
            margin_target=0.14,
            margin_convergence_year=5,

            sales_to_capital_1_5=1.5,
            sales_to_capital_6_10=1.5,

            riskfree_rate_now=0.0408,
            wacc_initial=0.0860, # From Cost of Capital Worksheet calculation

            tax_rate_effective=0.19,
            tax_rate_marginal=0.25,

            # Switches
            capitalize_rnd=True,
            rnd_asset=rnd_asset,
            rnd_ebit_adjustment=rnd_adj,

            capitalize_operating_leases=False,
            has_employee_options=False, # "No" in sheet, despite having numbers

            mature_market_erp=0.0411, # From Country equity risk premiums.csv
        )

        outputs = compute_ginzu(inputs)

        print("\n--- Amazon Valuation Results ---")
        print(f"Value of Operating Assets: {outputs.value_of_operating_assets:,.2f}")
        print(f"Value of Equity: {outputs.value_of_equity:,.2f}")
        print(f"Value per Share: {outputs.estimated_value_per_share:,.2f}")
        print(f"Price as % of Value: {outputs.price_as_percent_of_value:.2%}")

        # Verify against Excel Truth (103.79)
        self.assertAlmostEqual(outputs.estimated_value_per_share, 103.79, places=1)

    def test_coca_cola_valuation_archive(self):
        """
        Reproduction of the 'Archive' dataset (Coca Cola) from fcffsimpleginzu-formulas/archive.
        """
        # Inputs from archive/Input sheet.csv
        inputs = GinzuInputs(
            # Base Year
            revenues_base=46465.0,
            ebit_reported_base=13815.0,
            book_equity=25853.0,
            book_debt=45063.0,
            cash=19000.0,
            non_operating_assets=21119.0,
            minority_interests=1558.0,
            shares_outstanding=4315.0,
            stock_price=72.28,

            # Drivers
            rev_growth_y1=0.05,
            rev_cagr_y2_5=0.05,

            # Margin Y1 = Base Margin (Unadjusted since R&D/Leases are No)
            # 13815 / 46465 = 29.73%
            margin_y1=13815.0 / 46465.0,
            margin_target=13815.0 / 46465.0, # Target = Current
            margin_convergence_year=5,

            # Sales to Capital
            sales_to_capital_1_5=1.7732, # From Global Industry Averages (Beverage Soft)
            sales_to_capital_6_10=5.0,   # From Input Sheet B31 reference

            riskfree_rate_now=0.0458,
            wacc_initial=0.08, # Estimated placeholder

            tax_rate_effective=0.175,
            tax_rate_marginal=0.25,

            # Switches
            capitalize_rnd=False,
            capitalize_operating_leases=False,
            has_employee_options=False,

            mature_market_erp=0.0411, # Assuming same ERP source
        )

        outputs = compute_ginzu(inputs)

        print("\n--- Coca Cola Valuation Results ---")
        print(f"Value of Operating Assets: {outputs.value_of_operating_assets:,.2f}")
        print(f"Value of Equity: {outputs.value_of_equity:,.2f}")
        print(f"Value per Share: {outputs.estimated_value_per_share:,.2f}")
        print(f"Price as % of Value: {outputs.price_as_percent_of_value:.2%}")

        # Verify against Excel Truth (39.94) - Checking to closest integer as requested
        self.assertAlmostEqual(round(outputs.estimated_value_per_share), round(39.94), places=0)

if __name__ == "__main__":
    unittest.main()
