# Robust XBRL Financial Reports Downloader

Automatically download XBRL financial reports from NSE India with support for both **quarterly** and **annual** reports.

## Features

✅ **Automatic cookie management** - Cookies cached for 2 hours  
✅ **Quarterly reports** - Download last N quarterly filings  
✅ **Annual reports** - Download last N annual filings  
✅ **Consolidated & Non-Consolidated** - Get both versions  
✅ **Easy cookie setup** - One-time setup with clear instructions  
✅ **Multiple companies** - Works for any NSE-listed company  

## Installation

```bash
# Install dependencies
pip3 install requests

# Make executable (optional)
chmod +x download_xbrl_robust.py
```

## Quick Start

### 1. One-Time Cookie Setup

NSE India requires browser cookies for API access. You have **three options**:

#### Option A: Interactive Setup (Recommended)
```bash
python3 download_xbrl_robust.py BPCL --setup
```
Follow the on-screen instructions to paste cookies from your browser.

#### Option B: Environment Variable
```bash
export NSE_COOKIES="nsit=YOUR_VALUE; AKA_A2=YOUR_VALUE"
python3 download_xbrl_robust.py BPCL
```

#### Option C: Use Default Cookies
Just run the script - it will use example cookies (may not always work):
```bash
python3 download_xbrl_robust.py BPCL
```

### 2. Get Cookies from Browser

**Step-by-step:**

1. Open Chrome/Brave/Firefox
2. Go to: `https://www.nseindia.com`
3. Open Developer Tools (`F12` or `Cmd+Option+I`)
4. Go to **Application** tab → **Cookies** → `https://www.nseindia.com`
5. Find and copy these cookies:
   - `nsit`
   - `AKA_A2`

**Quick method - Browser Console:**

Press `F12` → **Console** tab → Paste this command:
```javascript
document.cookie.split('; ').filter(c => c.startsWith('nsit=') || c.startsWith('AKA_A2=')).join('; ')
```

Copy the output and paste it when prompted.

## Usage Examples

### Download Quarterly Reports

```bash
# Download last 4 quarterly reports (default)
python3 download_xbrl_robust.py BPCL

# Download last 2 quarterly reports
python3 download_xbrl_robust.py BPCL --quarters 2

# Download all available quarterly reports
python3 download_xbrl_robust.py BPCL --all
```

### Download Annual Reports

```bash
# Download last 2 annual reports
python3 download_xbrl_robust.py BPCL --annual 2

# Download last annual report
python3 download_xbrl_robust.py BPCL --annual 1
```

### Download Both Quarterly and Annual

```bash
# Download last 4 quarterly + last 2 annual
python3 download_xbrl_robust.py BPCL --quarters 4 --annual 2

# Download everything available
python3 download_xbrl_robust.py BPCL --all
```

### Filter by Type

```bash
# Download only consolidated reports
python3 download_xbrl_robust.py BPCL --consolidated

# Download only non-consolidated (standalone) reports
python3 download_xbrl_robust.py BPCL --non-consolidated
```

### Custom Output Directory

```bash
python3 download_xbrl_robust.py BPCL --output ./my_reports
```

### Multiple Companies

```bash
# Download for multiple companies
for company in BPCL RELIANCE TCS INFY HDFC; do
    python3 download_xbrl_robust.py $company --quarters 4 --annual 1
done
```

## Command Reference

| Argument | Description | Default |
|----------|-------------|---------|
| `SYMBOL` | Stock symbol (required) | - |
| `--quarters N` | Number of quarterly reports | 4 |
| `--annual N` | Number of annual reports | 0 |
| `--all` | Download all available | - |
| `--output DIR` | Output directory | `xbrl_downloads` |
| `--consolidated` | Only consolidated reports | - |
| `--non-consolidated` | Only standalone reports | - |
| `--setup` | Force cookie setup | - |
| `--clear-cache` | Clear cached cookies | - |

## Output Structure

