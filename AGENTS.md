# Agent Rules

## Continuous Integration
- **Always run CI checks before committing or pushing changes.**
  - **Linting:** Run `uv run ruff check packages/ tests/` and fix any issues.
  - **Formatting:** Run `uv run ruff format --check packages/ tests/` and fix any issues.
  - **Testing:** Run `uv run pytest tests/ -v --tb=short` and ensure all tests pass.
