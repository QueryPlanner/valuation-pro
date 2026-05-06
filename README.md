# Valuation Pro

A Python implementation of advanced valuation models, designed for 1:1 mathematical parity with reference Google Sheets models.

## Project Structure

This is a **UV workspace monorepo** with two packages:

```
packages/
├── valuation-engine/    # Pure computation library (zero external deps)
│   └── src/valuation_engine/
│       ├── engine.py           # FCFF Ginzu engine
│       ├── inputs_builder.py   # Canonical input preparation
│       └── models/             # Data contracts (re-exports)
│
├── valuation-service/   # FastAPI REST API
│   └── src/valuation_service/
│       ├── app.py              # FastAPI application factory
│       ├── api/                # Endpoints, schemas
│       ├── connectors/         # Data source adapters (Yahoo, SEC)
│       ├── services/           # Orchestration layer
│       └── utils/              # JSON sanitization, etc.
│
└── xbrl-downloader/     # CLI utility to download NSE XBRL filings
    └── src/xbrl_downloader/
        ├── cli/                # Command-line interface
        ├── downloader.py       # Orchestrator
        ├── client.py           # NSE API client
        └── selector.py         # Filing selection logic

tests/                   # All tests (engine + service)
docs/                    # Methodology & documentation
```

## Getting Started

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (Python package manager)

### XBRL Downloader
The `xbrl-downloader` tool intelligently fetches financial filings from the NSE to enable exact Trailing Twelve Months (TTM) calculations (without relying on crude annualization). It specifically:
- Prefers **Consolidated** filings over Standalone ones.
- Targets up to 4 exact filings: **Most Recent Annual**, **Current YTD**, **Prior YTD** (by scanning up to 24 months of history), and the **Latest Balance Sheet**.
- Saves the XML files and generates a `valuation_metadata.json` for the valuation engine.

```bash
# Download XBRL filings for a specific NSE symbol
uv run xbrl-downloader HCLTECH

# Specify a custom output directory (default: valuation_data)
uv run xbrl-downloader INFY --output-dir my_data_folder
```

### AI Extraction Pipeline
The project includes an AI pipeline that extracts inputs directly from XBRL data into the valuation schema. We use **Gemini 3 Flash Preview** (via OpenRouter) due to its excellent instruction following capabilities for accounting adjustments.
- **Core EBIT Calculation**: We compute "pure" EBIT that strictly excludes exceptional items and non-operating income to represent sustainable, recurring earning power: `ProfitBeforeExceptionalItemsAndTax - OtherIncome + FinanceCosts`.
- **Marginal Tax Rate**: Defaulted to 30% for India.

### Setup

```bash
# Install all dependencies
uv sync --all-packages

# Run test suite
uv run pytest tests/ -v

# Start development server
uv run uvicorn valuation_service.app:app --reload

# Download XBRL filings for a company (e.g., BPCL)
uv run xbrl-downloader BPCL

# Lint code
uv run ruff check packages/ tests/
```

## Documentation

- [Methodology](docs/METHODOLOGY.md) — FCFF Ginzu valuation model documentation
- [Engine Guide](docs/valuation_engine.md) — Usage guide for the valuation engine
- [Cost of Capital](docs/cost_of_capital_worksheet.md) — Cost of capital worksheet reference
