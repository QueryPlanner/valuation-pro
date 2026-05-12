---
name: intrinsic-valuation
description: Performs end-to-end intrinsic valuation for a company. Extracts financial data from US (10-K/10-Q) and Indian (Annual/Quarterly reports) financial statements using scrapers or XBRL downloaders. Builds a bottom-up cost of capital (WACC), runs a base case DCF model using historical growth, performs a Monte Carlo simulation, and generates an HTML report. Use this skill when the user asks to value a company, extract valuation inputs, or run a discounted cash flow (DCF) model.
---

# Valuation End-to-End Workflow

<workflow>
## Step 1: Document Retrieval
Before extracting inputs, retrieve the necessary financial statements:
- **For US Companies:** Download the latest 10-K and the latest 10-Q using the appropriate scraper.
- **For Indian Companies (Primary Focus):** Use the NSE scraper or the XBRL downloader to download:
  1. The latest Annual Report.
  2. The most recent Quarterly Report.
  3. The *previous* Quarterly Report as well.
  *Note on Indian Companies:* Balance sheet estimates are typically only published twice a year (usually Q2 and Q4). If the most recent quarterly report lacks a balance sheet, you must refer to the previous quarterly report that contains one.

## Step 2: Input Extraction
- Do **NOT** use any automated AI pipelines (like `ai_pipeline.py`) to extract or guess inputs. 
- You must manually figure out the inputs yourself by analyzing the retrieved financial statements.
- Follow the detailed extraction rules defined in the `<extraction_rules>` section below to parse the retrieved documents into the required JSON format.

## Step 3: Valuation Execution (Base Case)
Once inputs are extracted and formatted:
- Run the valuation model located inside this repository.
- **Cost of Capital (WACC):** Must be calculated using the **bottom-up** philosophy utilizing the `wacc.py` module (`packages/valuation-engine/src/valuation_engine/wacc.py`). This module uses Damodaran's CSV lookups (`Industry_Averages(US).csv`, `Country_equity_risk_premiums.csv`, etc.) located in `packages/valuation-engine/src/valuation_engine/data/` to find the industry unlevered beta, weighted equity risk premium, and synthetic rating for the cost of debt.
- **Growth Estimates:** For the base case scenario, growth estimates must match the previous year's historical growth.

## Step 4: Monte Carlo Simulation
After establishing the base case:
- Run a Monte Carlo simulation.
- Vary the **growth rates** and **operating margins** to generate a distribution of possible intrinsic values.

## Step 5: Reporting
- Create a final **HTML report** detailing the intrinsic valuation results.
- The report must include the base case valuation, the simulation distributions, the computed cost of capital (bottom-up build), and all the primary inputs used.

## Step 6: Stories to Numbers (Valuation as a Picture)
- You must create a visual representation of the valuation that maps narrative "stories" to the quantitative assumptions in the model.
- Include a comprehensive HTML table structure in the final report that mirrors the "Valuation as a Picture" framework.
- The top section of this table must include narrative descriptions explicitly linking to the assumptions for:
  - **Growth Story:** Linked to revenue growth rates.
  - **Profitability Story:** Linked to operating margins.
  - **Growth Efficiency Story:** Linked to the Sales-to-Capital ratio.
  - **Risk Story & Competitive Advantages:** Linked to the Cost of Capital and Terminal Value assumptions.
- The middle section must show a 10-year time-series (plus a terminal year column) displaying the year-by-year outputs for: Revenue Growth, Revenue, Operating Margin, Operating Income, EBIT(1-t), Reinvestment, FCFF, Cost of Capital, and Cumulated WACC.
- The left sidebar must display the final value bridge: PV of Terminal Value, PV of Cash Flows, Probability of Failure, Value of Operating Assets, less Debt/Minority Interests, plus Cash/Non-Operating Assets, to arrive at the Value of Equity and Estimated Value per Share.

## Step 7: Valuation Diagnostic
- Use the **Task Tool** to spawn a `general` sub-agent to perform a rigorous diagnostic of the valuation outputs.
- Pass the base outputs (Current Price, Estimated Value, Growth Rate, Operating Margin, Sales to Capital, ROC, Cost of Capital) and ask the sub-agent to evaluate the model using the following 6-step framework:
  1. **Check revenue growth rate:** Compare forecasted growth against industry averages and recent history. Is it realistic?
  2. **Check dollar revenues:** Analyze total market size and the implied market share by Year 10.
  3. **Check your margins:** Compare the target margin to industry averages and historical unit economics.
  4. **Check how much you are reinvesting:** Evaluate the Sales-to-Capital ratio and whether the terminal ROC makes sense. Is reinvestment consistent with forecasted growth?
  5. **Risk Metrics:** Compare the Cost of Capital to the industry median. Assess the transition of the discount rate over time and the failure probability.
  6. **Price versus Value:** Analyze the delta between calculated value and current price. Identify which inputs (Growth, Margin, Sales/Capital, Cost of Capital) might need adjustment if the value seems too high or too low.
