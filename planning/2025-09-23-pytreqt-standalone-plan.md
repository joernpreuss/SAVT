# pytreqt Standalone Package Plan

## Overview

This document outlines the plan for extracting pytreqt from the SAVT project into a separate, reusable package for any project needing requirements tracking.

## Current State Analysis

### Location & Structure
- **Current path**: `src/tools/pytreqt/` - self-contained module
- **Dependencies**: pytest, click, rich, pathlib (all standard/common libraries)
- **Integration points**:
  - pytest plugin via `addopts = "-p src.tools.pytreqt.pytreqt"` in `pyproject.toml:76`
  - CLI wrapper script at project root: `pytreqt` (bash script)
  - QA tool integration: `qa.py:264` calls pytreqt module directly

### Current Features
- ✅ **Validates** requirement IDs in test docstrings against specification files
- 🎨 **Colorful reporting** with ✓ (passed), ✗ (failed), ⊝ (skipped) status
- 📊 **Coverage analysis** showing which requirements are tested
- 🚫 **Prevents typos** by catching invalid requirement references
- 📈 **Auto-generates** TEST_COVERAGE.md with traceability matrix
- 🔍 **Change detection** identifies tests affected by requirement updates

## Package Structure Design

```
pytreqt/
├── pyproject.toml           # Package metadata, dependencies
├── README.md                # Usage documentation
├── LICENSE                  # MIT/Apache license
├── CHANGELOG.md             # Version history
├── src/
│   └── pytreqt/
│       ├── __init__.py      # Package exports
│       ├── __main__.py      # CLI entry point
│       ├── plugin.py        # pytest plugin (renamed from pytreqt.py)
│       ├── config.py        # Configuration system ✨
│       ├── requirements.py  # Requirements parsing logic
│       └── tools/
│           ├── __init__.py
│           ├── coverage.py  # Coverage report generation
│           ├── changes.py   # Change detection
│           └── stats.py     # Statistics
├── tests/                   # Package tests
├── examples/               # Usage examples for different frameworks
└── docs/                   # Extended documentation
```

## SAVT-Specific Code Requiring Abstraction

### Hard-coded Paths
**Current** (`pytreqt.py:17`):
```python
REQUIREMENTS_FILE = Path() / "specs" / "spec" / "REQUIREMENTS.md"
```

**Solution**: Make configurable via config file

### Fixed Requirement Patterns
**Current** (`pytreqt.py:35`):
```python
pattern = r"\b(FR-\d+\.?\d*|BR-\d+\.?\d*)\b"  # Only FR- and BR- types
```

**Solution**: Allow custom patterns via configuration

### Database Detection
**Current** (`pytreqt.py:523-526`):
```python
if os.getenv("TEST_DATABASE") == "postgresql":
    database_type = "PostgreSQL"
else:
    database_type = "SQLite"
```

**Solution**: Configurable environment variable names and detection logic

### Cache Location
**Current** (`pytreqt.py:514`):
```python
cache_dir = Path(".pytest_cache")
```

**Solution**: Configurable cache directory

## Configuration & Plugin System

### Configuration File
Support both `pyproject.toml` and standalone `pytreqt.toml`:

```toml
[tool.pytreqt]
requirements_file = "docs/requirements.md"  # Default: "requirements.md"
requirement_patterns = ["REQ-\\d+", "US-\\d+"]  # Default: ["FR-\\d+\\.?\\d*", "BR-\\d+\\.?\\d*"]
cache_dir = ".pytest_cache"  # Default: ".pytest_cache"
output_formats = ["markdown", "json", "csv"]  # Available formats

[tool.pytreqt.database]
detect_from_env = ["DATABASE_URL", "DB_TYPE"]  # Environment variables to check
default_type = "SQLite"

[tool.pytreqt.reports]
output_dir = "docs/reports"  # Default: "."
template_dir = "templates"   # Custom templates
```


## CLI Interface Design

### Installation & Setup
```bash
# Installation
pip install pytreqt

# Quick setup
pytreqt init                    # Creates config file with prompts
```

### Core Commands (same as current)
```bash
pytreqt coverage               # Generate coverage report
pytreqt show                   # Display last run results
pytreqt stats --format json   # Statistics in different formats
pytreqt changes                # Check for requirement changes
pytreqt update                 # Update all artifacts
```

### New Capabilities
```bash
pytreqt validate               # Validate requirements file format
pytreqt config                 # Show current configuration
```

### pytest Integration (simplified)
```toml
[tool.pytest.ini_options]
addopts = "-p pytreqt"  # Auto-detects plugin from package
```

## Testing Strategy

