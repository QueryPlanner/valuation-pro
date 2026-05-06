import argparse
import logging
import sys

from xbrl_downloader.downloader import DownloaderOrchestrator


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def main():
    setup_logging()
    parser = argparse.ArgumentParser(
        description="Download XBRL filings required for accurate TTM calculation from NSE."
    )
    parser.add_argument("symbol", help="NSE Symbol (e.g., BPCL)")
    parser.add_argument(
        "--output-dir",
        default="valuation_data",
        help="Directory to save downloaded files (default: valuation_data)",
    )

    args = parser.parse_args()

    downloader = DownloaderOrchestrator(symbol=args.symbol, output_dir=args.output_dir)
    metadata = downloader.run()

    if not metadata:
        sys.exit(1)


if __name__ == "__main__":
    main()
