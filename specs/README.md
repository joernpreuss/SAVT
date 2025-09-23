# Specifications Management

This folder contains all functional requirements (FR) and business rules (BR) related files for the SAVT project.

## Structure

```
specs/
├── spec/           # Input: Source specifications
│   ├── REQUIREMENTS.md    # Master requirements document
│   └── README.md
└── reports/        # Output: Generated reports
    ├── TEST_COVERAGE.md   # Coverage matrix
    └── README.md
```

## Workflow

1. **Define requirements** in `spec/REQUIREMENTS.md`
2. **Reference in tests** using docstring format
3. **Auto-validate** with pytreqt plugin
4. **Generate reports** in `reports/`

## Usage

**View requirements coverage:**
```bash
uv run pytest -v  # Shows coverage in test output
pytreqt show       # Rich-formatted coverage from last run
```

**Generate coverage reports:**
```bash
pytreqt coverage  # Generate TEST_COVERAGE.md
pytreqt stats     # Show detailed statistics
```

**Validate requirements:**
```bash
pytreqt validate  # Check requirements file format
pytreqt changes   # Detect requirement changes
```

## Configuration

Requirements tracking is configured via `pytreqt.toml` in the project root. This configures:
- Requirements file location (`specs/spec/REQUIREMENTS.md`)
- Requirement ID patterns (FR-*, BR-*)
- Report output directory (`specs/reports/`)
