# QA Tool Export Plan

## Overview

Extract SAVT's project-specific `qa.py` into a standalone, reusable package that discovers local configuration like nox, while maintaining 100% functionality for SAVT.

## Current State Analysis

### SAVT's qa.py Structure
- **Location**: `src/tools/qa/qa.py` - 935 lines of sophisticated QA tooling
- **Dependencies**: typer, rich, subprocess, pathlib (all standard/common libraries)
- **Generic functionality**: ~60% (command execution, interactive prompts, basic checks)
- **SAVT-specific functionality**: ~40% (database testing, nox integration, hardcoded paths)
- **Integration points**:
  - Nox configuration imports (`noxfile.py` functions)
  - SAVT database credentials and test patterns
  - QA wrapper script: `./qa` (bash script)
  - Interactive menu system with extensive features

### Key Features to Preserve (All Current Functionality)
- ✅ **Interactive menu system** with single-key navigation (f/s/q prompts)
- ✅ **Parallel test execution** (Fibonacci sequence workers: 1,2,3,5,8,13,21,34,55,89,120,160,200)
- ✅ **Database switching** (SQLite/PostgreSQL with environment setup)
- ✅ **Fix/skip/quit prompts** for each check type with unsafe fix options
- ✅ **Requirements coverage integration** (`pytreqt show` command)
- ✅ **Custom newlines checking** script integration
- ✅ **Nox session integration** for consistent tool configuration
- ✅ **Rich terminal output** with colors, emojis, and progress indicators
- ✅ **ESC key support** for quick quit from any menu
- ✅ **Template formatting** (djlint integration)
- ✅ **Individual command support** (format, lint, typecheck, newlines)

### SAVT-Specific Code Requiring Abstraction

#### Hard-coded Database Configuration
**Current** (`qa.py:547-561`):
```python
cmd = [
    "env",
    "TEST_DATABASE=postgresql",
    "DATABASE_URL=postgresql://savt_user:savt_password@localhost:5432/savt",
    "uv", "run", "pytest", "--color=yes"
]
```

#### Fixed File Structure Assumptions
**Current** (`qa.py:24-26`):
```python
paths = ["src/", "tests/"] if path == "." else [f"{path}/src/", f"{path}/tests/"]
```

#### Nox Function Imports
**Current** (`qa.py:12-18`):
```python
from noxfile import (
    get_djlint_command,
    get_format_command,
    get_lint_command,
    get_typecheck_command,
)
```

#### Custom Script Integration
**Current** (`qa.py:58-82`):
```python
script_dir = Path(__file__).parent
tools_dir = script_dir.parent  # Go up from src/tools/qa to src/tools
check_newlines_path = tools_dir / "check_newlines.py"
```

## Configuration Strategy

### Use Current SAVT Configuration as Baseline

Following the successful pytreqt approach: **Use SAVT's proven configuration as the starting point**, then make it configurable without redesigning everything.

### SAVT-Specific Configuration
For SAVT migration, preserve exact current behavior:

```toml
[tool.qa]
# Core tool configurations (from noxfile.py)
lint_tool = ["uv", "tool", "run", "ruff", "check"]
lint_paths = ["src/", "tests/"]
format_tool = ["uv", "tool", "run", "ruff", "format"]
format_paths = ["src/", "tests/"]
typecheck_tool = ["uv", "tool", "run", "mypy"]
typecheck_paths = ["src/", "tests/"]

# Template support
has_templates = true
template_tool = ["uv", "run", "djlint"]
template_paths = ["templates/"]

# Database testing (SAVT-specific)
databases = ["sqlite", "postgresql"]
postgresql_url = "postgresql://savt_user:savt_password@localhost:5432/savt"
test_env_var = "TEST_DATABASE"

# Custom integrations
newlines_script = "src/tools/check_newlines.py"
requirements_tool = ["uv", "run", "pytreqt", "show"]

# Interactive features
parallel_workers = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 120, 160, 200]  # Fibonacci sequence
default_database = "sqlite"

# Tool runner
runner = "uv"
```

### Configuration Discovery Logic

Like nox and pytreqt, walk up the directory tree:

1. **Primary**: `pyproject.toml [tool.qa]` section
2. **Fallback**: `qa.toml` dedicated file
3. **Backwards compatibility**: Import functions from existing `noxfile.py`
4. **Default**: Sensible generic configuration for any Python project

## Implementation Plan

### Phase 0: Preparation (3-5 days)

Infrastructure setup before code extraction to reduce risk:

#### 1. Repository & Infrastructure Setup
- [ ] Create GitHub repository `qa-tool` with basic structure
- [ ] Set up CI/CD pipeline (GitHub Actions) for multi-platform testing
- [ ] Choose and add license (MIT recommended for wide adoption)
- [ ] Create initial `pyproject.toml` with package metadata and entry points

#### 2. Dependency Analysis & Planning
- [ ] Audit current qa.py dependencies (typer, rich, subprocess, pathlib)
- [ ] Research uv tool best practices and distribution methods
- [ ] Plan configuration file schema using SAVT as baseline
- [ ] Document all current CLI commands and their exact behavior

