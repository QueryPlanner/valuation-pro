
import unittest
from dataclasses import replace
from valuation_engine.fcff_ginzu.engine import (
    _compute_ebit_after_tax_with_nol,
    _black_scholes_call_value,
    compute_dilution_adjusted_black_scholes_option_value,
    OptionInputs,
    _compute_margins,
    _compute_reinvestment,
    InputError,
    GinzuInputs,
    compute_ginzu
)

class TestEngineUnits(unittest.TestCase):

    def test_nol_logic(self):
        # Case 1: Simple NOL usage
        # Need lists of length 11
        ebit = [100.0] * 11
        tax_rates = [0.25] * 11
        nol_start = 150.0
        
        nol_series, ebit_after_tax = _compute_ebit_after_tax_with_nol(
            ebit=ebit, tax_rates=tax_rates, nol_start_year1=nol_start
        )
        
        # Year 0 (Base): EBIT 100, tax applied = 75
        self.assertEqual(ebit_after_tax[0], 75.0)
        
        # Year 1: EBIT 100. NOL 150. EBIT < NOL. 
        self.assertEqual(ebit_after_tax[1], 100.0)
        self.assertEqual(nol_series[1], 50.0)
        
        # Year 2: EBIT 100. NOL 50. EBIT > NOL.
        self.assertEqual(ebit_after_tax[2], 87.5)
        self.assertEqual(nol_series[2], 0.0)

    def test_nol_logic_negative_ebit(self):
        # Case 2: Negative EBIT generating NOL
        ebit = [0.0] * 11
        ebit[0] = 100.0
        ebit[1] = -50.0
        ebit[2] = 100.0
        tax_rates = [0.25] * 11
        nol_start = 0.0
        
        nol_series, ebit_after_tax = _compute_ebit_after_tax_with_nol(
            ebit=ebit, tax_rates=tax_rates, nol_start_year1=nol_start
        )
        
        # Year 0: 100 -> 75
        self.assertEqual(ebit_after_tax[0], 75.0)
        
        # Year 1: -50. EBIT after tax = -50. NOL = 0 - (-50) = 50.
        self.assertEqual(ebit_after_tax[1], -50.0)
        self.assertEqual(nol_series[1], 50.0)
        
        # Year 2: 100. NOL 50. Taxable = 50. Tax = 12.5. EBIT after tax = 87.5.
        self.assertEqual(ebit_after_tax[2], 87.5)
        self.assertEqual(nol_series[2], 0.0)

    def test_black_scholes_basic(self):
        # Comparison with known values (roughly)
        # S=100, K=100, T=1, sigma=0.2, r=0.05, div=0
        val = _black_scholes_call_value(
            stock_price=100.0,
            strike_price=100.0,
            maturity_years=1.0,
            volatility=0.2,
            riskfree_rate=0.05,
            dividend_yield=0.0
        )
        # Expected value is approx 10.45
        self.assertAlmostEqual(val, 10.45, places=2)

    def test_dilution_adjusted_options(self):
        inputs = OptionInputs(
            stock_price=100.0,
            strike_price=100.0,
            maturity_years=1.0,
            volatility=0.2,
            dividend_yield=0.0,
            riskfree_rate=0.05,
            options_outstanding=10.0,
            shares_outstanding=100.0
        )
        val = compute_dilution_adjusted_black_scholes_option_value(inputs)
        # With dilution, value should be slightly different than pure 10.45 * 10
        # The iteration should converge.
        self.assertTrue(val > 0)
        
        # Test zero options
        inputs_zero = OptionInputs(**{**inputs.__dict__, 'options_outstanding': 0.0})
        self.assertEqual(compute_dilution_adjusted_black_scholes_option_value(inputs_zero), 0.0)

    def test_margin_convergence(self):
        # base=0.1, target=0.2, conv=5, years=10
        # margins length should be 11
        margins = _compute_margins(
            base_ebit=10,
            base_revenues=100,
            year1_margin=0.12,
            target_margin=0.20,
            convergence_year=5,
            forecast_years=10
        )
        self.assertEqual(len(margins), 11)
        self.assertEqual(margins[0], 0.1)
        self.assertEqual(margins[1], 0.12)
        # Convergence at year 5
        self.assertAlmostEqual(margins[5], 0.20)
        # Years 6-10 should be target_margin
        for m in margins[6:]:
            self.assertEqual(m, 0.20)

    def test_reinvestment_lag(self):
        revenues = [100, 110, 121, 133.1] + [0]*7 # base + years 1-3
        # If lag=0, reinvestment in year 1 depends on delta(Rev Y1 - Base)
        # But engine uses:
        # left_index = year + lag - 1
        # right_index = year + lag
        # For year 1, lag 0: left=0, right=1 -> Rev[1] - Rev[0] = 110 - 100 = 10
        
        reinv_lag0 = _compute_reinvestment(
            revenues=revenues,
            growth_rates=[0.1]*10,
            sales_to_capital=[1.0]*10,
            override_reinvestment_lag=True,
            reinvestment_lag_years=0,
            stable_growth_rate=0.02
        )
        self.assertAlmostEqual(reinv_lag0[0], 10.0)
        
        # For year 1, lag 1 (default): left=1, right=2 -> Rev[2] - Rev[1] = 121 - 110 = 11
        reinv_lag1 = _compute_reinvestment(
            revenues=revenues,
            growth_rates=[0.1]*10,
            sales_to_capital=[1.0]*10,
            override_reinvestment_lag=False,
            reinvestment_lag_years=1,
            stable_growth_rate=0.02
        )
        self.assertAlmostEqual(reinv_lag1[0], 11.0)

    def test_input_validation(self):
        from valuation_engine.fcff_ginzu import GinzuInputs, compute_ginzu
        
        # Baseline valid inputs (minimal)
        valid_inputs = GinzuInputs(
            revenues_base=100, ebit_reported_base=10, book_equity=50, book_debt=50,
            cash=10, non_operating_assets=0, minority_interests=0,
            shares_outstanding=10, stock_price=10, rev_growth_y1=0.05, rev_cagr_y2_5=0.05,
            margin_y1=0.1, margin_target=0.1, margin_convergence_year=5,
            sales_to_capital_1_5=2.0, sales_to_capital_6_10=2.0,
            riskfree_rate_now=0.04, wacc_initial=0.08, tax_rate_effective=0.2, tax_rate_marginal=0.25
        )
        
        with self.assertRaises(InputError):
            compute_ginzu(replace(valid_inputs, revenues_base=-1))

        with self.assertRaises(InputError):
            compute_ginzu(replace(valid_inputs, shares_outstanding=0))

if __name__ == "__main__":
    unittest.main()
