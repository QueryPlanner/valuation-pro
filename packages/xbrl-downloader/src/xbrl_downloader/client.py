import logging
from typing import Optional

import requests

from xbrl_downloader.models import FilingSource

logger = logging.getLogger(__name__)


_INVALID_TRADITIONAL_XBRL_URL = "https://nsearchives.nseindia.com/corporate/xbrl/-"


class NSEClient:
    """Client for interacting with NSE India APIs to fetch XBRL filings."""

    def __init__(self) -> None:
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/114.0.0.0 Safari/537.36"
            ),
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.nseindia.com/",
            "cookie": (
                "AKA_A2=A; bm_mi=853E644EDFBF408217A41EA9864DF85E~YAAQFv7UF0x0FQ6eAQAAU4wTGh+uF4mWeIUonw5qnUS3uQoSUl"
                "GD6BNIC2VK4KF5s/WXhJbkM2xg//6Ea9RYU1uigG7DYe0blmtuONMlYfpk0vnoeda0lz5nkZZYkao5Jjw4mY8HcvAO4M6Pc5eIV"
                "krxMk9X+ffqJDOTCFMPk26lNpPU0Pk15AfhvzbN6/fsqWsoFlx/h51j8XhasTYozoENPt7QdxO91DVE1AfKNqlLoJI5cZI6vGHGUD"
                "FZ4tBKOVAWEmUV3XhGjSguQq2NKUdDiXmO/yR71iy6Bgs/Wi13TThTqkQOyQMm12nN9fE=~1; bm_sz=B31609EEDFB5A8B8491119"
                "153929A532~YAAQFv7UF050FQ6eAQAAU4wTGh+K+fIG3+I4Z12DQavS63shn/DawxF4SgfwXUbRhgZoe+gi8lrM4CRGGRrMJRgQ8Zbw"
                "pgInzRgZDqrcoIc0ysh6omcEN9m4r5wFMkz8Bq2s/2mr/Ssf8suYMpeuNzazj5iBJu5bvzXBzxOIozk0oVnn8qXJHEN0T+xQpHcmu"
                "Rn9Dq0sJjqPaptuluyolISsRKvQiLGBbUY4KpgNAnjptWfnFElPGiycpXLhqfBYVZHZN8YgBGYpbV2ofLx8sWrEA3VftAPVQIOQIx"
                "oBfflijkMfR0JNcvM45CQtTDgUj2FbXUDrXEr0GEOMj5XOsfV118q45FrLWmLVlAxMF7xL7vL5UmC/aE5WIDfeomHfGQdWA2pEXkr"
                "9X7DcFVOzrrJPm/4=~3622465~3163699; _abck=43461C3E7C1BEABBFABA441BE97A13E8~0~YAAQFv7UF1N0FQ6eAQAA4YwTG"
                "g/iPXnCASgF7VxcBYYipZEZnGHaA52OVxOrfzw1NQdRfcvp+43E1pM1IYLglqYVWWaNMLgqihuiVJA9pi6LSZ7UzG9pL0BgP8gqFo"
                "heQIuXXgkAz2J/snFQ2CiWEEfQJzxAjUyx43uXrGDiNx2Uy4jGdXZiofc+Fq3/Hh2CwS3lwv01S6n4j3iXY7gr9rcJWB06cyE4ovN"
                "6gOh2eoJ4RUJHkEE+Ggd1PtPFa9artV0dv1yjWwm54jnQm9LZsoSEp6sNNds72xKKGCmz85ebTraUaqeAa9Rc7Od3xGZKx3h2WXEx"
                "KHaztF1ClA+d9Bj2WiDBAOn36z0ePkyUgoBJj7Vw7ZQj8melf0q9X1gQahmIv4tZbp8VEXnr4FyAue80Co/PWJ21o36qzjB8RFWKY"
                "s20D+Mg+/yKZ7I0/74c+UrUsBHt1LCt1lyiqFB5EcIkX55JbxuRzXjBhFtsPsR5YgXlvm1riJTZeMYakv1mIZUTdPnZ1G0ExU+FuM"
                "qrkD5wAJULzlmpVD+dqevAmTA7kmIdqIJJi6ofDrrvcicvdrWYtsv6Dl18MQja+pcSCt8wKBT25+cfEvZXLWD1MBYEoj2hFACvYqb"
                "Bhj/G1fCd9FGwxpl0bInM614wTOxU9InM~-1~-1~-1~AAQAAAAF%2f%2f%2f%2f%2f32xolLmCfTjZlBWVMA25BPAKhbzksX%2fEA"
                "S%2fZWfgj6lRC8uL7MkLQRX+U79arBJe7jMT8E2Mu7mKnJufv62eZCO5BNAskZRUiQJm~-1; bm_sv=E28D0DFF08A6BFDBA5582"
                "EFF7A7B6D22~YAAQFv7UF091FQ6eAQAA85sTGh/OkpvhgcT09NVgLHblL5tcBPA3uaNqmTczom/n30VLnlIVL7EBvbJsI/fy3ONJN"
                "lN3Vi0f2qXjjv+gbSQs4N9xNpho9MzBA9WIG9vJI5Z7b+9KU2kz4dd8EvFumZlPTVWh52yeOrTaJW56ABEIzMf39H8ZQ4/RQ9AA+/"
                "/a5alz/pB0707SRSWqhzUc/Ez6OOISEzYSnaha75M+VnXERstxqck3uy1T4Xg+Ni5yuqQ=~1; ak_bmsc=002A06FEEBE44661017"
                "4CAEE994F56F4~000000000000000000000000000000~YAAQz/Q3FwzrfOOdAQAAEZwTGh9/gNRhpZlEsDc5c4wkZ/iTVaGVWJymD"
                "ykXfiISWg2cueEl794ztAEZlBRu/L2iHWLktKauUCORODt41q/V+RhUABkYJb59OaSDkNIPHd/nhF7zwKr5nK1nmcNNcL3MPOwwOo"
                "ab1UtpbKG5ORLs8OsqBAfkbgUq7hWiTJV+uPb/vKf9Kt2JVkGTM/r9CppyHcfreXvw1UfTf+6K5roW/D5vMJsiBHibzgV0Yq0Lggev"
                "0pv/quwJkPxb+UMj98RxlzKrkjcjCjBa3az/2TS4A7tX6+Wkl0UnoslPLBu1n0kvmby+X3wZCgqax/4Q+LPa5Qq7ixRWI6P7jFzQ8Z"
                "y6d+lwDWGvyYxBVCpu3nWeGXZ4eqb0zMaTD3HNme8ml3V0mW7y23pEnjxTQfjd09BUSdotciGKy4rSrN1BxYkrMBEOvNL49cRbOIVz"
                "uFCEZkV9wm5SxMzvz7nYy2HYddCgE/so4UG4G3wpeIfQx4bmxNKGjOi1NfKERWhKNiGJbIBL5qLRrSjCBHkyLAU="
            ),
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.base_url = "https://www.nseindia.com"

    def fetch_cookies(self) -> bool:
        """Fetch initial cookies required by NSE APIs."""
        logger.info("Fetching cookies from NSE... (Skipped because we have explicit cookies)")
        return True

    def get_integrated_filings(self, symbol: str) -> list[dict]:
        """Fetch newer integrated filing results from NSE API."""
        url = f"{self.base_url}/api/integrated-filing-results?symbol={symbol}"
        try:
            response = self.session.get(url, timeout=30)
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
            response = self.session.get(url, timeout=30)
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
                        "type": f.get("type", "") + " " + str(f.get("consolidated", "")),
                        "source": FilingSource.INTEGRATED,
                    }
                )

        logger.info("Fetching traditional filing data (Older format)...")
        for f in self.get_traditional_filings(symbol):
            url = f.get("xbrl")
            if url and url != _INVALID_TRADITIONAL_XBRL_URL:
                filings.append(
                    {
                        "date_str": f.get("toDate", ""),
                        "xbrl_url": url,
                        "type": "Financial Results " + str(f.get("consolidated", "")),
                        "financial_year": f.get("financialYear", ""),
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