#### 3. SAVT Integration Analysis
- [ ] Document current usage patterns (how `./qa` script works, nox integration)
- [ ] Test current qa functionality thoroughly to establish baseline
- [ ] Identify all places qa is referenced in SAVT

#### 4. Configuration Design
- [ ] Design exact config file format using current SAVT values
- [ ] Plan migration path for SAVT's current hardcoded values
- [ ] Create test cases for different configuration scenarios

### Phase 1: Extract & Generalize (1-2 weeks)

1. **Create repository**: `github.com/joernpreuss/qa-tool`
2. **Copy & refactor code**:
   - [ ] Extract configuration system
   - [ ] Remove SAVT-specific hardcoded values
   - [ ] Generalize database detection and testing
   - [ ] Make file paths and tool commands configurable
3. **Add configuration support**:
   - [ ] Parse `pyproject.toml [tool.qa]` and `qa.toml`
   - [ ] Add validation for config values
   - [ ] Implement noxfile.py imports for backwards compatibility
4. **Preserve all interactive features**:
   - [ ] Single-key navigation system
   - [ ] Parallel worker selection (Fibonacci sequence)
   - [ ] Database switching functionality
   - [ ] Rich terminal output and formatting

### Phase 2: Polish & Test (1 week)

1. **Package structure**:
   - [ ] Create proper Python package with modern typing
   - [ ] Add entry points for CLI and uv tool integration
   - [ ] Set up comprehensive test suite
2. **Documentation**:
   - [ ] Comprehensive README with usage examples
   - [ ] Migration guide for existing qa.py users
   - [ ] Configuration reference documentation
3. **Quality assurance**:
   - [ ] Complete test coverage for all features
   - [ ] Code quality checks (ruff, mypy)
   - [ ] Performance testing with large test suites

### Phase 3: Publish & Migrate (1 week)

1. **Publish package**:
   - [ ] Package as `qa-tool` and publish to PyPI
   - [ ] Set up automated releases from GitHub
   - [ ] Create release notes and versioning strategy
2. **Update SAVT integration**:
   - [ ] Add `pyproject.toml [tool.qa]` configuration with SAVT settings
   - [ ] Test feature parity with current `./qa` script
   - [ ] Update SAVT to use `uv tool install qa-tool`
   - [ ] Remove `src/tools/qa/` directory and bash wrapper
   - [ ] Update CI/CD and documentation

## Package Structure

```
qa-tool/
├── pyproject.toml              # Package metadata, dependencies, entry points
├── README.md                   # Usage documentation and examples
├── LICENSE                     # MIT license for wide adoption
├── CHANGELOG.md                # Version history and release notes
├── src/
│   └── qa_tool/
│       ├── __init__.py         # Package exports and version
│       ├── __main__.py         # CLI entry point for `python -m qa_tool`
│       ├── cli.py              # Main CLI interface (typer-based)
│       ├── config.py           # Configuration discovery and loading
│       ├── commands.py         # Tool command builders (configurable)
│       ├── interactive.py      # Menu systems and single-key prompts
│       ├── runners.py          # Command execution engine
│       ├── compat.py           # Backwards compatibility (noxfile imports)
│       └── database.py         # Database testing and environment setup
├── tests/                      # Comprehensive test suite
│   ├── test_cli.py            # CLI command testing
│   ├── test_config_discovery.py # Configuration loading tests
│   ├── test_interactive.py    # Interactive menu testing
│   ├── test_backwards_compat.py # noxfile.py import testing
│   └── fixtures/              # Sample project structures
│       ├── minimal/           # Basic Python project
│       ├── with-templates/    # Project with HTML templates
│       ├── with-noxfile/      # Project using noxfile.py
│       └── savt-like/         # SAVT-style configuration
└── examples/                  # Usage examples and documentation
    ├── basic-usage.md
    ├── django-integration.md
    ├── fastapi-integration.md
    └── migration-guide.md
```

## Key Components

### Configuration Loader

```python
class QAConfig:
    def __init__(self, config_data: dict):
        self.lint = ToolConfig(config_data.get("lint", DEFAULT_LINT))
        self.format = ToolConfig(config_data.get("format", DEFAULT_FORMAT))
        self.typecheck = ToolConfig(config_data.get("typecheck", DEFAULT_TYPECHECK))
        # ...

    @classmethod
    def discover(cls, start_path: Path = None) -> "QAConfig":
        """Find and load configuration like nox does"""
```

### Command Builder

```python
class ToolBuilder:
    def __init__(self, config: QAConfig):
        self.config = config

    def build_lint_cmd(self, fix=False, unsafe=False) -> list[str]:
        cmd = list(self.config.lint.tool)
        cmd.extend(self.config.lint.paths)
        if fix:
            cmd.append("--fix")
            if unsafe:
                cmd.append("--unsafe-fixes")
        return cmd
```

### Interactive System

