import json
import logging
import os
from typing import Any, Dict

from openai import OpenAI

from valuation_service.connectors.yahoo import YahooFinanceConnector
from valuation_service.services.ai_schema import ValuationAssumptions
from valuation_service.services.xbrl_preprocessor import load_xbrl_data

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


def extract_ai_inputs(symbol: str, yf_ticker: str = None) -> Dict[str, Any]:
    """Runs the AI pipeline to extract valuation inputs."""
    if not yf_ticker:
        yf_ticker = f"{symbol}.NS"

    # 1. Load Condensed XBRL Data
    try:
        xbrl_data = load_xbrl_data(symbol)
    except FileNotFoundError:
        logger.error(f"XBRL data for {symbol} not found.")
        xbrl_data = {"error": "No local XBRL data found."}

    # 2. Fetch Live Market Data
    market_data = {}
    try:
        yf_connector = YahooFinanceConnector()
        market_data = yf_connector.get_valuation_inputs(yf_ticker)
    except Exception as e:
        logger.warning(f"Failed to fetch Yahoo Finance data for {yf_ticker}: {e}")

    # 3. Prepare Context
    context = {
        "xbrl_financials": xbrl_data,
        "market_data": {
            "stock_price": market_data.get("stock_price"),
            "shares_outstanding": market_data.get("shares_outstanding"),
            "risk_free_rate": market_data.get("risk_free_rate", 0.07),  # Default fallback for India approx
        },
    }

    # 4. Call OpenAI (via OpenRouter)
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not found in environment variables.")

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    try:
        # Use instructor or native structured outputs. Here using native JSON schema mapping.
        schema = ValuationAssumptions.model_json_schema()
        schema["additionalProperties"] = False

        response = client.chat.completions.create(
            model="google/gemini-3-flash-preview",  # Using Gemini 3 Flash Preview
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Extract valuation inputs for {symbol} based on this data:\n{json.dumps(context, indent=2)}",
                },
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "ValuationAssumptions", "schema": schema, "strict": True},
            },
            # extra_body={"reasoning": {"enabled": True}} # Disabled temporarily as gpt-4o native doesn't support this via strict json schema in OR easily without specific models
        )

        raw_content = response.choices[0].message.content

        # Clean markdown code blocks if any
        if raw_content.startswith("```"):
            lines = raw_content.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            raw_content = "\n".join(lines)

        result_json = json.loads(raw_content)

        # Sometimes models return a dict for rationale instead of a string
        if isinstance(result_json.get("rationale"), dict):
            result_json["rationale"] = json.dumps(result_json["rationale"])

        # Validate through Pydantic
        validated_result = ValuationAssumptions(**result_json)
        return validated_result.model_dump()

    except Exception as e:
        logger.error(f"AI Extraction failed: {e}")
        raise