```
xbrl_downloads/
└── BPCL/
    ├── BPCL_Quarterly_Third_Quarter_01-Apr-2024_To_31-Mar-2025_Consolidated.xml
    ├── BPCL_Quarterly_Third_Quarter_01-Apr-2024_To_31-Mar-2025_NonConsolidated.xml
    ├── BPCL_Quarterly_Second_Quarter_01-Apr-2024_To_31-Mar-2025_Consolidated.xml
    ├── BPCL_Quarterly_Second_Quarter_01-Apr-2024_To_31-Mar-2025_NonConsolidated.xml
    ├── BPCL_Annual_Annual_01-Apr-2023_To_31-Mar-2024_Consolidated.xml
    ├── BPCL_Annual_Annual_01-Apr-2023_To_31-Mar-2024_NonConsolidated.xml
    └── metadata.json
```

### File Naming Convention

```
{SYMBOL}_{PERIOD_TYPE}_{PERIOD}_{FINANCIAL_YEAR}_{CONSOLIDATION_STATUS}.xml

Example:
BPCL_Quarterly_Third_Quarter_01-Apr-2024_To_31-Mar-2025_Consolidated.xml
│     │          │              │                          │
│     │          │              │                          └─ Consolidated/NonConsolidated
│     │          │              └─ Financial Year
│     │          └─ Quarter/Annual
│     └─ Quarterly/Annual
└─ Company Symbol
```

## What's Inside an XBRL File?

Each XBRL file contains complete financial statements:

- **Balance Sheet** - Assets, Liabilities, Equity
- **Profit & Loss Statement** - Revenue, Expenses, Profit
- **Cash Flow Statement** - Operating, Investing, Financing activities
- **Notes to Accounts** - Detailed breakdowns and disclosures
- **Segment Reporting** - Business segment performance
- **Key Metrics** - EPS, Book Value, etc.

### Sample Data (BPCL Q3 FY2025)

```xml
<in-bse-fin:RevenueFromOperations>1275205000000.00</in-bse-fin:RevenueFromOperations>
<in-bse-fin:ProfitBeforeTax>61761700000.00</in-bse-fin:ProfitBeforeTax>
<in-bse-fin:TotalAssets>1867239000000.00</in-bse-fin:TotalAssets>
```

**Interpreted as:**
- Revenue from Operations: ₹1,27,520 Crores
- Profit Before Tax: ₹61,762 Crores
- Total Assets: ₹1,86,724 Crores

## Cookie Management

### Automatic Caching

- Cookies are **automatically cached** for 2 hours
- Cache location: `~/.nse_xbrl_cookies.json`
- After 2 hours, you'll be prompted to enter new cookies

### Clear Cache

```bash
python3 download_xbrl_robust.py --clear-cache
```

### Force Setup

```bash
python3 download_xbrl_robust.py BPCL --setup
```

## Troubleshooting

### Issue: "403 Forbidden" or "Cookies may be expired"

**Solution:** Cookies have expired. Get fresh cookies:
```bash
python3 download_xbrl_robust.py BPCL --setup
```

### Issue: "No XBRL files found"

**Possible reasons:**
1. Company symbol is incorrect - verify on NSE website
2. Company hasn't filed XBRL reports recently
3. Try with `--all` flag to see all available reports

### Issue: Downloaded files are empty

**Solution:** The XBRL URL might be invalid. Check the API response:
```bash
# Check what's available
curl 'https://www.nseindia.com/api/corporates-financial-results?index=equities&symbol=BPCL&period=Quarterly' \
  -H 'cookie: nsit=YOUR_VALUE; AKA_A2=VALUE' | jq '.[] | {period, xbrl}'
```

## API Details

### Endpoint
```
GET https://www.nseindia.com/api/corporates-financial-results
```

### Parameters
- `index=equities` (NOT "equity")
- `symbol=BPCL`
- `period=Quarterly` or `period=Annual`

### Authentication
Requires cookies:
- `nsit` - Session token
- `AKA_A2` - Akamai bot detection cookie

## Workflow for Production Use

### Option 1: Scheduled Downloads

```bash
#!/bin/bash
# download_monthly.sh

COMPANIES="BPCL RELIANCE TCS INFY"

for company in $COMPANIES; do
    echo "Downloading $company..."
    python3 download_xbrl_robust.py $company --quarters 4 --annual 1
done

echo "Done! Reports saved to xbrl_downloads/"
```