- Append the sub-agent's qualitative diagnostic report into the final HTML report under a "Valuation Diagnostic Report" section to provide a narrative critique of the model's assumptions.
</workflow>

<system_instructions>
You are an expert financial analyst. Your task is to extract specific financial metrics from the provided 10-K and 10-Q documents strictly based on the defined accounting rules.
</system_instructions>
<input_context>
Input Context See attached recent annual report. See attached recent quarterly report.
</input_context>
<extraction_rules>
Extraction Rules:
Timeframes for Financial Data: For all metrics in the "financial_data" section, extract both the Most Recent 12 Months (LTM) and the value from the Last 10-K prior to the LTM period. Bridge the gap using recent 10-Qs if mid-year.
Years since last 10K: If your most recent 12 months of data represent the most recent fiscal year, and your last 10K before LTM is the previous fiscal year, enter 1.00. If your most recent 12 months of data are midway through a fiscal year, enter the fraction of the most recent fiscal year is in this data. Thus, if your were valuing in Nov 2023, and using the trailing 12 months of data through September 2023, the 3rd quarter of the 2023 fiscal year, you would enter 0.75. Enter 0.5, if your data is through the second quarter, and 0.25, if is through the first quarter.
Revenues: If the company had no revenues, enter a small positive number to provide a base for growth rates. Use compact units (e.g., millions).
Revenue Splits (Region/Country & Business): Extract revenue breakdowns if available.
By Region/Country: Map operating regions or countries to the following exact list. Use "Rest of the World" for ambiguous countries or regions: Africa, Asia, Australia & New Zealand, Caribbean, Central and South America, Eastern Europe, Middle East, North America, Western Europe, Rest of the World.
By Business/Industry: Extract revenues and strictly map the company's reported business segments to the closest matching industry names from the <list_of_businesses> provided below. You MUST use only the exact industry names from that list as the keys in the "by_business" JSON object. Do not use the company's internal segment names.
Operating income or EBIT: Locate this on the income statement. It must be strictly below the gross income line and above the net income line. It must exclude interest income, interest expenses, and other income. Must be strictly below gross income.
Interest expense: Pull this from the income statement. It is required to calculate the cost of debt.
Cost of Capital Inputs (Debt): Extract the company's debt rating and the average maturity of its debt from the financial statements.
Book value of equity: Locate Shareholders' Equity on the liability side of the balance sheet. This includes paid-in capital, retained earnings, and offset by treasury stock. Crucial: If the company lists minority or non-controlling interests separately, aggregate them into this total. This number can be negative.
Book value of debt: Aggregate all interest-bearing debt (short-term, long-term, and short-term portion of long-term debt). Do not include accounts payable, supplier credit, or non-interest-bearing liabilities. You MUST also include all lease liabilities (both operating and finance leases, including their short-term and long-term portions) in the Book value of debt. Be sure to check the Leases footnote to find the total operating and finance lease liabilities if they are grouped into other current/long-term liabilities on the balance sheet.
R&D expenses to capitalize: Treat R&D as capital expenses. You must identify the company's primary industry from the <list_of_businesses> below to determine the amortization period. You must pull the current year's R&D expense and the historical R&D expenses for previous years corresponding to that specific amortization period. If the required years of historical R&D expenses are missing from the provided statements, request the older financial statements needed in the missing_documents_required array.
Cash and Marketable Securities: Found on the asset side of the balance sheet. Look out for companies that separate short-term and long-term investments.
Cross holdings and other non-operating assets: Include only assets not already generating cash flows. Exclude Goodwill and Brand Name. Look for long-term minority investments. Extract minority holdings in other companies (unconsolidated). If marked to market, extract the number directly. If recorded at book value, extract the book value.
Minority interests: Found on the liability side of the balance sheet. Represents equity in a cross-holding that your company has consolidated.
Number of shares outstanding: If Available in the financial statements
Effective tax rate: Compute this by taking the taxes paid (accrual number on the income statement) divided by the taxable income.
Employee Options: Locate the employee compensation footnotes and extract: (1) Total number of options outstanding, (2) Weighted average exercise price, and (3) Average maturity of the options.
</extraction_rules>
<list_of_businesses>
List of Businesses and R&D Amortization Periods Advertising (2), Aerospace/Defense (10), Air Transport (10), Aluminum (5), Apparel (3), Auto & Truck (10), Auto Parts (OEM) (5), Auto Parts (Replacement) (5), Bank (2), Bank (Canadian) (2), Bank (Foreign) (2), Bank (Midwest) (2), Beverage (Alcoholic) (3), Beverage (Soft Drink) (3), Building Materials (5), Cable TV (10), Canadian Energy (10), Cement & Aggregates (10), Chemical (Basic) (10), Chemical (Diversified) (10), Chemical (Specialty) (10), Coal/Alternate Energy (5), Computer & Peripherals (5), Computer Software & Svcs (3), Copper (5), Diversified Co. (5), Drug (10), Drugstore (3), Educational Services (3), Electric Util. (Central) (10), Electric Utility (East) (10), Electric Utility (West) (10), Electrical Equipment (10), Electronics (5), Entertainment (3), Environmental (5), Financial Services (2), Food Processing (3), Food Wholesalers (3), Foreign Electron/Entertn (5), Foreign Telecom. (10), Furn./Home Furnishings (3), Gold/Silver Mining (5), Grocery (2), Healthcare Info Systems (3), Home Appliance (5), Homebuilding (5), Hotel/Gaming (3), Household Products (3), Industrial Services (3), Insurance (Diversified) (3), Insurance (Life) (3), Insurance (Prop/Casualty) (3), Internet (3), Investment Co. (Domestic) (3), Investment Co. (Foreign) (3), Investment Co. (Income) (3), Machinery (10), Manuf. Housing/Rec Veh (5), Maritime (10), Medical Services (3), Medical Supplies (5), Metal Fabricating (10), Metals & Mining (Div.) (5), Natural Gas (Distrib.) (10), Natural Gas (Diversified) (10), Newspaper (3), Office Equip & Supplies (5), Oilfield Services/Equip. (5), Packaging & Container (5), Paper & Forest Products (10), Petroleum (Integrated) (5), Petroleum (Producing) (5), Precision Instrument (5), Publishing (3), R.E.I.T. (3), Railroad (5), Recreation (5), Restaurant (2), Retail (Special Lines) (2), Retail Building Supply (2), Retail Store (2), Securities Brokerage (2), Semiconductor (5), Semiconductor Cap Equip (5), Shoe (3), Steel (General) (10), Steel (Integrated) (10), Telecom. Equipment (10), Telecom. Services (10), Tobacco (3), Toiletries/Cosmetics (3), Trucking (5), Utility (Water) (10), Wireless Telecomm. (10)
</list_of_businesses>
<critical_rule>
CRITICAL RULE 1: Strict Availability. All inputs must be extracted based strictly on availability in the provided financial statements. Do not estimate, calculate, or extrapolate any missing numbers unless explicitly instructed by a rule. If any required input is not available, you must strictly request the missing financial statements in the missing_documents_required array.
CRITICAL RULE 2: Strict Industry Mapping. For "revenue_splits" -> "by_business", the industries in the <list_of_businesses> are the ONLY valid options. You are strictly forbidden from using the company's internal segment names.
</critical_rule>
<execution_instructions>
Execution Instructions
Read the footnotes to verify terms, accumulated NOLs, debt maturity profiles, and R&D figures.
Do not output conversational text. Output must strictly conform to the JSON schema.
</execution_instructions>
<output_format>
Output Format
{
  "financial_data": {
    "Revenues": {
      "Most_Recent_12_months": 0.0,
      "Last_10K_before_LTM": 0.0
    },
    "Operating_income_or_EBIT": {
      "Most_Recent_12_months": 0.0,
      "Last_10K_before_LTM": 0.0
    },
    "Interest_expense": {
      "Most_Recent_12_months": 0.0,
      "Last_10K_before_LTM": 0.0
    },
    "Book_value_of_equity": {
      "Most_Recent_12_months": 0.0,
      "Last_10K_before_LTM": 0.0
    },
    "Book_value_of_debt": {
      "Most_Recent_12_months": 0.0,
      "Last_10K_before_LTM": 0.0
    },
    "Cash_and_Marketable_Securities": {
      "Most_Recent_12_months": 0.0,
      "Last_10K_before_LTM": 0.0
    },
    "Cross_holdings_and_other_non_operating_assets": {
      "Most_Recent_12_months": 0.0,
      "Last_10K_before_LTM": 0.0
    },
    "Minority_interests": {
      "Most_Recent_12_months": 0.0,
      "Last_10K_before_LTM": 0.0
    }
  },
  "revenue_splits": {
    "by_region": {
      "Africa": 0.0,
      "Asia": 0.0,
      "Australia & New Zealand": 0.0,
      "Caribbean": 0.0,
      "Central and South America": 0.0,
      "Eastern Europe": 0.0,
      "Middle East": 0.0,
      "North America": 0.0,
      "Western Europe": 0.0,
      "Rest of the World": 0.0
    },
    "by_business": {
      "Industry_Name_Example_1": 0.0,
      "Industry_Name_Example_2": 0.0
    }
  },
  "cost_of_capital_inputs": {
    "debt_rating": "N/A",
    "average_maturity_of_debt_years": 0.0
  },
  "employee_options": {
    "total_options_outstanding": 0.0,
    "weighted_average_exercise_price": 0.0,
    "average_maturity_years": 0.0
  },
  "r_and_d_details": {
    "industry_name": "N/A",
    "amortization_period_years": 0,
    "current_year_expense": 0.0,
    "historical_expenses": {
      "Year_Minus_1": 0.0,
      "Year_Minus_2": 0.0,
      "Year_Minus_N": 0.0
    }
  },
  "single_value_metrics": {
    "Years_since_last_10K": 0.0,
    "Number_of_shares_outstanding": 0.0,
    "Effective_tax_rate": 0.0
  },
  "missing_documents_required": [
    "List specifically requested reports here if data is missing, otherwise leave empty"
  ]
}
</output_format>