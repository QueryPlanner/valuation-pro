#!/bin/bash

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Set PYTHONPATH to include the project root so valuation_engine can be imported
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# Run uvicorn with uv
cd "$SCRIPT_DIR"
uv run uvicorn valuation_service.main:app --reload "$@"
