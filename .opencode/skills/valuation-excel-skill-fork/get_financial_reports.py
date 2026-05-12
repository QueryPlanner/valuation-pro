import argparse
import json
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()


def get_financial_reports_links(company_name: str):
    """
    Uses Gemini API to find downloadable PDF links for a company's financial reports.
    """
    # Initialize the client. Assumes GEMINI_API_KEY environment variable is set.
    try:
        client = genai.Client()
    except Exception as e:
        print(f"Error initializing Google GenAI client. Make sure GEMINI_API_KEY is set: {e}")
        return

    import datetime

    current_year = datetime.datetime.now().year

    # User specified "gemini 3 flash preview"
    model_name = "gemini-3-flash-preview"  # Update this if the exact API model string differs

    prompt = f"""
Can you get me downloadable PDF links to the latest annual report and the last two quarterly reports (Financial results, not press releases or presentation reports) for the company: {company_name}.

CRITICAL INSTRUCTIONS:
1. You MUST use the google_search tool to find actual, working PDF or SEC EDGAR HTML links.
2. The current year is {current_year}. Do NOT hallucinate future quarters or years that have not occurred yet.
3. Only return verified, working URLs.

Please provide the output as a valid JSON object with the following structure:
{{
  "company_name": "{company_name}",
  "annual_report": {{
    "year": "YYYY-YYYY",
    "pdf_link": "https://..."
  }},
  "quarterly_reports": [
    {{
      "quarter": "Qx YYYY-YYYY",
      "pdf_link": "https://..."
    }},
    {{
      "quarter": "Qx YYYY-YYYY",
      "pdf_link": "https://..."
    }}
  ]
}}
Only return the JSON object and no other text.
"""

    print(f"Querying Gemini API for {company_name} reports...")

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                response_mime_type="application/json",
                tools=[{"google_search": {}}],
            ),
        )

        # Parse the JSON response
        try:
            result = json.loads(response.text)
            print("\nSuccessfully retrieved links:")
            print(json.dumps(result, indent=2))

            # Save to a file
            output_file = f"{company_name.lower().replace(' ', '_')}_reports.json"
            with open(output_file, "w") as f:
                json.dump(result, f, indent=2)
            print(f"\nSaved results to {output_file}")

        except json.JSONDecodeError:
            print("Failed to parse the response as JSON. Raw response:")
            print(response.text)

    except Exception as e:
        print(f"Error calling Gemini API: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Get company financial report links using Gemini API")
    parser.add_argument("--company", type=str, default="ONGC", help="Target company name (default: ONGC)")
    args = parser.parse_args()

    # Check if API key is set
    if not os.environ.get("GEMINI_API_KEY"):
        print("Warning: GEMINI_API_KEY environment variable is not set.")
        print("You can set it by running: export GEMINI_API_KEY='your_api_key'")
        # We'll continue anyway, the client initialization might handle it differently

    get_financial_reports_links(args.company)
