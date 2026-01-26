from typing import Dict, Any, Optional
import logging
from .connectors import BaseConnector
from valuation_engine.fcff_ginzu.engine import (
    compute_ginzu, 
    GinzuInputs, 
    GinzuOutputs,
    RnDCapitalizationInputs,
    compute_rnd_capitalization_adjustments
)

logger = logging.getLogger(__name__)

class ValuationService:
    def __init__(self, connector: BaseConnector):
        self.connector = connector

    def calculate_valuation(self, ticker: str, assumptions: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Orchestrates the valuation process.
        """
        # 1. Fetch normalized inputs from Connector
        # This encapsulates source-specific logic (LTM, etc.)
        fetched_inputs = self.connector.get_valuation_inputs(ticker)
        
        # 2. Map to GinzuInputs (Merging with assumptions)
        inputs = self._prepare_ginzu_inputs(fetched_inputs, assumptions or {})
        
        # 3. Run Engine
        outputs = compute_ginzu(inputs)
        
        # 4. Return results (Dict for API)
        return outputs.__dict__

    def _prepare_ginzu_inputs(self, data: Dict[str, Any], assumptions: Dict[str, Any]) -> GinzuInputs:
        """
        Merges fetched data with user assumptions and applies default heuristics.
        Handles complex logic like R&D Capitalization.
        """
        
        # --- 1. R&D Capitalization Logic ---
        # If fetched data has history and user didn't disable it
        rnd_history = data.get('rnd_history', [])
        current_rnd = data.get('rnd_expense', 0.0)
        
        capitalize_rnd = assumptions.get('capitalize_rnd', False)
        
        # Auto-enable if not specified and data exists
        if 'capitalize_rnd' not in assumptions and current_rnd > 0 and len(rnd_history) > 0:
             # Default behavior: Do not auto-capitalize unless requested, to match simple output first?
             # Or match run_yf_valuation.py logic which had it disabled by default?
             # Let's default to False unless user asks, for transparency.
             capitalize_rnd = False

        rnd_asset = 0.0
        rnd_ebit_adj = 0.0
        
        if capitalize_rnd:
            try:
                # Prepare past expenses (excluding current year from history if it overlaps?)
                # rnd_history from connector is [Year0, Year-1, Year-2...] usually
                # Engine needs [Year-1, Year-2, ...].
                # Yahoo Connector provides ann_inc sorted newest first. 
                # If current_rnd comes from LTM, and history comes from Annual, 
                # we usually use the Annual history for amortization.
                
                # Heuristic: Take up to 5 years from history
                amort_years = assumptions.get('rnd_amortization_years', 5)
                past_rnd = []
                # If the first element of history looks like current year, skip it?
                # Simplify: Just take the first N from history provided by connector
                for i in range(amort_years):
                    val = rnd_history[i] if i < len(rnd_history) else 0.0
                    past_rnd.append(val)
                
                rnd_inputs = RnDCapitalizationInputs(
                    amortization_years=amort_years,
                    current_year_rnd_expense=float(current_rnd),
                    past_year_rnd_expenses=past_rnd
                )
                rnd_asset, rnd_ebit_adj = compute_rnd_capitalization_adjustments(rnd_inputs)
            except Exception as e:
                logger.warning(f"R&D Capitalization failed: {e}")
                capitalize_rnd = False

        # --- 2. Base Financials ---
        revenues = data.get('revenues_base', 0.0)
        ebit = data.get('ebit_reported_base', 0.0)
        
        # Invested Capital Calculation for Sales/Cap Ratio
        book_equity = data.get('book_equity', 0.0)
        book_debt = data.get('book_debt', 0.0)
        cash = data.get('cash', 0.0)
        
        # Adjust Book Equity for R&D if capitalized
        if capitalize_rnd:
            book_equity += rnd_asset

        invested_capital = book_equity + book_debt - cash
        
        sales_to_capital_actual = 1.5 # Default
        if invested_capital > 0 and revenues > 0:
            sales_to_capital_actual = revenues / invested_capital
            
        # Margins
        # If capitalizing R&D, use adjusted EBIT
        base_ebit_adj = ebit + rnd_ebit_adj if capitalize_rnd else ebit
        current_margin = base_ebit_adj / revenues if revenues > 0 else 0.10

        # --- 3. Defaults & Overrides ---
        risk_free = data.get('risk_free_rate', 0.04)
        
        # Helper to pick Assumption > Data > Default
        def get_val(key, data_key, default):
            if key in assumptions: return assumptions[key]
            if data_key in data: return data[data_key]
            return default

        return GinzuInputs(
            revenues_base=revenues,
            ebit_reported_base=ebit,
            book_equity=book_equity,
            book_debt=book_debt,
            cash=cash,
            non_operating_assets=get_val("non_operating_assets", "cross_holdings", 0.0),
            minority_interests=get_val("minority_interests", "minority_interest", 0.0),
            shares_outstanding=data.get('shares_outstanding', 1.0), # Avoid div/0
            stock_price=data.get('stock_price', 0.0),
            
            # Value Drivers
            rev_growth_y1=assumptions.get("rev_growth_y1", 0.05),
            rev_cagr_y2_5=assumptions.get("rev_cagr_y2_5", 0.05),
            margin_y1=assumptions.get("margin_y1", current_margin),
            margin_target=assumptions.get("margin_target", current_margin),
            margin_convergence_year=assumptions.get("margin_convergence_year", 5),
            
            sales_to_capital_1_5=assumptions.get("sales_to_capital_1_5", sales_to_capital_actual),
            sales_to_capital_6_10=assumptions.get("sales_to_capital_6_10", sales_to_capital_actual),
            
            riskfree_rate_now=assumptions.get("riskfree_rate_now", risk_free),
            wacc_initial=assumptions.get("wacc_initial", 0.08),
            
            tax_rate_effective=get_val("tax_rate_effective", "effective_tax_rate", 0.20),
            tax_rate_marginal=get_val("tax_rate_marginal", "marginal_tax_rate", 0.25),
            
            # R&D
            capitalize_rnd=capitalize_rnd,
            rnd_asset=rnd_asset,
            rnd_ebit_adjustment=rnd_ebit_adj,
            
            # Leases (Placeholder for now as YF usually bundles them)
            capitalize_operating_leases=assumptions.get("capitalize_operating_leases", False),
            lease_debt=assumptions.get("lease_debt", 0.0),
            lease_ebit_adjustment=assumptions.get("lease_ebit_adjustment", 0.0),
            
            # Options
            has_employee_options=assumptions.get("has_employee_options", False),
            options_value=assumptions.get("options_value", 0.0),
            
            # Overrides
            override_stable_wacc=assumptions.get("override_stable_wacc", False),
            stable_wacc=assumptions.get("stable_wacc", None),
            mature_market_erp=assumptions.get("mature_market_erp", 0.0460),
            
            override_perpetual_growth=True,
            perpetual_growth_rate=assumptions.get("perpetual_growth_rate", risk_free),
            
            override_tax_rate_convergence=assumptions.get("override_tax_rate_convergence", False),
            override_riskfree_after_year10=assumptions.get("override_riskfree_after_year10", False),
            override_stable_roc=assumptions.get("override_stable_roc", False),
            override_failure_probability=assumptions.get("override_failure_probability", False),
            has_nol_carryforward=assumptions.get("has_nol_carryforward", False),
            override_reinvestment_lag=assumptions.get("override_reinvestment_lag", False),
            override_trapped_cash=assumptions.get("override_trapped_cash", False)
        )
