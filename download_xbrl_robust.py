#!/usr/bin/env python3
"""
Robust XBRL Financial Reports Downloader from NSE India

Features:
- Automatic cookie caching and management
- Support for both Quarterly and Annual reports
- Easy cookie setup (one-time or automatic)
- Consolidated and Non-Consolidated reports

Usage:
    # First time setup (interactive)
    python3 download_xbrl_robust.py BPCL --setup

    # Then download reports (cookies cached for 2 hours)
    python3 download_xbrl_robust.py BPCL
    python3 download_xbrl_robust.py BPCL --annual 2
    python3 download_xbrl_robust.py BPCL --all
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import requests


class CookieManager:
    """Manages cookies for NSE India with caching and easy setup"""

    COOKIE_CACHE_FILE = Path.home() / ".nse_xbrl_cookies.json"
    COOKIE_EXPIRY_HOURS = 2

    def __init__(self):
        self.cookies = {}

    def get_cookies(self) -> Dict[str, str]:
        """Get valid cookies from cache or prompt for new ones"""
        # Try to load from cache
        cached = self._load_from_cache()
        if cached:
            return cached

        # No valid cache - prompt user
        print("\n" + "=" * 70)
        print("Cookie Setup Required")
        print("=" * 70)
        print("\nNSE India requires browser cookies for API access.")
        print("Cookies are cached for 2 hours after setup.\n")
        print("How to get cookies from your browser:")
        print("-" * 70)
        print("1. Open Chrome/Brave/Firefox")
        print("2. Go to: https://www.nseindia.com")
        print("3. Open Developer Tools (F12 or Cmd+Option+I)")
        print("4. Go to 'Application' tab → 'Cookies' → 'https://www.nseindia.com'")
        print("5. Find and copy these cookies:")
        print("   - nsit")
        print("   - AKA_A2")
        print("\nOr run this command in browser console (F12 → Console):")
        print("-" * 70)
        print("  document.cookie.split('; ').filter(c => c.startsWith('nsit=') || c.startsWith('AKA_A2=')).join('; ')")
        print("-" * 70)

        # Interactive input or use env variable
        print("\nPaste cookies (format: 'nsit=VALUE; AKA_A2=VALUE'):")

        # Check if running interactively
        if sys.stdin.isatty():
            try:
                cookie_input = input("> ").strip()
            except KeyboardInterrupt:
                print("\n\n✗ Cancelled by user")
                sys.exit(1)
        else:
            # Non-interactive mode - use env variable
            cookie_input = os.environ.get("NSE_COOKIES", "")
            if not cookie_input:
                print("  (No cookies provided - non-interactive mode)")

        if cookie_input:
            cookies = self._parse_cookie_string(cookie_input)
        else:
            # No cookies provided
            print("\n✗ No cookies provided. Please run with --setup to configure cookies.")
            print("  Or set NSE_COOKIES environment variable.")
            sys.exit(1)

        if cookies:
            self._save_to_cache(cookies)
            print("\n✓ Cookies saved to cache")
            return cookies
        else:
            raise ValueError("Invalid cookie format")

    def _parse_cookie_string(self, cookie_str: str) -> Optional[Dict[str, str]]:
        """Parse cookie string into dictionary"""
        cookies = {}
        for cookie in cookie_str.split(";"):
            cookie = cookie.strip()
            if "=" in cookie:
                name, value = cookie.split("=", 1)
                cookies[name.strip()] = value.strip()
        return cookies if cookies else None

    def _load_from_cache(self, ignore_expiry: bool = False) -> Optional[Dict[str, str]]:
        """Load cookies from cache file"""
        if not self.COOKIE_CACHE_FILE.exists():
            return None

        try:
            with open(self.COOKIE_CACHE_FILE, "r") as f:
                data = json.load(f)

            if not ignore_expiry:
                timestamp = datetime.fromisoformat(data.get("timestamp", "2000-01-01"))
                if datetime.now() - timestamp > timedelta(hours=self.COOKIE_EXPIRY_HOURS):
                    print("⚠ Cached cookies expired")
                    return None

            print("✓ Using cached cookies")
            return data.get("cookies", {})
        except Exception as e:
            print(f"Warning: Could not load cookie cache: {e}")
            return None

    def _save_to_cache(self, cookies: Dict[str, str]):
        """Save cookies to cache file"""
        try:
            data = {"timestamp": datetime.now().isoformat(), "cookies": cookies}
            with open(self.COOKIE_CACHE_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save cookie cache: {e}")

    def clear_cache(self):
        """Clear cached cookies"""
        if self.COOKIE_CACHE_FILE.exists():
            self.COOKIE_CACHE_FILE.unlink()
            print("✓ Cookie cache cleared")


class NSEXBRLDownloader:
    """Download XBRL financial reports from NSE India"""

    API_URL = "https://www.nseindia.com/api/corporates-financial-results"

    def __init__(self, cookies: Dict[str, str]):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X_10_15_7) AppleWebKit/537.36",
                "Accept": "application/json, text/plain, */*",
                "Referer": "https://www.nseindia.com/",
            }
        )
        self.session.cookies.update(cookies)

    def get_financial_results(self, symbol: str, period: str = "Quarterly") -> List[dict]:
        """Fetch financial results from NSE API"""
        params = {"index": "equities", "symbol": symbol.upper(), "period": period}

        try:
            response = self.session.get(self.API_URL, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"✗ Error fetching {period} results: {e}")
            if "403" in str(e):
                print("  → Cookies may be expired. Try: --setup")
            return []

    def download_xbrl(self, url: str, output_path: Path) -> bool:
        """Download a single XBRL file"""
        try:
            with self.session.get(url, timeout=60, stream=True) as response:
                response.raise_for_status()
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
            return True
        except Exception as e:
            print(f"  ✗ Download failed: {e}")
            return False

    def download_reports(
        self,
        symbol: str,
        output_dir: str = "xbrl_downloads",
        quarterly: int = 0,
        annual: int = 0,
        consolidated_only: Optional[bool] = None,
    ) -> List[dict]:
        """Download XBRL reports for a company"""
        downloaded = []

        # Quarterly reports
        if quarterly > 0:
            print(f"\n{'=' * 70}")
            print(f"Fetching QUARTERLY Results for {symbol.upper()}")
            print(f"{'=' * 70}\n")

            results = self.get_financial_results(symbol, period="Quarterly")
            if results:
                print(f"✓ Found {len(results)} quarterly results")
                downloaded.extend(
                    self._download_reports_list(results, output_dir, symbol, "Quarterly", quarterly, consolidated_only)
                )

        # Annual reports
        if annual > 0:
            print(f"\n{'=' * 70}")
            print(f"Fetching ANNUAL Results for {symbol.upper()}")
            print(f"{'=' * 70}\n")

            results = self.get_financial_results(symbol, period="Annual")
            if results:
                print(f"✓ Found {len(results)} annual results")
                downloaded.extend(
                    self._download_reports_list(results, output_dir, symbol, "Annual", annual, consolidated_only)
                )

        # Save metadata
        if downloaded:
            output_path = Path(output_dir) / symbol.upper()
            metadata_path = output_path / "metadata.json"
            metadata_path.write_text(json.dumps(downloaded, indent=2))
            print(f"\n✓ Metadata saved to: {metadata_path}")

        return downloaded

    def _download_reports_list(
        self,
        results: List[dict],
        output_dir: str,
        symbol: str,
        period_type: str,
        limit: int,
        consolidated_only: Optional[bool],
    ) -> List[dict]:
        """Download from a list of results"""
        # Filter for valid XBRL URLs
        xbrl_files = []
        for item in results:
            xbrl_url = item.get("xbrl")

            if not xbrl_url or xbrl_url.endswith("/-"):
                continue

            is_consolidated = item.get("consolidated") == "Consolidated"
            if consolidated_only is not None:
                if consolidated_only and not is_consolidated:
                    continue
                if not consolidated_only and is_consolidated:
                    continue

            xbrl_files.append(
                {
                    "symbol": item.get("symbol"),
                    "company": item.get("companyName"),
                    "period": item.get("relatingTo"),
                    "period_type": period_type,
                    "financial_year": item.get("financialYear"),
                    "filing_date": item.get("filingDate"),
                    "consolidated": item.get("consolidated"),
                    "audited": item.get("audited"),
                    "xbrl_url": xbrl_url,
                    "seq_number": item.get("seqNumber"),
                }
            )

        print(f"  → Found {len(xbrl_files)} results with XBRL files\n")

        if not xbrl_files:
            return []

        output_path = Path(output_dir) / symbol.upper()
        downloaded = []
        files_to_download = xbrl_files[: limit * 2] if consolidated_only is None else xbrl_files[:limit]

        for i, xbrl in enumerate(files_to_download, 1):
            period_clean = xbrl["period"].replace(" ", "_").replace("-", "")
            year_clean = xbrl["financial_year"].replace(" ", "_").replace(":", "")
            cons_suffix = "_Consolidated" if xbrl["consolidated"] == "Consolidated" else "_NonConsolidated"

            filename = f"{xbrl['symbol']}_{period_type}_{period_clean}_{year_clean}{cons_suffix}.xml"
            file_path = output_path / filename

            print(f"[{i}/{len(files_to_download)}] {xbrl['period']} - {xbrl['financial_year']}")
            print(f"  Type: {xbrl['consolidated']}")
            print(f"  Filed: {xbrl['filing_date']}")

            if self.download_xbrl(xbrl["xbrl_url"], file_path):
                print(f"  ✓ Downloaded: {filename}")
                downloaded.append({"file": str(file_path), "url": xbrl["xbrl_url"], **xbrl})
            print()

        return downloaded


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Download XBRL financial reports from NSE India",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Setup cookies (first time)
  python3 download_xbrl_robust.py BPCL --setup

  # Download last 4 quarterly reports (default)
  python3 download_xbrl_robust.py BPCL

  # Download last 2 annual reports
  python3 download_xbrl_robust.py BPCL --annual 2

  # Download both quarterly and annual
  python3 download_xbrl_robust.py BPCL --quarters 4 --annual 2

  # Download all available
  python3 download_xbrl_robust.py BPCL --all

  # Only consolidated reports
  python3 download_xbrl_robust.py BPCL --consolidated

Cookie Setup:
  Cookies are cached for 2 hours. After that, you'll be prompted to enter new cookies.
  Use --setup to force cookie setup even if cached cookies exist.
""",
    )

    parser.add_argument("symbol", help="Stock symbol (e.g., BPCL, RELIANCE, TCS)")
    parser.add_argument(
        "--quarters", type=int, help="Number of quarterly reports (default: 4 if no annual reports requested)"
    )
    parser.add_argument("--annual", type=int, default=0, help="Number of annual reports (default: 0)")
    parser.add_argument("--all", action="store_true", help="Download all available reports")
    parser.add_argument("--output", default="xbrl_downloads", help="Output directory")
    parser.add_argument("--consolidated", action="store_true", help="Download only consolidated reports")
    parser.add_argument("--non-consolidated", action="store_true", help="Download only non-consolidated reports")
    parser.add_argument("--setup", action="store_true", help="Force cookie setup")
    parser.add_argument("--clear-cache", action="store_true", help="Clear cached cookies")

    args = parser.parse_args()

    # Clear cache if requested
    if args.clear_cache:
        cookie_manager = CookieManager()
        cookie_manager.clear_cache()
        print("✓ Cookie cache cleared\n")

    # Determine what to download
    quarterly = args.quarters if args.quarters is not None else (4 if args.annual == 0 else 0)
    annual = args.annual

    if args.all:
        quarterly = 100
        annual = 100

    # Determine consolidated filter
    consolidated_only = None
    if args.consolidated:
        consolidated_only = True
    elif args.non_consolidated:
        consolidated_only = False

    # Get cookies
    cookie_manager = CookieManager()

    # Force setup if requested or no cache
    if args.setup or not cookie_manager._load_from_cache():
        cookies = cookie_manager.get_cookies()
    else:
        cookies = cookie_manager._load_from_cache()

    # Initialize downloader
    downloader = NSEXBRLDownloader(cookies=cookies)

    # Download reports
    downloaded = downloader.download_reports(
        symbol=args.symbol,
        output_dir=args.output,
        quarterly=quarterly,
        annual=annual,
        consolidated_only=consolidated_only,
    )

    # Summary
    print("\n" + "=" * 70)
    print("Download Summary")
    print("=" * 70)
    print(f"Total files downloaded: {len(downloaded)}")
    if downloaded:
        print(f"Files saved to: {args.output}/{args.symbol.upper()}/")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