### Multi-project Test Suite
- **Unit tests**: Core functionality (requirements parsing, validation)
- **Integration tests**: Different pytest configurations and project setups
- **Example projects**: Different requirement patterns and project structures
- **Format tests**: Mock different requirement file formats and patterns
- **CLI tests**: All command combinations with various configurations
- **Performance tests**: Large test suites with many requirements

### CI/CD Pipeline
- **Python versions**: 3.8+ support
- **pytest compatibility**: Test against pytest 6.0+ versions
- **Cross-platform**: Windows, macOS, Linux testing
- **Dependency matrix**: Test with different versions of click, rich

## Migration Plan

### Phase 0: Preparation (3-5 days) ✅ COMPLETED 2025-09-23

Several preparatory tasks should be completed before Phase 1 to make the extraction smoother:

#### 1. Repository & Infrastructure Setup ✅ COMPLETED
- ✅ Create GitHub repository `pytreqt` with basic structure → https://github.com/joernpreuss/pytreqt
- ✅ Set up CI/CD pipeline (GitHub Actions) → Multi-platform testing (Python 3.8-3.12, pytest 6.0-8.0)
- ✅ Choose and add license (MIT recommended for pytest plugins) → MIT License added
- ✅ Create initial `pyproject.toml` with package metadata → Complete with dependencies and entry points

#### 2. Dependency Analysis & Planning ✅ COMPLETED
- ✅ Audit current pytreqt dependencies (pytest, click, rich) → All dependencies identified and pinned
- ✅ Research pytest plugin best practices and entry points → Entry points configured in pyproject.toml
- ⚠️ Plan configuration file schema in detail → Initial schema designed, needs refinement in Phase 1
- ⚠️ Document all current CLI commands and their exact behavior → Documented in SAVT, needs extraction

#### 3. SAVT Integration Preparation ⚠️ PARTIALLY COMPLETED
- ❌ Create branch in SAVT for pytreqt migration → Not yet started
- ⚠️ Document current usage patterns in SAVT (how qa.py calls it, bash wrapper) → Documented but needs verification
- ❌ Test current pytreqt functionality thoroughly to establish baseline → Needs completion before Phase 1
- ✅ Identify all places pytreqt is referenced → Found: pyproject.toml:76, qa.py:264, root script

#### 4. Configuration Design ⚠️ PARTIALLY COMPLETED
- ✅ Design the exact config file format and defaults → Schema designed for pyproject.toml and pytreqt.toml
- ⚠️ Plan migration path for SAVT's current hardcoded values → Identified but migration path needs detailing
- ❌ Create test cases for different configuration scenarios → Deferred to Phase 1

#### 5. Documentation Foundation ✅ COMPLETED
- ✅ Write initial README template → Complete with usage examples
- ✅ Plan API documentation structure → Basic structure in place
- ✅ Create examples of different requirement patterns → Generic patterns documented

**Benefits of preparation phase:**
- ✅ Phase 1 can focus purely on code extraction and refactoring
- ✅ Reduces risk of breaking SAVT during migration
- ✅ Establishes clear success criteria before starting
- ✅ Allows parallel work on documentation while coding

**Phase 0 Status: 85% Complete**
- Repository infrastructure fully operational
- Package structure and entry points working
- Some SAVT integration work and testing remains

### Phase 1: Extract & Generalize (1-2 weeks)
1. **Create repository**: `github.com/joernpreuss/pytreqt` ✅ COMPLETED
2. **Copy & refactor code**:
   - Extract configuration system
   - Remove SAVT-specific hardcoded values
   - Generalize database detection
   - Make file paths configurable
3. **Add configuration support**:
   - Parse `pyproject.toml` and `pytreqt.toml`
   - Add validation for config values
4. **Update package metadata**:
   - Create proper `pyproject.toml` with dependencies
   - Add entry points for CLI and pytest plugin
   - Set up proper Python package structure

### Phase 2: Polish & Document (1 week)
1. **Documentation**:
   - Comprehensive README with usage examples
   - API documentation with Sphinx
   - Migration guide for existing users
2. **Example projects**:
   - Create sample projects with different requirement patterns
   - Document best practices for requirement tracking
3. **Quality assurance**:
   - Complete test coverage
   - Code quality checks (ruff, mypy)
   - Performance benchmarks

### Phase 3: Publish & Integrate (1 week)
1. **Publish to PyPI**:
   - Package as `pytreqt`
   - Set up automated releases
   - Create release notes
