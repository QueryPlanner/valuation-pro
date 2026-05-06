import logging
from typing import Optional

import requests

from xbrl_downloader.models import FilingSource

logger = logging.getLogger(__name__)


class NSEClient:
    """Client for interacting with NSE India APIs to fetch XBRL filings."""

    def __init__(self) -> None:
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/114.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.nseindia.com/",
            "X-Requested-With": "XMLHttpRequest",
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.base_url = "https://www.nseindia.com"

    def fetch_cookies(self) -> bool:
        """Fetch initial cookies required by NSE APIs."""
        logger.info("Fetching cookies from NSE...")
        try:
            response = self.session.get(self.base_url, timeout=10)
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            logger.error(f"Error fetching cookies: {e}")
            return False

    def get_integrated_filings(self, symbol: str) -> list[dict]:
        """Fetch newer integrated filing results from NSE API."""
        url = f"{self.base_url}/api/integrated-filing-results?symbol={symbol}"
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except requests.RequestException as e:
            logger.error(f"Error fetching integrated filings: {e}")
            return []

    def get_traditional_filings(self, symbol: str) -> list[dict]:
        """Fetch older traditional corporate financial results from NSE API."""
        url = f"{self.base_url}/api/corporates-financial-results?index=equities&symbol={symbol}&period=24Months"
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching traditional filings: {e}")
            return []

    def get_all_filings_metadata(self, symbol: str) -> list[dict]:
        """Fetch and normalize all filings metadata."""
        if not self.fetch_cookies():
            logger.warning("Could not establish NSE session. Continuing anyway, but requests may fail.")

        filings = []

        logger.info("Fetching integrated filing data (Newer format)...")
        for f in self.get_integrated_filings(symbol):
            if f.get("xbrl"):
                filings.append(
                    {
                        "date_str": f.get("qe_Date", ""),
                        "xbrl_url": f.get("xbrl"),
                        "type": f.get("type", ""),
                        "consolidated": f.get("consolidated", ""),
                        "source": FilingSource.INTEGRATED,
                    }
                )

        logger.info("Fetching traditional filing data (Older format)...")
        for f in self.get_traditional_filings(symbol):
            url = f.get("xbrl")
            if url and url != "https://nsearchives.nseindia.com/corporate/xbrl/-":
                filings.append(
                    {
                        "date_str": f.get("toDate", ""),
                        "xbrl_url": url,
                        "type": "Financial Results " + str(f.get("consolidated", "")),
                        "source": FilingSource.TRADITIONAL,
                    }
                )

        return filings

    def download_file(self, url: str) -> Optional[bytes]:
        """Download file content from a given URL."""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.content
        except requests.RequestException as e:
            logger.error(f"Error downloading {url}: {e}")
            return None
