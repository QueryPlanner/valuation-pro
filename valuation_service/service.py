from typing import Dict, Any, Optional
import logging
from .connectors import BaseConnector
from valuation_engine.fcff_ginzu.engine import compute_ginzu, GinzuInputs, GinzuOutputs

logger = logging.getLogger(__name__)

class ValuationService:
    def __init__(self, connector: BaseConnector):
        self.connector = connector

    def calculate_valuation(self, ticker: str, assumptions: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Orchestrates the valuation process.
        """
        financials = self.connector.get_financials(ticker)
        market_data = self.connector.get_market_data(ticker)
        
        inputs = self._map_data_to_inputs(ticker, financials, market_data, assumptions or {})
        
        # Run engine
        outputs = compute_ginzu(inputs)
        
        # Convert dataclass to dict for API response
        return outputs.__dict__

    def _map_data_to_inputs(
        self, 
        ticker: str, 
        financials: Dict[str, Any], 
        market_data: Dict[str, Any], 
        assumptions: Dict[str, Any]
    ) -> GinzuInputs:
        """
        Maps raw connector data to GinzuInputs, applying defaults and overrides.
        """
        income = financials.get("income_statement", {})
        balance = financials.get("balance_sheet", {})
        
        # 1. Find most recent period
        # Keys are dates. Sort and take latest.
        # Assuming keys are comparable (strings 'YYYY-MM-DD' or Timestamps)
        if not income:
             raise ValueError(f"No income statement data found for {ticker}")
        
        latest_date = sorted(income.keys())[-1]
        
        # Helpers to safely get values
        def get_inc(field, default=0.0):
            val = income[latest_date].get(field, default)
            if val is None:
                return default
            try:
                return float(val)
            except (ValueError, TypeError):
                return default
            
        def get_bal(field, default=0.0):
            # Balance sheet might have different latest date? Usually same.
            # If not, try latest available in balance sheet
            if not balance: return default
            bs_date = sorted(balance.keys())[-1]
            val = balance[bs_date].get(field, default)
            if val is None:
                return default
            try:
                return float(val)
            except (ValueError, TypeError):
                return default

        # 2. Extract Base Inputs
        revenues = get_inc("Total Revenue") or get_inc("TotalRevenue")
        ebit = get_inc("EBIT") or get_inc("Operating Income") or get_inc("OperatingIncome")
        
        # Equity: Try "Total Equity Gross Minority Interest" first, then "Stockholders Equity"
        book_equity = get_bal("Total Equity Gross Minority Interest") or get_bal("Stockholders Equity") or get_bal("TotalStockholderEquity")
        
        # Debt: "Total Debt"
        book_debt = get_bal("Total Debt") or get_bal("TotalDebt")
        
        # Cash: "Cash And Cash Equivalents"
        cash = get_bal("Cash And Cash Equivalents") or get_bal("CashAndCashEquivalents")
        
        # Non-Op Assets
        # yfinance varies. "InvestmentProperties", "LongTermInvestments"?
        # Be conservative: 0 unless explicit.
        non_op = get_bal("Investment Properties") 
        
        minority = get_bal("Minority Interest") or get_bal("MinorityInterest")
        
        # Shares
        # yfinance doesn't always put shares in balance sheet.
        # But market_data often has 'sharesOutstanding' or we use 'market_cap / price'
        shares = market_data.get("shares_outstanding")
        if not shares:
            # Derive from market cap and price
            # CRITICAL: Check price > 0 to avoid ZeroDivisionError
            price = market_data.get("price")
            if market_data.get("market_cap") and price and price > 0:
                shares = market_data["market_cap"] / price
            else:
                # Fallback to balance sheet 'Share Issued'? (Unreliable)
                # shares = 1000000.0 # Critical fallback to avoid div/0, usually caught earlier
                raise ValueError(f"Could not determine Share Count for {ticker}. Cannot calculate per-share value.")
        
        stock_price = market_data.get("price", 0.0)
        risk_free = market_data.get("risk_free_rate", 0.04)

        # 3. Calculate Derived Defaults (Assumptions)
        
        # Tax Rates
        pretax_income = get_inc("Pretax Income") or get_inc("PretaxIncome")
        tax_provision = get_inc("Tax Provision") or get_inc("TaxProvision")
        
        if pretax_income > 0:
            tax_rate_effective = tax_provision / pretax_income
            # Cap realistic bounds (0% to 50%)
            tax_rate_effective = max(0.0, min(0.5, tax_rate_effective))
        else:
            tax_rate_effective = 0.20 # Fallback
            
        tax_rate_marginal = 0.25 # US Default
        
        # Sales to Capital
        # Invested Capital = Book Equity + Book Debt - Cash
        invested_capital = book_equity + book_debt - cash
        if invested_capital > 0:
            sales_to_capital = revenues / invested_capital
        else:
            sales_to_capital = 1.5 # Global average fallback
            
        # Margins
        current_margin = ebit / revenues if revenues > 0 else 0.10
        
        # 4. Construct Inputs (with Overrides)
        inputs = GinzuInputs(
            revenues_base=revenues,
            ebit_reported_base=ebit,
            book_equity=book_equity,
            book_debt=book_debt,
            cash=cash,
            non_operating_assets=assumptions.get("non_operating_assets", non_op),
            minority_interests=assumptions.get("minority_interests", minority),
            shares_outstanding=shares,
            stock_price=stock_price,
            
            # Assumptions
            rev_growth_y1=assumptions.get("rev_growth_y1", risk_free), # Conservative default
            rev_cagr_y2_5=assumptions.get("rev_cagr_y2_5", risk_free),
            margin_y1=assumptions.get("margin_y1", current_margin),
            margin_target=assumptions.get("margin_target", current_margin),
            margin_convergence_year=assumptions.get("margin_convergence_year", 5),
            sales_to_capital_1_5=assumptions.get("sales_to_capital_1_5", sales_to_capital),
            sales_to_capital_6_10=assumptions.get("sales_to_capital_6_10", sales_to_capital),
            riskfree_rate_now=assumptions.get("riskfree_rate_now", risk_free),
            wacc_initial=assumptions.get("wacc_initial", 0.08), # Placeholder default
            tax_rate_effective=assumptions.get("tax_rate_effective", tax_rate_effective),
            tax_rate_marginal=assumptions.get("tax_rate_marginal", tax_rate_marginal),
            
            # Toggles
            capitalize_rnd=assumptions.get("capitalize_rnd", False),
            capitalize_operating_leases=assumptions.get("capitalize_operating_leases", False),
            has_employee_options=assumptions.get("has_employee_options", False),
            
            # Common overrides
            override_stable_wacc=assumptions.get("override_stable_wacc", False),
            stable_wacc=assumptions.get("stable_wacc", None),
            mature_market_erp=assumptions.get("mature_market_erp", 0.0433)
        )
        
        return inputs