Preserve all current interactive features:
- Single-key navigation (f/s/q prompts)
- Database selection menu
- Parallel worker selection (Fibonacci sequence)
- Requirements coverage display
- Clear screen functionality

## Backwards Compatibility Guarantees

Following the successful pytreqt model:

- **CLI commands**: All existing commands work identically (`qa check`, `qa format`, `qa lint`, etc.)
- **Interactive behavior**: Same menu system, key bindings, and user experience
- **Output formats**: Identical terminal output, colors, and formatting
- **Configuration**: Existing SAVT workflow continues unchanged during transition
- **Performance**: Same or better execution speed and parallel testing

## Migration Strategy

### SAVT Migration Path

1. **Add configuration**: Create `pyproject.toml [tool.qa]` with current SAVT settings
2. **Install standalone**: `uv tool install qa-tool`
3. **Test feature parity**: Verify all 935 lines of functionality work identically
4. **Switch gradually**: Use global `qa` command alongside existing `./qa` script
5. **Clean up**: Remove `src/tools/qa/` directory and bash wrapper
6. **Update CI/CD**: Update GitHub Actions to use global qa tool

### Other Projects

```bash
# One-time global installation
uv tool install qa-tool

# Add project-specific configuration
# pyproject.toml:
[tool.qa]
lint_tool = ["ruff", "check"]  # or ["pylint"], ["flake8"]
format_tool = ["black"]       # or ["autopep8"], ["ruff", "format"]
paths = ["src/", "tests/"]     # or ["myapp/", "test/"]

# Use anywhere with project-specific settings
qa check --fix-all
qa i                          # Interactive mode
```

## Expected Benefits

### For SAVT
- ✅ Keep all current functionality and interactive features
- ✅ Cleaner project structure (remove `src/tools/qa/`)
- ✅ Shared configuration with other development tools
- ✅ Easier maintenance and updates

### For Other Projects
- ✅ Reusable QA tool with project-specific configuration
- ✅ No need to reinvent interactive QA workflows
- ✅ Consistent experience across different project types
- ✅ Rich interactive features out of the box

### Developer Experience

```bash
# One-time global installation
uv tool install qa-tool

# Works in any project with configuration
cd ~/projects/my-django-app
qa check                    # Check all QA aspects
qa check --fix-all          # Fix what can be auto-fixed
qa format                   # Just run formatters
qa i                        # Interactive mode

# Discovers project-specific settings automatically
# - Different linters (ruff, pylint, flake8)
# - Different formatters (black, autopep8, ruff)
# - Different test runners (pytest, unittest)
# - Custom scripts and integrations
```

## Success Metrics

### Technical Metrics
- [ ] **100% feature parity** with SAVT's current qa.py functionality
- [ ] **Configuration discovery** works in any project structure
- [ ] **Performance**: Handle 1000+ tests with parallel execution
- [ ] **Cross-platform**: Windows, macOS, Linux compatibility
- [ ] **Python compatibility**: Python 3.10+ support

### Quality Metrics
- [ ] **Test coverage**: 95%+ coverage for qa-tool package
- [ ] **Documentation coverage**: Comprehensive usage examples
- [ ] **Code quality**: ruff, mypy, and modern typing standards
- [ ] **User experience**: All interactive features preserved

### Adoption Metrics
- [ ] **SAVT migration**: Completed without functionality loss
- [ ] **External usage**: At least 2 projects using qa-tool
- [ ] **Community**: GitHub stars, issues, and contributions
- [ ] **Distribution**: Available as `uv tool install qa-tool`

## Benefits of Standalone Package

### For qa-tool Users
- **Easy installation**: `uv tool install qa-tool`
- **Project flexibility**: Works with any Python project structure
- **Rich features**: Sophisticated interactive menus and parallel testing out of the box
- **Semantic versioning**: Clear upgrade paths and change communication

### For SAVT Project
- **Reduced maintenance**: Focus on core SAVT functionality
- **Smaller codebase**: Remove 935 lines of QA tooling code
- **Better testing**: qa-tool gets dedicated test suite and CI
- **Latest features**: Automatic access to qa-tool improvements

### For Python Ecosystem
- **Reusable tool**: Any project can benefit from sophisticated QA workflows
- **Best practices**: Promotes interactive QA and comprehensive testing
- **Standardization**: Common approach to project quality assurance

## Timeline Summary

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| Phase 0 | 3-5 days | Repository setup, dependency analysis, configuration design |
| Phase 1 | 1-2 weeks | Extracted, configurable qa-tool package with full feature parity |
| Phase 2 | 1 week | Documentation, comprehensive tests, quality assurance |
| Phase 3 | 1 week | PyPI publication, SAVT migration, CI/CD updates |
| **Total** | **4-5 weeks** | **Standalone qa-tool + migrated SAVT with 100% feature preservation** |

---

This plan transforms SAVT's sophisticated qa.py into a valuable community resource while ensuring zero functionality loss and providing a smooth migration path. The approach follows the proven success pattern from the pytreqt extraction project.
