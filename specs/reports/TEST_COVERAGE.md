# Test Coverage Matrix

This document shows the traceability between functional requirements (FR), business rules (BR), and test cases.

**Last updated**: 2025-09-23

## Coverage Summary

- **Total Requirements**: 29
- **Requirements with Tests**: 28
- **Requirements without Tests**: 1

**Coverage Percentage**: 96.6%

## Requirements Coverage

### BR-3.1: Immutable history - Created items cannot be deleted
**Status**: ✅ **Tested**

**Test Cases**:
- `test_data_immutability`
- `test_delete_item`
- `test_item_data_immutability`

### BR-3.2: Referential integrity - Properties maintain references to objects
**Status**: ✅ **Tested**

**Test Cases**:
- `test_referential_integrity`

### BR-3.3: Atomic operations - Veto/unveto operations are transactional
**Status**: ✅ **Tested**

**Test Cases**:
- `test_unveto_idempotency`
- `test_veto_idempotency`

### BR-3.4: Unique constraints - Names must be unique within scope
**Status**: ✅ **Tested**

**Test Cases**:
- `test_unique_constraints`

### FR-1.1: Users can create objects with unique names
**Status**: ✅ **Tested**

**Test Cases**:
- `test_async_item_creation_works`
- `test_create_item`
- `test_create_item_with_feature`
- `test_create_item_with_user`

### FR-1.2: Object names must be unique within the system
**Status**: ✅ **Tested**

**Test Cases**:
- `test_async_duplicate_item_prevention`
- `test_create_item`
- `test_create_item_conflict`
- `test_create_item_duplicate_conflict`

### FR-1.3: Objects cannot be deleted (data persistence)
**Status**: ✅ **Tested**

**Test Cases**:
- `test_delete_item`
- `test_item_data_immutability`

### FR-1.4: Objects display all their associated properties
**Status**: ✅ **Tested**

**Test Cases**:
- `test_get_item_by_name`
- `test_item_feature_relationship`
- `test_list_items_empty`
- `test_list_items_with_data`
- `test_referential_integrity`

### FR-1.5: System prevents duplicate object creation (returns 409 error)
**Status**: ✅ **Tested**

**Test Cases**:
- `test_create_item_conflict`
- `test_create_item_duplicate_conflict`

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
- `test_item_feature_relationship`
- `test_item_scoped_veto`

### FR-2.3: Property names must be unique within their scope (object or standalone)
**Status**: ✅ **Tested**

**Test Cases**:
- `test_property_duplicate_prevention`

### FR-2.4: System prevents duplicate property creation (returns 409 error)
**Status**: ✅ **Tested**

**Test Cases**:
- `test_property_duplicate_prevention`

### FR-2.5: Properties cannot be deleted (data persistence)
**Status**: ✅ **Tested**

**Test Cases**:
- `test_data_immutability`

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
**Status**: ✅ **Tested**

**Test Cases**:
- `test_vetoed_properties_visual_distinction`

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
**Status**: ✅ **Tested**

**Test Cases**:
- `test_vetoed_properties_visual_distinction`

### FR-4.3: HTMX provides immediate visual feedback (no page reloads)
**Status**: ✅ **Tested**

**Test Cases**:
- `test_htmx_immediate_feedback`

### FR-4.4: Forms have graceful fallback for non-JavaScript browsers
**Status**: ✅ **Tested**

**Test Cases**:
- `test_non_javascript_graceful_fallback`

### FR-4.5: System shows objects and standalone properties separately
**Status**: ✅ **Tested**

**Test Cases**:
- `test_objects_and_properties_separate_display`

### FR-5.1: All data persists in SQLite database
**Status**: ✅ **Tested**

**Test Cases**:
- `test_database_persistence`

### FR-5.2: No data is ever deleted (append-only system)
**Status**: ✅ **Tested**

**Test Cases**:
- `test_data_immutability`
- `test_item_data_immutability`

### FR-5.3: System maintains complete audit trail of all actions
**Status**: ✅ **Tested**

**Test Cases**:
- `test_database_persistence`
- `test_item_data_immutability`

### FR-5.4: Database schema supports future extensions
**Status**: ✅ **Tested**

**Test Cases**:
- `test_database_schema_extensibility`

## Requirements Needing Tests

The following requirements have no test coverage:

- **FR-4.1**: Properties display as clickable links when not vetoed

## Test Statistics

- **Total Test Cases with Requirements**: 56
- **Unique Requirements Tested**: 28
- **Average Tests per Requirement**: 2.0

---

*This file is auto-generated by `pytreqt/generate_coverage_report.py`*
*To update, run: `uv run python pytreqt/generate_coverage_report.py`*
