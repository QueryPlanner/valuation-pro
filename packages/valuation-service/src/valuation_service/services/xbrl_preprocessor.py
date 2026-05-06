import json
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Key XBRL tags we care about to reduce context size
KEY_TAGS = {
    "RevenueFromOperations",
    "TotalIncome",
    "ProfitBeforeExceptionalItemsAndTax",
    "ProfitLossBeforeTax",
    "ProfitBeforeTax",
    "ProfitLoss",
    "OtherIncome",
    "TotalEquity",
    "FinanceCosts",
    "EquityAttributableToOwnersOfParent",
    "NonControllingInterests",
    "NonControllingInterest",
    "MinorityInterest",
    "Borrowings",
    "BorrowingsCurrent",
    "BorrowingsNoncurrent",
    "OtherNoncurrentFinancialLiabilities",
    "OtherCurrentFinancialLiabilities",
    "FinanceCosts",
    "CashAndCashEquivalents",
    "BankBalanceOtherThanCashAndCashEquivalents",
    "NoncurrentInvestments",
    "CurrentInvestments",
    "TaxExpense",
    "CurrentTaxExpense",
}


def load_xbrl_data(symbol: str, data_dir: str = "valuation_data") -> Dict[str, Any]:
    """Loads and condenses XBRL data for a given symbol."""
    base_path = Path(data_dir) / symbol
    metadata_file = base_path / "valuation_metadata.json"

    if not metadata_file.exists():
        raise FileNotFoundError(f"Metadata file not found at {metadata_file}")

    with open(metadata_file, "r") as f:
        metadata = json.load(f)

    condensed_data = {"symbol": symbol, "fraction_of_year": metadata.get("fraction_of_year", 1.0), "periods": {}}

    for period_key, file_info in metadata.get("files", {}).items():
        json_path = file_info.get("parsed_json_path")
        if not json_path:
            continue

        full_path = Path(json_path)
        if not full_path.exists():
            logger.warning(f"Parsed JSON not found: {full_path}")
            continue

        with open(full_path, "r") as f:
            raw_data = json.load(f)

        # Filter down to key tags
        filtered_period = {}
        for duration_or_instant, metrics in raw_data.items():
            filtered_metrics = {}
            if isinstance(metrics, dict):
                for tag_key, value in metrics.items():
                    main_tag = tag_key.split(" [")[0].strip()
                    if main_tag in KEY_TAGS:
                        filtered_metrics[tag_key] = value
            if filtered_metrics:
                filtered_period[duration_or_instant] = filtered_metrics

        condensed_data["periods"][period_key] = {"date": file_info.get("date"), "data": filtered_period}

    return condensed_data
