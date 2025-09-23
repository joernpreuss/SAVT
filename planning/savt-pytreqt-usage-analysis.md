# SAVT pytreqt Usage Analysis

## Current Integration Points

### 1. pytest Plugin Registration
**Location**: `pyproject.toml:77`
```toml
addopts = "-p src.tools.pytreqt.pytreqt"
```
- Automatically loads pytreqt as a pytest plugin
- Plugin runs during every test execution
- Captures requirement annotations from test docstrings

### 2. CLI Wrapper Script
**Location**: `/pytreqt` (bash script)
```bash
#!/bin/bash
exec uv run python -m src.tools.pytreqt "$@"
```
- Provides convenient CLI access: `./pytreqt coverage`
- Passes all arguments to the Python module

### 3. QA Tool Integration
**Location**: `src/tools/qa/qa.py:264`
```python
cmd = ["uv", "run", "python", "-m", "src.tools.pytreqt", "show"]
```
- QA tool option 7 calls pytreqt show command
- Displays requirements coverage from last test run

## Current Configuration (Hardcoded)

### Requirements File Location
```python
REQUIREMENTS_FILE = Path() / "specs" / "spec" / "REQUIREMENTS.md"
```

### Requirement ID Patterns
```python
pattern = r"\b(FR-\d+\.?\d*|BR-\d+\.?\d*)\b"
```
- FR- (Functional Requirements): FR-1.1, FR-2.3
- BR- (Business Rules): BR-3.1, BR-4.2

### Database Detection Logic
```python
if os.getenv("TEST_DATABASE") == "postgresql":
    database_type = "PostgreSQL"
else:
    database_type = "SQLite"
```

### Cache Directory
```python
cache_dir = Path(".pytest_cache")
```

### Output Directory
```python
output_file = Path("specs") / "reports" / "TEST_COVERAGE.md"
```

## Current CLI Commands

1. `./pytreqt coverage` - Generate TEST_COVERAGE.md report
2. `./pytreqt show` - Display last run results
3. `./pytreqt stats` - Show detailed statistics
4. `./pytreqt changes` - Check for requirement changes
5. `./pytreqt update` - Update all artifacts

## Current Dependencies

From `src/tools/pytreqt/pytreqt.py`:
- `pytest` - Core testing framework
- `click` - CLI interface
- `rich` - Terminal formatting
- `pathlib` - Path handling
- `re` - Regex pattern matching
- `json` - Data serialization
- `os` - Environment variables

## Test Integration Patterns

### Requirement Annotation Format
Tests include requirements in docstrings:
```python
def test_create_item_with_feature():
    """
    Test item creation with associated feature.

    Covers:
    - FR-1.1: Users can create items with unique names
    - FR-2.1: Users can create features with names
    - FR-2.2: Features can be associated with items
    """
```

### Coverage Reporting
- Extracts requirements from all test docstrings
- Matches against valid requirements in REQUIREMENTS.md
- Generates traceability matrix in TEST_COVERAGE.md
- Reports coverage percentage and untested requirements

## Verification Results

✅ **CLI Integration**: All commands work correctly
✅ **pytest Plugin**: Automatically detects and reports requirements
✅ **QA Tool Integration**: Option 7 successfully shows coverage
✅ **Coverage Generation**: Creates TEST_COVERAGE.md with 96.6% coverage
✅ **Statistics**: Shows 29 total requirements, 28 tested

## Migration Requirements for Standalone Package

### Must Preserve
1. **Identical CLI commands** - All existing commands work the same way
2. **pytest plugin behavior** - Same automatic requirement detection
3. **Output formats** - TEST_COVERAGE.md format unchanged
4. **Cache compatibility** - Existing .pytest_cache files work

### Must Make Configurable
1. **Requirements file path** - Currently hardcoded to `specs/spec/REQUIREMENTS.md`
2. **Requirement patterns** - Currently only FR- and BR- patterns
3. **Database detection** - Currently hardcoded environment variable names
4. **Output directories** - Currently hardcoded paths
5. **Cache location** - Currently hardcoded to `.pytest_cache`

### SAVT-Specific Configuration for Migration
```toml
[tool.pytreqt]
requirements_file = "specs/spec/REQUIREMENTS.md"
requirement_patterns = ["FR-\\d+\\.?\\d*", "BR-\\d+\\.?\\d*"]
cache_dir = ".pytest_cache"

[tool.pytreqt.database]
detect_from_env = ["TEST_DATABASE"]
default_type = "SQLite"

[tool.pytreqt.reports]
output_dir = "specs/reports"
```

## Integration Test Results

**Current Status**: ✅ All functionality verified working
- pytest plugin captures requirements correctly
- CLI commands generate proper reports
- QA tool integration functions as expected
- No breaking changes anticipated with proper configuration
