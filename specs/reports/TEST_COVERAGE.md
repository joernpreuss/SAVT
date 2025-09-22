# Test Coverage Matrix

This document shows the traceability between functional requirements (FR), business rules (BR), and test cases.

**Last updated**: 2025-09-21

## Coverage Summary

- **Total Requirements**: 29
- **Requirements with Tests**: 11
- **Requirements without Tests**: 18

**Coverage Percentage**: 37.9%

## Requirements Coverage

### BR-3.1: Immutable history - Created items cannot be deleted
**Status**: ❌ **Not Tested**

**Test Cases**: None
⚠️ *This requirement needs test coverage*

### BR-3.2: Referential integrity - Properties maintain references to objects
**Status**: ❌ **Not Tested**

**Test Cases**: None
⚠️ *This requirement needs test coverage*

### BR-3.3: Atomic operations - Veto/unveto operations are transactional
**Status**: ✅ **Tested**

**Test Cases**:
- `test_unveto_idempotency`
- `test_veto_idempotency`

### BR-3.4: Unique constraints - Names must be unique within scope
**Status**: ❌ **Not Tested**

**Test Cases**: None
⚠️ *This requirement needs test coverage*

### FR-1.1: Users can create objects with unique names
**Status**: ✅ **Tested**

**Test Cases**:
- `test_async_item_creation_works`
- `test_create_item_with_feature`

### FR-1.2: Object names must be unique within the system
**Status**: ✅ **Tested**

**Test Cases**:
- `test_async_duplicate_item_prevention`
- `test_create_item_conflict`

### FR-1.3: Objects cannot be deleted (data persistence)
**Status**: ❌ **Not Tested**

**Test Cases**: None
⚠️ *This requirement needs test coverage*

### FR-1.4: Objects display all their associated properties
**Status**: ❌ **Not Tested**

**Test Cases**: None
⚠️ *This requirement needs test coverage*

### FR-1.5: System prevents duplicate object creation (returns 409 error)
**Status**: ✅ **Tested**

**Test Cases**:
- `test_create_item_conflict`

### FR-2.1: Users can create properties with names
**Status**: ✅ **Tested**

**Test Cases**:
- `test_create_feature`
- `test_create_feature_conflict`
- `test_create_feature_without_item`
- `test_create_item_with_feature`

### FR-2.2: Properties can be standalone or associated with objects
**Status**: ✅ **Tested**

**Test Cases**:
- `test_create_feature_without_item`
- `test_create_item_with_feature`
- `test_item_scoped_veto`

### FR-2.3: Property names must be unique within their scope (object or standalone)
**Status**: ❌ **Not Tested**

**Test Cases**: None
⚠️ *This requirement needs test coverage*

### FR-2.4: System prevents duplicate property creation (returns 409 error)
**Status**: ❌ **Not Tested**

**Test Cases**: None
⚠️ *This requirement needs test coverage*

### FR-2.5: Properties cannot be deleted (data persistence)
**Status**: ❌ **Not Tested**

**Test Cases**: None
⚠️ *This requirement needs test coverage*

### FR-3.1: Any user can veto any property
**Status**: ✅ **Tested**

**Test Cases**:
- `test_item_scoped_veto`
- `test_veto_then_unveto_feature`

### FR-3.2: Users can only veto once per property (idempotent operation)
**Status**: ✅ **Tested**

**Test Cases**:
- `test_two_vetos_by_same_user`
- `test_veto_idempotency`

### FR-3.3: Users can unveto their own vetoes
**Status**: ✅ **Tested**

**Test Cases**:
- `test_unveto_idempotency`
- `test_veto_then_unveto_feature`

### FR-3.4: Vetoed properties are visually distinguished (strikethrough)
**Status**: ❌ **Not Tested**

**Test Cases**: None
⚠️ *This requirement needs test coverage*

### FR-3.5: System tracks which users vetoed each property
**Status**: ✅ **Tested**

**Test Cases**:
- `test_item_scoped_veto`
- `test_veto_then_unveto_feature`

### FR-3.6: Veto/unveto operations are immediate and persistent
**Status**: ✅ **Tested**

**Test Cases**:
- `test_unveto_idempotency`
- `test_veto_then_unveto_feature`

### FR-4.1: Properties display as clickable links when not vetoed
**Status**: ❌ **Not Tested**

**Test Cases**: None
⚠️ *This requirement needs test coverage*

### FR-4.2: Vetoed properties display as strikethrough text with "undo" link
**Status**: ❌ **Not Tested**

**Test Cases**: None
⚠️ *This requirement needs test coverage*

### FR-4.3: HTMX provides immediate visual feedback (no page reloads)
**Status**: ❌ **Not Tested**

**Test Cases**: None
⚠️ *This requirement needs test coverage*

### FR-4.4: Forms have graceful fallback for non-JavaScript browsers
**Status**: ❌ **Not Tested**

**Test Cases**: None
⚠️ *This requirement needs test coverage*

### FR-4.5: System shows objects and standalone properties separately
**Status**: ❌ **Not Tested**

**Test Cases**: None
⚠️ *This requirement needs test coverage*

### FR-5.1: All data persists in SQLite database
**Status**: ❌ **Not Tested**

**Test Cases**: None
⚠️ *This requirement needs test coverage*

### FR-5.2: No data is ever deleted (append-only system)
**Status**: ❌ **Not Tested**

**Test Cases**: None
⚠️ *This requirement needs test coverage*

### FR-5.3: System maintains complete audit trail of all actions
**Status**: ❌ **Not Tested**

**Test Cases**: None
⚠️ *This requirement needs test coverage*

### FR-5.4: Database schema supports future extensions
**Status**: ❌ **Not Tested**

**Test Cases**: None
⚠️ *This requirement needs test coverage*

## Requirements Needing Tests

The following requirements have no test coverage:

- **BR-3.1**: Immutable history - Created items cannot be deleted
- **BR-3.2**: Referential integrity - Properties maintain references to objects
- **BR-3.4**: Unique constraints - Names must be unique within scope
- **FR-1.3**: Objects cannot be deleted (data persistence)
- **FR-1.4**: Objects display all their associated properties
- **FR-2.3**: Property names must be unique within their scope (object or standalone)
- **FR-2.4**: System prevents duplicate property creation (returns 409 error)
- **FR-2.5**: Properties cannot be deleted (data persistence)
- **FR-3.4**: Vetoed properties are visually distinguished (strikethrough)
- **FR-4.1**: Properties display as clickable links when not vetoed
- **FR-4.2**: Vetoed properties display as strikethrough text with "undo" link
- **FR-4.3**: HTMX provides immediate visual feedback (no page reloads)
- **FR-4.4**: Forms have graceful fallback for non-JavaScript browsers
- **FR-4.5**: System shows objects and standalone properties separately
- **FR-5.1**: All data persists in SQLite database
- **FR-5.2**: No data is ever deleted (append-only system)
- **FR-5.3**: System maintains complete audit trail of all actions
- **FR-5.4**: Database schema supports future extensions

## Test Statistics

- **Total Test Cases with Requirements**: 24
- **Unique Requirements Tested**: 11
- **Average Tests per Requirement**: 2.2

---

*This file is auto-generated by `pytreqt/generate_coverage_report.py`*
*To update, run: `uv run python pytreqt/generate_coverage_report.py`*
