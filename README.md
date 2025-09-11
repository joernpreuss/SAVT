# SAVT
Pure Python Suggestion And Veto Tool

## Start
- Python version is pinned to 3.12 via `.python-version` to ensure consistent behavior across development environments and match the pyproject.toml requirement (~=3.12.0)

### Run test server
- `uv run uvicorn src.main:app --reload --host 0.0.0.0`
  
### Run tests
- `uv run pytest`
