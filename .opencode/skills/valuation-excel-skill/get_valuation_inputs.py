import os
import json
import argparse
import time
import httpx
import io
import pathlib
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

from playwright.sync_api import sync_playwright

def download_and_upload_pdf(client, url, display_name):
    file_ext = display_name.split('.')[-1]
    
    if url.startswith("http"):
        print(f"Downloading {display_name} from {url}...")
        
        # We use follow_redirects and a longer timeout for large PDFs
        # Add a user-agent to avoid getting blocked by SEC servers
        headers = {
            "User-Agent": os.environ.get("SEC_USER_AGENT", "FinancialBot/1.0 (contact@example.com)")
        }
        
        if file_ext in ['htm', 'html']:
            response = httpx.get(url, headers=headers, follow_redirects=True, timeout=120.0)
            response.raise_for_status()
            htm_path = pathlib.Path(display_name)
            htm_path.write_bytes(response.content)
            
            pdf_display_name = display_name.rsplit('.', 1)[0] + '.pdf'
            pdf_path = pathlib.Path(pdf_display_name)
            print(f"Converting local HTML to PDF using Playwright...")
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                page.goto(htm_path.absolute().as_uri(), wait_until='networkidle', timeout=120000)
                page.pdf(path=str(pdf_path))
                browser.close()
            display_name = pdf_display_name
            file_path = pdf_path
            print(f"Saved to {file_path.absolute()}")
        else:
            response = httpx.get(url, headers=headers, follow_redirects=True, timeout=120.0)
            response.raise_for_status()
            file_path = pathlib.Path(display_name)
            file_path.write_bytes(response.content)
            print(f"Saved to {file_path.absolute()}")
    else:
        print(f"Using local file {url} for {display_name}...")
        file_path = pathlib.Path(url)
        if not file_path.exists():
            raise FileNotFoundError(f"Local file not found: {url}")
            
    mime_type = 'text/plain' if display_name.endswith('.txt') else ('text/html' if display_name.endswith('.htm') or display_name.endswith('.html') else 'application/pdf')
    print(f"Uploading {display_name} to Gemini as {mime_type}...")
    uploaded_file = client.files.upload(
        file=file_path,
        config={'mime_type': mime_type, 'display_name': display_name}
    )
    
    print(f"Waiting for {display_name} to be processed...")
    while True:
        file_info = client.files.get(name=uploaded_file.name)
        if file_info.state == 'PROCESSING':
            print(f"File {display_name} is processing, retrying in 5 seconds...")
            time.sleep(5)
        elif file_info.state == 'ACTIVE':
            print(f"File {display_name} is ready.")
            break
        elif file_info.state == 'FAILED':
            raise Exception(f"File processing failed for {display_name}")
        else:
            print(f"Unknown state {file_info.state} for {display_name}")
            time.sleep(5)
            
    return file_info

def generate_valuation_inputs(company_name: str, reports_json_path: str, prompt_file: str):
    try:
        client = genai.Client()
    except Exception as e:
        print(f"Error initializing Google GenAI client: {e}")
        return

    with open(reports_json_path, 'r') as f:
        reports_data = json.load(f)
        
    with open(prompt_file, 'r') as f:
        prompt_text = f.read()

    uploaded_files = []
    
    # Process Annual Report
    if "annual_report" in reports_data and reports_data["annual_report"].get("pdf_link"):
        ar = reports_data["annual_report"]
        try:
            ext = ".htm" if ar["pdf_link"].endswith(".htm") or ar["pdf_link"].endswith(".html") else ".pdf"
            ar_file = download_and_upload_pdf(client, ar["pdf_link"], f"{company_name}_AR_{ar.get('year', 'latest')}{ext}")
            uploaded_files.append(ar_file)
        except Exception as e:
            print(f"Error processing annual report: {e}")

    # Process Quarterly Reports
    if "quarterly_reports" in reports_data:
        for i, qr in enumerate(reports_data["quarterly_reports"]):
            if qr.get("pdf_link"):
                try:
                    ext = ".htm" if qr["pdf_link"].endswith(".htm") or qr["pdf_link"].endswith(".html") else ".pdf"
                    qr_file = download_and_upload_pdf(client, qr["pdf_link"], f"{company_name}_{qr.get('quarter', f'Q{i+1}')}{ext}")
                    uploaded_files.append(qr_file)
                except Exception as e:
                    print(f"Error processing quarterly report: {e}")

    if not uploaded_files:
        print("No files were successfully uploaded. Exiting.")
        return

    print(f"Sending request to Gemini for {company_name} valuation inputs...")
    
    contents = []
    for f in uploaded_files:
        contents.append(f)
    contents.append(prompt_text)

    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=0.0, # low temp for extraction
                response_mime_type="application/json",
            )
        )
        
        output_file = f"{company_name.lower().replace(' ', '_')}_valuation_inputs.json"
        
        try:
            result = json.loads(response.text)
            print("\nSuccessfully generated valuation inputs!")
            with open(output_file, "w") as f:
                json.dump(result, f, indent=2)
            print(f"Saved results to {output_file}")
            
        except json.JSONDecodeError:
            print("Failed to parse the response as JSON. Raw response:")
            print(response.text)
            with open(f"{company_name.lower().replace(' ', '_')}_raw_response.txt", "w") as f:
                f.write(response.text)
            
    except Exception as e:
        print(f"Error calling Gemini API: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate valuation inputs using downloaded financial reports")
    parser.add_argument("--company", type=str, required=True, help="Target company name (e.g. DRREDDY)")
    parser.add_argument("--reports", type=str, required=True, help="Path to the JSON file with report links")
    parser.add_argument("--prompt", type=str, default="prompt.txt", help="Path to prompt.txt file")
    
    args = parser.parse_args()
    
    if not os.environ.get("GEMINI_API_KEY"):
        print("Warning: GEMINI_API_KEY environment variable is not set.")
        
    generate_valuation_inputs(args.company, args.reports, args.prompt)
