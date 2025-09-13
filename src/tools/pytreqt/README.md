# pytreqt - pytest Requirements Tracking

A pytest plugin for validating and reporting functional requirements (FR) and business rules (BR) coverage.

## Features

- ✅ **Validates** requirement IDs in test docstrings against specification files
- 🎨 **Colorful reporting** with ✓ (passed), ✗ (failed), ⊝ (skipped) status
- 📊 **Coverage analysis** showing which requirements are tested
- 🚫 **Prevents typos** by catching invalid requirement references
- 📈 **Auto-generates** TEST_COVERAGE.md with traceability matrix
- 🔍 **Change detection** identifies tests affected by requirement updates

## Structure

```
pytreqt/
├── __main__.py              # Central CLI entry point
├── __init__.py              # Package initialization
├── pytreqt.py               # Main pytest plugin
├── README.md                # This documentation
└── tools/                   # Standalone tools
    ├── __init__.py
    ├── generate_coverage_report.py  # Auto-generates TEST_COVERAGE.md
    ├── change_detector.py           # Detects requirement changes
    └── update_traceability.py       # Updates all artifacts
```

## Configuration

The plugin is configured in `pyproject.toml`:
```toml
[tool.pytest.ini_options]
addopts = "-p pytreqt.pytreqt"
```

## Usage

### Basic Testing with Requirements Coverage
Run any pytest command with `-v` to see requirements coverage:
```bash
uv run pytest -v
```

### Central CLI Interface
Use the unified command interface:
```bash
python -m pytreqt coverage     # Generate TEST_COVERAGE.md
python -m pytreqt changes      # Check for requirement changes
python -m pytreqt update       # Update all artifacts
python -m pytreqt help         # Show available commands
```

### Direct Tool Access
Or run tools directly:
```bash
uv run python pytreqt/tools/generate_coverage_report.py
uv run python pytreqt/tools/change_detector.py
uv run python pytreqt/tools/update_traceability.py
```

## Test Format

Reference requirements in test docstrings:
```python
def test_example():
    """Test something important.

    Requirements:
    - FR-1.1: Users can create objects
    - BR-3.3: Operations are atomic
    """
    assert True
```

## Future

pytreqt is designed to become a separate reusable package for any project needing requirements tracking.
