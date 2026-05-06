import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from xbrl_downloader.client import NSEClient
from xbrl_downloader.models import DownloadedFile, ValuationMetadata
from xbrl_downloader.parser import XBRLParser
from xbrl_downloader.selector import FilingSelector

logger = logging.getLogger(__name__)


class DownloaderOrchestrator:
    """Orchestrates the selection and downloading of XBRL filings."""

    def __init__(self, symbol: str, output_dir: str = "valuation_data") -> None:
        self.symbol = symbol.upper()
        self.output_dir = Path(output_dir) / self.symbol
        self.client = NSEClient()
        self.selector = FilingSelector()

    def run(self) -> Optional[ValuationMetadata]:
        logger.info(f"VALUATION XBRL DOWNLOADER: {self.symbol}")

        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Fetching filings list from NSE...")
        raw_filings = self.client.get_all_filings_metadata(self.symbol)
        logger.info(f"Found {len(raw_filings)} total filings with XBRL links.")

        logger.info("Analyzing dates to find Target Valuation Filings...")
        targets = self.selector.select_targets(raw_filings)

        if not targets:
            logger.error("Failed to identify target filings.")
            return None

        logger.info(f"Most Recent Data Date: {targets.current_date}")
        logger.info(f"Fraction of Year Completed: {targets.fraction_of_year}")

        metadata = ValuationMetadata(
            symbol=self.symbol,
            extraction_date=datetime.now().isoformat(),
            fraction_of_year=targets.fraction_of_year,
            files={},
        )

        files_to_download = {}
        if targets.current_ytd:
            files_to_download["Current_YTD"] = targets.current_ytd
        if targets.latest_bs_cf:
            files_to_download["Latest_BS_CF"] = targets.latest_bs_cf
        if targets.annual:
            files_to_download["Annual"] = targets.annual
        if targets.prior_ytd:
            files_to_download["Prior_YTD"] = targets.prior_ytd

        logger.info(f"Files to download: {list(files_to_download.keys())}")

        for key, filing in files_to_download.items():
            date_str = filing.date.strftime("%Y-%m-%d")
            ext = filing.url.split("?")[0].split(".")[-1]
            if len(ext) > 4:
                ext = "xml"
            filename = f"{self.symbol}_{key}_{date_str}.{ext}"
            filepath = self.output_dir / filename

            content = self.client.download_file(filing.url)
            if content:
                with open(filepath, "wb") as f:
                    f.write(content)
                logger.info(f"Downloaded {filename}")

                # Parse the XML and save as JSON
                parsed_json_path = None
                try:
                    if ext == "xml":
                        parser = XBRLParser(filepath)
                        parsed_data = parser.parse()

                        json_filename = f"{self.symbol}_{key}_{date_str}.json"
                        json_filepath = self.output_dir / json_filename
                        with open(json_filepath, "w", encoding="utf-8") as jf:
                            json.dump(parsed_data, jf, indent=2)

                        parsed_json_path = str(json_filepath)
                        logger.info(f"Parsed and saved JSON to {json_filename}")
                except Exception:
                    logger.exception(f"Failed to parse {filename}")

                metadata.files[key] = DownloadedFile(
                    date=date_str,
                    path=str(filepath),
                    original_url=filing.url,
                    parsed_json_path=parsed_json_path,
                )
            else:
                logger.error(f"Failed to download {filename}")

        # Save metadata
        meta_path = self.output_dir / "valuation_metadata.json"
        with open(meta_path, "w") as f:
            f.write(metadata.model_dump_json(indent=2))

        logger.info(f"Success! Metadata saved to {meta_path}")
        return metadata
