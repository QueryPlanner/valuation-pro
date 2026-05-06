import logging
from datetime import datetime
from typing import Optional

from xbrl_downloader.models import FilingMetadata, TargetFilings

logger = logging.getLogger(__name__)


class FilingSelector:
    """Logic to select the appropriate filings for valuation."""

    @staticmethod
    def parse_date(date_str: str) -> Optional[datetime]:
        """Parse NSE date strings into datetime objects."""
        formats = ["%d-%b-%Y", "%d-%b-%y", "%Y-%m-%d"]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None

    @staticmethod
    def calculate_fraction(month: int) -> float:
        """Calculate years since last annual filing based on the current month."""
        if month in [4, 5, 6]:
            return 0.25
        elif month in [7, 8, 9]:
            return 0.50
        elif month in [10, 11, 12]:
            return 0.75
        elif month in [1, 2, 3]:
            return 1.00
        return 0.0

    def get_valid_filings(self, raw_filings: list[dict]) -> list[FilingMetadata]:
        """Filter out governance reports and parse into domain models."""
        valid_filings = []
        for f in raw_filings:
            date_obj = self.parse_date(f["date_str"])
            if not date_obj:
                continue

            url = f.get("xbrl_url", "")
            ftype = f.get("type", "")

            # Skip governance reports
            if "GOVERNANCE" in url.upper() or "governance" in ftype.lower():
                continue

            is_consolidated = "Consolidated" in ftype or "Consolidated" in f.get("consolidated", "")

            valid_filings.append(
                FilingMetadata(
                    date=date_obj,
                    url=url,
                    type=ftype,
                    source=f["source"],
                    is_consolidated=is_consolidated,
                )
            )

        # Sort by date descending
        valid_filings.sort(key=lambda x: x.date, reverse=True)
        return valid_filings

    def select_targets(self, raw_filings: list[dict]) -> Optional[TargetFilings]:
        """Identify Current YTD, Latest BS/CF, Annual, and Prior YTD filings."""
        valid_filings = self.get_valid_filings(raw_filings)
        if not valid_filings:
            logger.warning("No valid financial XBRL filings found.")
            return None

        unique_dates = sorted({f.date for f in valid_filings}, reverse=True)
        most_recent_date = unique_dates[0]
        fraction = self.calculate_fraction(most_recent_date.month)

        def get_best_file(target_date: datetime) -> Optional[FilingMetadata]:
            files_for_date = [f for f in valid_filings if f.date == target_date]
            if not files_for_date:
                return None
            cons = [f for f in files_for_date if f.is_consolidated]
            if cons:
                return cons[0]
            return files_for_date[0]

        targets = TargetFilings(
            fraction_of_year=fraction,
            current_date=most_recent_date.strftime("%Y-%m-%d"),
        )

        # 1. Current YTD
        current_file = get_best_file(most_recent_date)
        if current_file:
            targets.current_ytd = current_file

        # 2. Latest Balance Sheet / Cash Flow (Most recent September or March)
        latest_bs_date = None
        for d in unique_dates:
            if d.month in [3, 9]:
                latest_bs_date = d
                break

        if latest_bs_date:
            targets.latest_bs_cf = get_best_file(latest_bs_date)

        # If most recent is Q4 (fraction 1.0), we only need this annual file for TTM and BS
        if fraction == 1.00:
            targets.annual = current_file
            # Note: We keep latest_bs_cf and current_ytd as they are, or just rely on annual.
            # But having them defined explicitly is fine.
            return targets

        # 3. Most Recent Annual (March of current or previous calendar year)
        annual_year = most_recent_date.year if most_recent_date.month > 3 else most_recent_date.year - 1
        annual_date = datetime(annual_year, 3, 31)

        annual_file = get_best_file(annual_date)
        if annual_file:
            targets.annual = annual_file

        # 4. Prior YTD (Exact same month, previous year)
        prior_date = datetime(most_recent_date.year - 1, most_recent_date.month, most_recent_date.day)
        prior_file = get_best_file(prior_date)

        if prior_file:
            targets.prior_ytd = prior_file

        return targets
