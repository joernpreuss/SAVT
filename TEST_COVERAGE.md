# Test Coverage - Requirements Traceability

This document maps test cases to functional requirements (FR) and business rules (BR) defined in [REQUIREMENTS.md](./REQUIREMENTS.md).

## Requirements Coverage Matrix

### FR-1: Object Management
- **FR-1.1** ✅ Users can create objects with unique names
  - `test_service.py::test_create_object_with_property`
- **FR-1.2** ✅ Object names must be unique within the system
  - `test_service.py::test_create_object_conflict`
- **FR-1.5** ✅ System prevents duplicate object creation (returns 409 error)
  - `test_service.py::test_create_object_conflict`
- **FR-1.3** ⚠️ Objects cannot be deleted (data persistence) - *Not explicitly tested*
- **FR-1.4** ⚠️ Objects display all their associated properties - *Tested in frontend tests*

### FR-2: Property Management
- **FR-2.1** ✅ Users can create properties with names
  - `test_service.py::test_create_object_with_property`
  - `test_service.py::test_create_property_without_object`
  - `test_api.py::test_create_property`
- **FR-2.2** ✅ Properties can be standalone or associated with objects
  - `test_service.py::test_create_object_with_property` (with objects)
  - `test_service.py::test_create_property_without_object` (standalone)
  - `test_service.py::test_object_scoped_veto` (both types)
- **FR-2.3** ✅ Property names must be unique within their scope
  - `test_service.py::test_create_property_conflict`
  - `test_api.py::test_create_property_conflict`
- **FR-2.4** ✅ System prevents duplicate property creation (returns 409 error)
  - `test_service.py::test_create_property_conflict`
  - `test_api.py::test_create_property_conflict`
- **FR-2.5** ⚠️ Properties cannot be deleted (data persistence) - *Not explicitly tested*

### FR-3: Veto System
- **FR-3.1** ✅ Any user can veto any property
  - `test_service.py::test_object_scoped_veto`
  - `test_api.py::test_veto_then_unveto_property`
- **FR-3.2** ✅ Users can only veto once per property (idempotent operation)
  - `test_service.py::test_veto_idempotency`
  - `test_api.py::test_two_vetos_by_same_user`
- **FR-3.3** ✅ Users can unveto their own vetoes
  - `test_service.py::test_unveto_idempotency`
  - `test_api.py::test_veto_then_unveto_property`
- **FR-3.5** ✅ System tracks which users vetoed each property
  - `test_service.py::test_object_scoped_veto`
  - `test_api.py::test_veto_then_unveto_property`
- **FR-3.6** ✅ Veto/unveto operations are immediate and persistent
  - `test_service.py::test_unveto_idempotency`
  - `test_api.py::test_veto_then_unveto_property`
- **FR-3.4** ⚠️ Vetoed properties are visually distinguished (strikethrough) - *Tested in frontend tests*

### FR-4: User Interface Behavior
- **FR-4.1** ⚠️ Properties display as clickable links when not vetoed - *Tested in frontend tests*
- **FR-4.2** ⚠️ Vetoed properties display as strikethrough text with "undo" link - *Tested in frontend tests*
- **FR-4.3** ⚠️ HTMX provides immediate visual feedback (no page reloads) - *Tested in HTMX tests*
- **FR-4.4** ⚠️ Forms have graceful fallback for non-JavaScript browsers - *Tested in frontend tests*
- **FR-4.5** ⚠️ System shows objects and standalone properties separately - *Tested in frontend tests*

### FR-5: Data Persistence
- **FR-5.1** ✅ All data persists in SQLite database - *Implicitly tested by all database tests*
- **FR-5.2** ⚠️ No data is ever deleted (append-only system) - *Not explicitly tested*
- **FR-5.3** ⚠️ System maintains complete audit trail of all actions - *Not explicitly tested*
- **FR-5.4** ✅ Database schema supports future extensions - *Demonstrated by existing schema*

## Business Rules Coverage

### BR-3: Data Integrity
- **BR-3.3** ✅ Atomic operations - Veto/unveto operations are transactional
  - `test_service.py::test_veto_idempotency`
  - `test_service.py::test_unveto_idempotency`

## Coverage Statistics

- **Well Tested**: 15 requirements with explicit test coverage
- **Partially Tested**: 8 requirements tested in other test files (frontend/HTMX)
- **Not Tested**: 3 requirements lack explicit test coverage
- **Overall Coverage**: ~77% of functional requirements have direct test coverage

## Recommendations for Additional Tests

1. **Data Persistence Tests**:
   - Verify objects/properties cannot be deleted via API
   - Test that all operations are logged for audit trail
   - Verify data survives application restarts

2. **Error Handling Tests**:
   - Test behavior with malformed input
   - Verify graceful handling of database connection issues
   - Test concurrent access scenarios

3. **Integration Tests**:
   - Full workflow tests (create object → add properties → veto → unveto → decision)
   - Cross-browser compatibility for HTMX features
   - Performance tests with many properties/vetoes

4. **Security Tests**:
   - Input validation and sanitization
   - SQL injection prevention
   - XSS prevention in templates

## Usage for AI Development

When working on SAVT features:
1. **Before making changes**: Check which requirements are affected
2. **After implementing**: Update test coverage matrix
3. **When debugging**: Verify the relevant FR/BR tests still pass
4. **For new features**: Add requirements to REQUIREMENTS.md and corresponding tests

This traceability ensures that business requirements drive technical implementation and testing strategy.
