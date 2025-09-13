# Specification Documentation

This folder contains the source requirements specification for SAVT.

## Files

- **`REQUIREMENTS.md`** - Master requirements document defining all functional requirements (FR) and business rules (BR)

This is the **source of truth** for what the system should do. All test requirements validation is done against this document.

## Adding Requirements

1. Add new requirements using format: `- **FR-X.Y**: Description`
2. Reference them in test docstrings
3. Validation ensures tests only reference requirements that exist here