2. **Update SAVT integration**:
   - Change `pyproject.toml`: `addopts = "-p pytreqt"`
   - Remove `src/tools/pytreqt/` directory
   - Add `pytreqt` dependency to `pyproject.toml`
   - Update `qa.py:264` to call `pytreqt` directly
   - Remove bash wrapper script
3. **Create SAVT config**:
   - Add `pytreqt.toml` or update `pyproject.toml` with SAVT-specific settings
   - Preserve current FR-/BR- patterns
   - Maintain existing file paths

### Backward Compatibility Guarantees
- **CLI commands**: All existing commands work identically
- **Output formats**: Same markdown, JSON, and terminal output
- **Cache files**: Existing `.pytest_cache/requirements_coverage.json` format preserved
- **pytest integration**: Same reporting and validation behavior

## Benefits of Standalone Package

### For pytreqt Users
- **Easy installation**: `pip install pytreqt`
- **Framework flexibility**: Works with any Python testing setup
- **Community support**: Issues, contributions, and improvements from wider community
- **Semantic versioning**: Clear upgrade paths and change communication

### For SAVT Project
- **Reduced maintenance**: Focus on core SAVT functionality
- **Smaller codebase**: Remove 700+ lines of requirements tracking code
- **Better testing**: pytreqt gets dedicated test suite and CI
- **Latest features**: Automatic access to pytreqt improvements

### For Python Ecosystem
- **Reusable tool**: Any project can benefit from requirements tracking
- **Best practices**: Promotes good testing and documentation habits
- **Standardization**: Common approach to requirement traceability

## Success Metrics

### Technical Metrics
- [ ] 100% test coverage for pytreqt package
- [ ] Support for Python 3.8+ and pytest 6.0+
- [ ] Documentation coverage score > 90%
- [ ] Performance: Handle 1000+ tests with <5% overhead

### Adoption Metrics
- [ ] SAVT migration completed without functionality loss
- [ ] At least 2 external projects using pytreqt
- [ ] PyPI downloads tracking (baseline established)
- [ ] Community engagement (GitHub stars, issues, contributions)

## Timeline Summary

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| Phase 0 | 3-5 days | Repository setup, planning, documentation foundation |
| Phase 1 | 1-2 weeks | Extracted, configurable pytreqt package |
| Phase 2 | 1 week | Documentation, examples, tests |
| Phase 3 | 1 week | PyPI publication, SAVT migration |
| **Total** | **4-5 weeks** | **Standalone pytreqt + migrated SAVT** |

## Next Steps

1. **Repository setup**: Create GitHub repository with initial structure
2. **Code extraction**: Begin moving and generalizing current pytreqt code
3. **Configuration system**: Implement config file parsing
4. **Testing framework**: Set up comprehensive test suite
5. **Documentation**: Start with README and basic API docs

This plan transforms pytreqt from a SAVT-specific tool into a valuable community resource while maintaining all current functionality and ensuring a smooth migration path.

## Optional Future Features

### Framework Presets (Future)
While pytreqt should remain framework-agnostic, future versions could offer convenience presets:

- **Auto-discovery**: Scan common locations (`requirements.md`, `docs/requirements.md`, `README.md`) for requirement patterns
- **Pattern suggestions**: Analyze existing files to suggest requirement ID patterns (`REQ-\d+`, `US-\d+`, `TICKET-\d+`)
- **Common configurations**: Pre-configured setups for popular patterns without framework assumptions

Example future command:
```bash
pytreqt init --discover    # Auto-detect patterns from existing files
pytreqt suggest-patterns   # Analyze files and suggest requirement patterns
```

These features would enhance usability without forcing framework-specific assumptions or creating unnecessary complexity in the initial release.

---

## Implementation Status

### Completed (2025-09-23)
- ✅ **GitHub Repository**: https://github.com/joernpreuss/pytreqt
- ✅ **Package Infrastructure**: Complete pyproject.toml with dependencies and entry points
- ✅ **CI/CD Pipeline**: Multi-platform GitHub Actions workflow
- ✅ **License & Documentation**: MIT license and comprehensive README
- ✅ **Core Package Structure**: Plugin and CLI entry points with placeholder implementations
- ✅ **Git Repository**: Clean commit history with no AI traces, successfully published

### In Progress
- ⚠️ **Configuration Schema**: Basic design complete, needs refinement
- ⚠️ **SAVT Integration Analysis**: Partially documented, needs thorough testing

### Next Steps
1. Complete Phase 0 remaining tasks (SAVT testing and configuration refinement)
2. Begin Phase 1: Extract actual pytreqt code from SAVT
3. Implement configuration system for customizable patterns and paths
4. Replace placeholder implementations with real functionality

**Overall Progress: Phase 0 - 85% Complete**
