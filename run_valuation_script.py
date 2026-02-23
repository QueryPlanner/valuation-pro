import json
import sys
import argparse
from valuation_service.services.valuation import ValuationService
from valuation_service.connectors.yahoo import YahooFinanceConnector

def main():
    parser = argparse.ArgumentParser(description="Run a quick valuation for any company via Yahoo Finance.")
    parser.add_argument("ticker", type=str, help="The ticker symbol to value (e.g., 'AAPL', '2280.SR')")
    parser.add_argument("--query", "-q", type=str, help="Search for a company ticker before valuing", default=None)
    args = parser.parse_args()

    connector = YahooFinanceConnector()
    service = ValuationService(connector)

    if args.query:
        print(f"Searching for '{args.query}'...")
        results = service.search_companies(args.query)
        if not results:
            print("No matching companies found.")
            return
        
        print("\nSearch Results:")
        for r in results:
            print(f"- {r['symbol']}: {r['longname'] or r['shortname']} ({r['exchange']} - {r['quoteType']})")
        print(f"\nProceeding with valuation for user-specified ticker: {args.ticker}\n")

    # You can update these generic assumptions as needed, 
    # or remove them to rely entirely on the engine's auto-heuristics.
    # Currently maintaining the default overrides previously requested for reference.
    assumptions = {
        "tax_rate_effective": 0.17,
        "tax_rate_marginal": 0.25,
        "rev_growth_y1": 0.04,
        "margin_y1": 0.1406,
        "rev_cagr_y2_5": 0.05,
        "margin_target": 0.1406,
        "margin_convergence_year": 5,
        "sales_to_capital_1_5": 1.71,
        "sales_to_capital_6_10": 1.71,
        "riskfree_rate_now": 0.0458,
        "wacc_initial": 0.0706
    }
    
    print(f"Running valuation for {args.ticker}...")
    try:
        result = service.calculate_valuation(args.ticker, assumptions=assumptions)
        print("\nValuation Summary:")
        print(f"Value of Equity: {result.get('value_of_equity', 'N/A'):,.2f}")
        print(f"Value per Share: {result.get('estimated_value_per_share', 'N/A'):.2f}")
        print(f"Current Price (% of value): {result.get('price_as_percent_of_value', 'N/A') * 100:.2f}%")
        
        # Uncomment to see full JSON payload:
        # print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error calculating valuation for {args.ticker}: {e}")

if __name__ == "__main__":
    main()
