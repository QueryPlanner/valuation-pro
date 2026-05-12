---
name: valuation-excel-skill
description: Performs end-to-end valuation using an Excel template. Finds PDF links to financial reports using Gemini, downloads them, uploads them to Gemini Files API to extract valuation inputs, populates a predefined Excel valuation spreadsheet (e.g., fcffsimpleginzu.xlsx) using openpyxl, and uploads the populated spreadsheet to Google Drive as a Google Sheet.
license: MIT
compatibility: opencode
metadata:
  audience: developers
  workflow: valuation-excel
---

# Valuation Excel End-to-End Workflow

<workflow>
## Step 1: Document Retrieval via Gemini
- Use the `get_financial_reports.py` script provided within this skill directory.
- This script accepts a `--company` flag and uses the Gemini API (e.g., `gemini-3-flash-preview`) with Google Search grounding to find downloadable PDF links for the target company's latest Annual Report and the last two Quarterly Reports (financial results).
- Ensure the output is a structured JSON containing the company name and URLs to the PDFs.

## Step 2: Download and Upload to Gemini Files API
- Use the `get_valuation_inputs.py` script provided within this skill directory.
- This script accepts the flags (`--company`, `--reports`, `--prompt`).
- It uses a compliant `User-Agent` to download the SEC reports. If the target link is an HTML file, it will automatically use `Playwright` to convert it locally into a PDF to avoid exceeding Gemini token limits.
- It then uploads the local PDFs to Gemini using the `Files API`, and waits for the files to finish processing.

## Step 3: Input Extraction
- This step is also handled seamlessly by the `get_valuation_inputs.py` script.
- It passes the uploaded PDFs along with the extraction prompt (`prompt.txt`) to the Gemini model.
- The output will be saved as a structured JSON file (e.g., `<company_name>_valuation_inputs.json`) containing Revenues, EBIT, Interest Expense, Book Value of Equity, Book Value of Debt, Cash, Cross Holdings, Minority Interests, Shares Outstanding, Tax Rates, and details for Cost of Capital.

## Step 4: Populate the Excel Spreadsheet
- Use the `fill_excel.py` script provided within this skill directory.
- This script accepts flags (`--company`, `--inputs`, `--output`, `--price`, `--rf_rate`, `--erp`, `--ticker`) to cleanly inject the extracted JSON data into the `template.xlsx` file.
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
