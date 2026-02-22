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
└── valuation-service/   # FastAPI REST API
    └── src/valuation_service/
        ├── app.py              # FastAPI application factory
        ├── api/                # Endpoints, schemas
        ├── connectors/         # Data source adapters (Yahoo, SEC)
        ├── services/           # Orchestration layer
        └── utils/              # JSON sanitization, etc.

tests/                   # All tests (engine + service)
docs/                    # Methodology & documentation
```

## Getting Started

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (Python package manager)

### Setup

```bash
# Install all dependencies
uv sync --all-packages

# Run test suite
uv run pytest tests/ -v

# Start development server
uv run uvicorn valuation_service.app:app --reload

# Lint code
uv run ruff check packages/ tests/
```

## Documentation

- [Methodology](docs/METHODOLOGY.md) — FCFF Ginzu valuation model documentation
- [Engine Guide](docs/valuation_engine.md) — Usage guide for the valuation engine
- [Cost of Capital](docs/cost_of_capital_worksheet.md) — Cost of capital worksheet reference
