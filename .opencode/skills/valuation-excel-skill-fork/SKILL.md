---
name: valuation-excel-skill-fork
description: Performs end-to-end valuation using an Excel template. Finds PDF/HTML links to financial reports using AI, and then the agent itself calculates the valuation inputs using the provided prompt to organize thoughts instead of using Gemini API, populates a predefined Excel valuation spreadsheet using openpyxl, and uploads to Google Drive.
license: MIT
compatibility: opencode
metadata:
  audience: developers
  workflow: valuation-excel
---

# Valuation Excel End-to-End Workflow

<workflow>
## Step 1: Document Retrieval via Gemini
- Use the `get_financial_reports.py` script provided within this skill directory using `uv run python`.
- Example command: `uv run python .opencode/skills/valuation-excel-skill-fork/get_financial_reports.py --company "Company Name"`
- This script uses the Gemini API with Google Search grounding to find downloadable PDF links for the target company's latest Annual Report and the last two Quarterly Reports.
- Ensure the output is a structured JSON containing the company name and URLs to the PDFs.

## Step 2: Download Reports by Agent
- You, the agent, must download the PDF or SEC HTML reports locally.
- Use the links obtained in Step 1. However, since AI models can hallucinate broken links (404 Not Found), you must verify them.
- If the links are broken, autonomously search the web (e.g., using Python scripts fetching from SEC EDGAR API, `duckduckgo` search, or `curl`) to find the actual, working links for the latest Annual Report and the recent Quarterly Reports.
- Download them locally. If the target is an HTML file, save it.

## Step 3: Input Extraction by Agent
- The agent should itself calculate the valuation inputs from the downloaded reports instead of using the Gemini API.
- **CRITICAL DATA EXTRACTION RULE:** If the downloaded SEC reports are large HTML or PDF files, DO NOT try to read the entire file using the `read` tool, as you will run into offset and schema limits. Instead, write a quick Python script using `pandas.read_html` or `BeautifulSoup` to extract the Income Statement and Balance Sheet tables into small `.csv` or `.txt` files locally. Then, read those smaller files to extract your inputs.
- While extracting and calculating the valuation inputs, use this specific instruction: "Organize these unstructured thoughts into a clear, polished version without adding, removing, or changing meaning. Improve flow and readability while keeping all original ideas intact".
- **CRITICAL JSON RULE:** The output must be saved as a structured JSON file (e.g., `<company_name>_valuation_inputs.json`). You MUST strictly maintain the **nested schema** defined in `prompt.txt`. Do NOT output a flat list or flat dictionary, as the spreadsheet filling script requires nested paths (e.g., `financial_data.Revenues.Most_Recent_12_months`) and will default to zeros otherwise.

## Step 4: Populate the Excel Spreadsheet
- Use the `fill_excel.py` script provided within this skill directory using `uv run python`.
- Example command: `uv run python .opencode/skills/valuation-excel-skill-fork/fill_excel.py --company ... --inputs ...`
- We strongly recommend passing the `--ticker` flag (e.g. `--ticker NVDA`) so the script can automatically pull the current stock price and risk-free rate using `yfinance`.
- **Cost of Capital Nuances:** 
  - The script intelligently handles mapping both the `Input sheet` and the `Cost of capital worksheet`. 
  - It links the calculated Cost of Capital back to the Input sheet dynamically.
  - **Single vs Multibusiness:** The script detects whether the company operates in multiple industries based on the extracted `revenue_splits -> by_business` array. 
    - If single, it uses `Single Business(Global)` and references the primary industry.
    - If multibusiness, it changes the approach to `Multibusiness(US)`, clears out template dummy data, and populates the specific industries and their revenue breakdowns so the spreadsheet calculates a weighted composite beta and cost of capital.
- The output will be a newly saved Excel file (e.g., `<company_name>_valuation.xlsx`).

## Step 5: Upload to Google Sheets
- Use the `upload_to_sheets.py` script provided within this skill directory.
- This script accepts the flags (`--company`, `--file`).
- It will authenticate using OAuth 2.0 credentials (`client_secret_*.json` and the generated `token.json` session file).
- The script intelligently queries Google Drive first. If a sheet with the name `<company_name> Valuation (Auto-filled)` already exists, it will **update** that sheet in place. If not, it will create a new one.
- Output the `webViewLink` to the user so they can view the fully calculated intrinsic valuation in Google Sheets.

## Step 6: Guide User on Story Building
- Do **NOT** attempt to automate, extract, or fill in the "Stories to Numbers" tab via script.
- Instead, guide the user on what to look for and where to look for it. Provide them with instructions to open the generated Google Sheet, navigate to the "Stories to Numbers" tab, and create their own story about the company.
- Explicitly tell the user to think about the company's business model and manually fill in their qualitative assumptions (e.g., Growth Story, Profitability Story, Risk Story) in cells A2, A3, and G9 through G14 so that they can anchor the quantitative outputs to a solid narrative.
</workflow>
