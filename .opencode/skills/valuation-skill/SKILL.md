---
name: valuation-skill
description: Performs end-to-end intrinsic valuation for a company. Extracts financial data from US (10-K/10-Q) and Indian (Annual/Quarterly reports) financial statements using scrapers or XBRL downloaders. Builds a bottom-up cost of capital (WACC), runs a base case DCF model using historical growth, performs a Monte Carlo simulation, and generates an HTML report. Use this skill when the user asks to value a company, extract valuation inputs, or run a discounted cash flow (DCF) model.
license: MIT
compatibility: opencode
metadata:
  audience: developers
  workflow: valuation
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
  *Tooling:* You may use the included `scripts/download_xbrl.py` script. If it requires authentication, ask the user to provide the XBRL cookie.

## Step 2: Input Extraction
- Do **NOT** use any automated AI pipelines (like `ai_pipeline.py`) to extract or guess inputs. 
- You must manually figure out the inputs yourself by analyzing the retrieved financial statements.
- Follow the detailed extraction rules defined in `references/extraction_rules.md` to parse the retrieved documents.
- Reference `references/business_list.md` to properly map businesses and R&D amortization periods.
- The final output must conform strictly to the schema defined in `assets/output_schema.json`.

## Step 3: Valuation Execution (Base Case)
Once inputs are extracted and formatted, you MUST ask the user for the following key valuation assumptions using the `question` tool before proceeding:
1. Revenue growth rate for next year
2. Operating Margin for next year
3. Compounded annual revenue growth rate - years 2-5
4. Target pre-tax operating margin
5. Year of convergence for margin

After receiving these inputs from the user:
- Run the valuation model located inside this repository, or utilize the provided `scripts/calculate_valuation.py`.
- **Cost of Capital (WACC):** Must be calculated using the **bottom-up** philosophy utilizing the `scripts/wacc.py` module. This module uses Damodaran's CSV lookups located in `references/` (e.g., `industry_averages_us.csv`, `country_equity_risk_premiums.csv`, `industry_averages_global.csv`) to find the industry unlevered beta, weighted equity risk premium, and synthetic rating for the cost of debt.
- **Growth and Margin Estimates:** Use the user-provided growth and margin estimates to drive the base case scenario instead of relying solely on historical trailing averages.

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
You are an expert financial analyst. Your task is to extract specific financial metrics from the provided 10-K and 10-Q documents strictly based on the defined accounting rules in `references/extraction_rules.md`.
</system_instructions>
<input_context>
Input Context See attached recent annual report. See attached recent quarterly report.
</input_context>

<execution_instructions>
Execution Instructions
Read the footnotes to verify terms, accumulated NOLs, debt maturity profiles, and R&D figures.
Do not output conversational text. Output must strictly conform to the JSON schema defined in `assets/output_schema.json`.
</execution_instructions>