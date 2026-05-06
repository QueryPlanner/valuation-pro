import os
import json
import logging
from typing import Dict, Any
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import concurrent.futures

load_dotenv()

from valuation_service.services.xbrl_preprocessor import load_xbrl_data
from valuation_service.connectors.yahoo import YahooFinanceConnector
from valuation_service.services.ai_schema import ValuationAssumptions

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are an expert financial analyst. Your task is to calculate the base inputs required for a DCF valuation model using provided XBRL financial data and real-time market data.

Raw accounting data is flawed for valuation purposes. Accountants routinely misclassify expenses, and blindly trusting book values will skew your numbers. You cannot just look up a line item; you must actively convert and adjust the data to reflect economic reality.
Here are the specific definitions and adjustments required to pull inputs from financial statements based on Aswath Damodaran's valuation rules for Indian reports:

1. revenues_base: Pull this from the most recent 12 months. If you are in the middle of a year, combine the last Annual report with the most recent quarterly reports to get a trailing 12-month figure (TTM). Formula: TTM = Current YTD + Annual - Prior YTD. (If Current YTD is a full year, just use Current YTD).
2. ebit_reported_base: It is defined as the profit generated strictly from the company's continuous, core business activities. What it includes: Operating Revenue: Money earned directly from primary business operations. Operating Expenses: The recurring costs required to run the business day-to-day (e.g., employee salaries, technical sub-contractors, travel, and depreciation). What it strictly excludes: Exceptional Items: One-time, non-recurring events that skew normal profitability. Non-Operating Income: Money made outside the core business, such as interest on tax refunds or investment returns. Finance Costs: Interest expenses related to debt. Taxes: Income tax expenses. This metric is the purest representation of a company's sustainable, recurring earning power because it strips out the noise of financing decisions, tax rates, and one-off anomalies. To calculate this using the provided tags: ProfitBeforeExceptionalItemsAndTax - OtherIncome + FinanceCosts.
3. book_equity: Found on the liability side of the balance sheet. Use EquityAttributableToOwnersOfParent. (Minority interest is handled separately).
4. book_debt: Do not just look at long-term debt. You must aggregate all interest-bearing debt AND lease debt. This includes long-term debt (BorrowingsNoncurrent), short-term debt (BorrowingsCurrent), and Lease Liabilities. In Indian XBRL, Lease Liabilities are found as "OtherNoncurrentFinancialLiabilities [Description='Lease liabilities']" and "OtherCurrentFinancialLiabilities [Description='Lease liabilities']". YOU MUST ADD ALL THESE TOGETHER to get book_debt.
5. cash: Found on the asset side of the balance sheet. Sometimes broken out into short-term or long-term investments. Aggregate CashAndCashEquivalents, BankBalanceOtherThanCashAndCashEquivalents, and CurrentInvestments (which represents short-term marketable securities). DO NOT put CurrentInvestments in cross holdings!
6. non_operating_assets: Cross Holdings. Look for long-term investments where the company owns a minority stake (NoncurrentInvestments). Do not include Goodwill or Brand Name. Do not include CurrentInvestments.
7. minority_interests: Minority interest reflects the book value of the equity in a consolidated subsidiary that does not belong to you. Look for NonControllingInterests or NonControllingInterest on the liability side.
8. shares_outstanding: Do not use the share count listed on the balance sheet; it changes too frequently. Use the shares_outstanding provided in the market_data.
9. rev_growth_y1: Revenue growth for next year. Calculate the historical growth rate by comparing TTM revenues to the previous Annual revenue. Cap it at a reasonable number (e.g., 15%).
10. rev_cagr_y2_5: Revenue CAGR for years 2-5. Should slowly mean-revert towards the risk-free rate.
11. margin_y1: Operating margin for next year. Calculate as ebit_reported_base / revenues_base.
12. margin_target: Target operating margin. For mature companies, it can be close to the current operating margin.
13. margin_convergence_year: Year to converge to target margin (usually 5).
14. sales_to_capital_1_5: Sales to capital ratio for years 1-5. Invested Capital = book_equity + book_debt - cash. Then ratio = revenues_base / Invested Capital.
15. sales_to_capital_6_10: Sales to capital ratio for years 6-10. Usually the same as years 1-5.
16. tax_rate_effective: Do not use the statutory rate. Compute the effective rate by taking the taxes paid (TaxExpense) and dividing it by the taxable income (ProfitBeforeTax). If less than zero, floor it at 0.
17. tax_rate_marginal: This is a statutory tax rate. Default to 30% (0.30) for India.

You MUST output ONLY a valid JSON object representing the valuation assumptions. Do not output any markdown formatting, code blocks, or explanatory text outside the JSON.
The JSON must strictly conform to the following schema:
"""

MODELS_TO_TEST = [
    "google/gemini-3-flash-preview"
]

def process_model(model: str, client: OpenAI, system_prompt: str, context: Dict[str, Any]) -> tuple:
    print(f"\nTesting model: {model}")
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Extract valuation inputs for INFY based on this data:\n{json.dumps(context, indent=2)}"}
            ],
            temperature=0.1
        )
        
        raw_content = response.choices[0].message.content
        
        if raw_content.strip().startswith("```"):
            lines = raw_content.strip().split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            raw_content = "\n".join(lines)
            
        try:
            parsed_json = json.loads(raw_content)
            validated_result = ValuationAssumptions(**parsed_json).model_dump()
            print(f"✅ Success for {model}")
            return model, {"status": "success", "data": validated_result}
        except json.JSONDecodeError as e:
            print(f"❌ JSON Parse Error for {model}")
            return model, {"status": "error", "error": f"JSON Parse Error: {e}", "raw": raw_content}
        except Exception as e:
            print(f"❌ Validation Error for {model}")
            return model, {"status": "error", "error": f"Validation Error: {e}", "raw": raw_content}
            
    except Exception as e:
        print(f"❌ API Error for {model}: {e}")
        return model, {"status": "error", "error": f"API Error: {e}"}

def run_experiment(symbol: str):
    print(f"Gathering data for {symbol}...")
    try:
        xbrl_data = load_xbrl_data(symbol)
    except FileNotFoundError:
        print(f"XBRL data for {symbol} not found.")
        return

    try:
        yf_connector = YahooFinanceConnector()
        market_data = yf_connector.get_valuation_inputs(f"{symbol}.NS")
    except Exception as e:
        print(f"Failed to fetch Yahoo Finance data for {symbol}: {e}")
        return

    context = {
        "xbrl_financials": xbrl_data,
        "market_data": {
            "stock_price": market_data.get("stock_price"),
            "shares_outstanding": market_data.get("shares_outstanding"),
            "risk_free_rate": market_data.get("risk_free_rate", 0.07),
        }
    }

    api_key = os.getenv("OPENROUTER_API_KEY")
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    schema_str = json.dumps(ValuationAssumptions.model_json_schema(), indent=2)
    system_prompt = SYSTEM_PROMPT + "\n" + schema_str

    results = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(MODELS_TO_TEST)) as executor:
        future_to_model = {
            executor.submit(process_model, model, client, system_prompt, context): model 
            for model in MODELS_TO_TEST
        }
        
        for future in concurrent.futures.as_completed(future_to_model):
            model = future_to_model[future]
            try:
                m, res = future.result()
                results[m] = res
            except Exception as exc:
                print(f"{model} generated an exception: {exc}")

    output_file = "infosys_model_experiment.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
        
    print(f"\nExperiment complete. Results saved to {output_file}")

if __name__ == "__main__":
    run_experiment("INFY")
