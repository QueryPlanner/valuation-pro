import requests

headers = {"User-Agent": "ValuationPro/1.0 (valuation@example.com)"}

# search CIK for Wipro
response = requests.get("https://www.sec.gov/files/company_tickers.json", headers=headers)
data = response.json()
cik = None
for key, value in data.items():
    if value['ticker'] == 'WIT':
        cik = str(value['cik_str']).zfill(10)
        break

print(f"Wipro CIK: {cik}")

if cik:
    # Get latest filings
    subs_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    subs_response = requests.get(subs_url, headers=headers)
    subs_data = subs_response.json()
    
    recent = subs_data['filings']['recent']
    
    # find latest 20-F
    print("Latest 20-F:")
    for form, date, acc_no, doc in zip(recent['form'], recent['filingDate'], recent['accessionNumber'], recent['primaryDocument']):
        if form == '20-F':
            acc_no_no_dash = acc_no.replace("-", "")
            url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_no_no_dash}/{doc}"
            print(f"Found 20-F filed on {date}: {url}")
            break
            
    print("Latest 6-K:")
    count = 0
    for form, date, acc_no, doc in zip(recent['form'], recent['filingDate'], recent['accessionNumber'], recent['primaryDocument']):
        if form == '6-K':
            acc_no_no_dash = acc_no.replace("-", "")
            url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_no_no_dash}/{doc}"
            print(f"Found 6-K filed on {date}: {url}")
            count += 1
            if count >= 3:
                break