Run monthly via cron:
```bash
# Every month on 15th at 9 AM
0 9 15 * * /path/to/download_monthly.sh
```

### Option 2: Python Integration

```python
from download_xbrl_robust import CookieManager, NSEXBRLDownloader

# Setup cookies
cookie_manager = CookieManager()
cookies = cookie_manager.get_cookies()

# Download reports
downloader = NSEXBRLDownloader(cookies=cookies)
downloaded = downloader.download_reports(
    symbol='BPCL',
    output_dir='financial_data',
    quarterly=4,
    annual=2
)

print(f"Downloaded {len(downloaded)} XBRL files")
```

## Advanced Usage

### Parse XBRL Files

```python
import xml.etree.ElementTree as ET

def extract_revenue(xbrl_file):
    """Extract revenue from XBRL file"""
    tree = ET.parse(xbrl_file)
    root = tree.getroot()
    
    # XBRL uses namespaces
    ns = {'in-bse-fin': 'http://www.bseindia.com/xbrl/fin/2020-03-31/in-bse-fin'}
    
    for elem in root.findall('.//in-bse-fin:RevenueFromOperations', ns):
        return float(elem.text)
    
    return None

# Usage
revenue = extract_revenue('xbrl_downloads/BPCL/BPCL_Quarterly_Third_Quarter_...xml')
print(f"Revenue: ₹{revenue/10000000:.2f} Crores")
```

### Convert to CSV/Excel

Use NSE's XBRL converter:
```
http://ec2-3-221-41-38.compute-1.amazonaws.com
```

Upload XBRL file → Download as Excel

## Example Session

```
$ python3 download_xbrl_robust.py BPCL --quarters 2 --annual 1

======================================================================
Cookie Setup Required
======================================================================

NSE India requires browser cookies for API access.
Cookies are cached for 2 hours after setup.

How to get cookies from your browser:
----------------------------------------------------------------------
[... instructions ...]
----------------------------------------------------------------------

Paste cookies (format: 'nsit=VALUE; AKA_A2=VALUE'):
> nsit=ABC123...; AKA_A2=A

✓ Cookies saved to cache

======================================================================
Fetching QUARTERLY Results for BPCL
======================================================================

✓ Found 109 quarterly results
  → Found 49 results with XBRL files

[1/4] Third Quarter - 01-Apr-2024 To 31-Mar-2025
  Type: Consolidated
  Filed: 23-Jan-2025 11:27
  ✓ Downloaded: BPCL_Quarterly_Third_Quarter_...xml

[2/4] Third Quarter - 01-Apr-2024 To 31-Mar-2025
  Type: Non-Consolidated
  Filed: 23-Jan-2025 11:25
  ✓ Downloaded: BPCL_Quarterly_Third_Quarter_...xml

[... more files ...]

======================================================================
Fetching ANNUAL Results for BPCL
======================================================================

✓ Found 39 annual results
  → Found 13 results with XBRL files

[1/2] Annual - 01-Apr-2023 To 31-Mar-2024
  Type: Consolidated
  Filed: 10-May-2024 12:37
  ✓ Downloaded: BPCL_Annual_Annual_...xml

[... more files ...]

======================================================================
Download Summary
======================================================================
Total files downloaded: 6
Files saved to: xbrl_downloads/BPCL/
======================================================================
```

## Files Created

| File | Purpose |
|------|---------|
| `download_xbrl_robust.py` | Main download script |
| `~/.nse_xbrl_cookies.json` | Cookie cache (auto-created) |
| `xbrl_downloads/SYMBOL/` | Downloaded XBRL files |
| `xbrl_downloads/SYMBOL/metadata.json` | Download metadata |

## Summary

✅ **Fully automated** XBRL downloading from NSE India  
✅ **Quarterly and Annual** reports supported  
✅ **Cookie caching** minimizes manual intervention  
✅ **Works for any** NSE-listed company  
✅ **Production-ready** for scheduled downloads  

## Support

For issues or questions:
1. Try `--setup` to refresh cookies
2. Verify company symbol on NSE website
3. Check if company has filed XBRL reports

---

**Last Updated:** May 2026  
**NSE API Version:** v3.0.12  
**XBRL Standard:** Ind-AS
