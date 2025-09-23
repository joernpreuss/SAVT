# Requirements Reports

This folder contains generated reports and analysis about requirements coverage.

## Files

- **`TEST_COVERAGE.md`** - Auto-generated traceability matrix mapping tests to requirements

## Generation

Reports are automatically generated using pytreqt:

```bash
pytreqt coverage  # Generate TEST_COVERAGE.md
pytreqt stats     # Show detailed statistics
pytreqt update    # Update all reports and run tests
```

The reports are kept up-to-date automatically by analyzing test docstrings and mapping them to requirements defined in `spec/REQUIREMENTS.md`.
