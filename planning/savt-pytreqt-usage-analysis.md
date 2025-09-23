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

### Main Usage
```
Usage: python -m src.tools.pytreqt [OPTIONS] COMMAND [ARGS]...
  pytreqt - pytest requirements tracking
```

### Available Commands

#### 1. `coverage` - Generate TEST_COVERAGE.md report
```
Usage: python -m src.tools.pytreqt coverage [OPTIONS]
  Generate TEST_COVERAGE.md report
Options:
  -h, --help  Show this message and exit.
```
- **Function**: Extracts requirements from specifications, analyzes test coverage
- **Output**: Creates `specs/reports/TEST_COVERAGE.md` with traceability matrix
- **Example output**: "✅ Coverage report generated: specs/reports/TEST_COVERAGE.md"

#### 2. `stats` - Show detailed requirements statistics
```
Usage: python -m src.tools.pytreqt stats [OPTIONS]
  Show detailed requirements statistics
Options:
  --format [text|json|csv]  Output format
  -h, --help                Show this message and exit.
```
- **Function**: Displays coverage statistics in table format
- **Formats**: text (default), json, csv
- **Output**: Rich table with metrics like total requirements, tested count, coverage %

#### 3. `show` - Display last run results
```
Usage: python -m src.tools.pytreqt show [OPTIONS]
  Show requirements coverage from last test run
Options:
  -h, --help  Show this message and exit.
```
- **Function**: Shows requirements coverage from cached test results
- **Data source**: `.pytest_cache/requirements_coverage.json`

#### 4. `changes` - Check for requirement changes
```
Usage: python -m src.tools.pytreqt changes [OPTIONS]
  Check for requirement changes
Options:
  -h, --help  Show this message and exit.
```
- **Function**: Detects changes in requirements file and affected tests

#### 5. `update` - Update all traceability artifacts
```
Usage: python -m src.tools.pytreqt update [OPTIONS]
  Update all traceability artifacts
Options:
  -h, --help  Show this message and exit.
```
- **Function**: Runs all update operations (coverage, changes, stats)

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

## Standalone Repository Current State

**Repository**: https://github.com/joernpreuss/pytreqt
**Status**: Phase 0 complete, Phase 1 pending

### Current CLI Implementation
```bash
$ pytreqt --help
pytreqt CLI - Coming soon in Phase 1!
```

### Placeholder Commands (Not Implemented)
- `pytreqt init` - Configuration generation (planned)
- `pytreqt coverage` - Coverage analysis (planned)
- `pytreqt show` - Display results (planned)

### Current Code Status
- **Entry points**: Configured in pyproject.toml
- **Dependencies**: click, rich, pytest properly configured
- **CLI module**: Placeholder main() function only
- **Plugin module**: Empty RequirementsPlugin class with pytest hooks
- **Tools**: Empty directory structure

**Ready for Phase 1**: All infrastructure in place, needs real functionality from SAVT
