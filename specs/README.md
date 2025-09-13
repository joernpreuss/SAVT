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

pytest_requirements/    # Tooling (future separate package)
├── pytest_requirements.py    # Validation plugin
├── __init__.py
└── README.md
```

## Workflow

1. **Define requirements** in `spec/REQUIREMENTS.md`
2. **Reference in tests** using docstring format
3. **Auto-validate** with `pytest_requirements/` tooling
4. **Generate reports** in `reports/` (planned)

## Usage

Run tests with requirements coverage:
```bash
uv run pytest -v
```
