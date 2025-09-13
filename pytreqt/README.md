# pytreqt - pytest Requirements Tracking

A pytest plugin for validating and reporting functional requirements (FR) and business rules (BR) coverage.

## Features

- ✅ **Validates** requirement IDs in test docstrings against specification files
- 🎨 **Colorful reporting** with ✓ (passed), ✗ (failed), ⊝ (skipped) status
- 📊 **Coverage analysis** showing which requirements are tested
- 🚫 **Prevents typos** by catching invalid requirement references
- 📈 **Auto-generates** TEST_COVERAGE.md with traceability matrix
- 🔍 **Change detection** identifies tests affected by requirement updates

## Files

- **`pytreqt.py`** - Main plugin module
- **`__init__.py`** - Package initialization
- **`generate_coverage_report.py`** - Auto-generates TEST_COVERAGE.md
- **`change_detector.py`** - Detects requirement changes and affected tests
- **`update_traceability.py`** - Updates all traceability artifacts
- **`README.md`** - This documentation

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

### Coverage Matrix Generation
Auto-generate TEST_COVERAGE.md with complete traceability matrix:
```bash
uv run python pytreqt/generate_coverage_report.py
```

### Change Detection
Check for requirement changes and identify affected tests:
```bash
uv run python pytreqt/change_detector.py
```

### Complete Traceability Update
Update all traceability artifacts in one command:
```bash
uv run python pytreqt/update_traceability.py
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
