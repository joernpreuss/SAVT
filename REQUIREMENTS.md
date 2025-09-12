# SAVT - System Requirements & Specifications

This document defines the functional requirements, business logic, and system behavior for the Suggestion And Veto Tool (SAVT). This is intended for developers, AI assistants, and anyone needing to understand what the system should do (not just how it's implemented).

## System Overview

SAVT is a collaborative decision-making tool that enables groups to reach consensus through suggestions and vetoes. The core concept is democratic: anyone can suggest options, but anyone can also veto options they don't want.

## Core Concepts

### Objects
- **Definition**: Items that require group decisions (e.g., pizzas, events, purchases)
- **Properties**: Each object has a name and unique ID
- **Creation**: Any user can create objects
- **Scope**: Objects serve as containers for related properties

### Properties
- **Definition**: Specific options or features for objects (e.g., pizza toppings, event locations)
- **Types**:
  - **Object properties**: Belong to a specific object
  - **Standalone properties**: Independent options not tied to any object
- **Creation**: Any user can create properties
- **State**: Each property can be active or vetoed

### Users
- **Identity**: Currently anonymous (identified by "anonymous" or custom usernames)
- **Permissions**: All users have equal rights (create, veto, unveto)
- **No authentication**: System assumes trustworthy users

### Vetoes
- **Definition**: A user's rejection of a specific property
- **Scope**: User-specific (each user can veto independently)
- **Storage**: Tracked as JSON array of usernames per property
- **Reversibility**: Users can "unveto" (remove their veto)

## Functional Requirements

### FR-1: Object Management
- **FR-1.1**: Users can create objects with unique names
- **FR-1.2**: Object names must be unique within the system
- **FR-1.3**: Objects cannot be deleted (data persistence)
- **FR-1.4**: Objects display all their associated properties
- **FR-1.5**: System prevents duplicate object creation (returns 409 error)

### FR-2: Property Management
- **FR-2.1**: Users can create properties with names
- **FR-2.2**: Properties can be standalone or associated with objects
- **FR-2.3**: Property names must be unique within their scope (object or standalone)
- **FR-2.4**: System prevents duplicate property creation (returns 409 error)
- **FR-2.5**: Properties cannot be deleted (data persistence)

### FR-3: Veto System
- **FR-3.1**: Any user can veto any property
- **FR-3.2**: Users can only veto once per property (idempotent operation)
- **FR-3.3**: Users can unveto their own vetoes
- **FR-3.4**: Vetoed properties are visually distinguished (strikethrough)
- **FR-3.5**: System tracks which users vetoed each property
- **FR-3.6**: Veto/unveto operations are immediate and persistent

### FR-4: User Interface Behavior
- **FR-4.1**: Properties display as clickable links when not vetoed
- **FR-4.2**: Vetoed properties display as strikethrough text with "undo" link
- **FR-4.3**: HTMX provides immediate visual feedback (no page reloads)
- **FR-4.4**: Forms have graceful fallback for non-JavaScript browsers
- **FR-4.5**: System shows objects and standalone properties separately

### FR-5: Data Persistence
- **FR-5.1**: All data persists in SQLite database
- **FR-5.2**: No data is ever deleted (append-only system)
- **FR-5.3**: System maintains complete audit trail of all actions
- **FR-5.4**: Database schema supports future extensions

## Business Rules

### BR-1: Consensus Model
- **No threshold**: There's no minimum number of vetoes to reject a property
- **Individual choice**: Each user decides for themselves what to veto
- **No majority rule**: System doesn't automatically hide items with many vetoes
- **Transparency**: All vetoes are visible to all users

### BR-2: User Equality
- **Equal rights**: All users can create, veto, and unveto
- **No hierarchy**: No admin/moderator roles
- **No ownership**: Users don't "own" their created items
- **Anonymous operation**: No user authentication required

### BR-3: Data Integrity
- **Immutable history**: Created items cannot be deleted
- **Referential integrity**: Properties maintain references to objects
- **Unique constraints**: Names must be unique within scope
- **Atomic operations**: Veto/unveto operations are transactional

## User Stories

### Epic: Basic Usage
- **As a group member**, I want to create objects so that we can organize our decision-making
- **As a group member**, I want to suggest properties so that others can consider my ideas
- **As a group member**, I want to veto properties I don't want so that my preferences are heard
- **As a group member**, I want to change my mind and unveto so that I can adjust my preferences

### Epic: Pizza Ordering (Original Use Case)
- **As a pizza group**, we want to create different pizza objects so we can order multiple pizzas
- **As a group member**, I want to suggest toppings so others know my preferences
- **As someone with dietary restrictions**, I want to veto toppings I can't eat so they're not included
- **As a group**, we want to see which toppings are acceptable to everyone

### Epic: General Decision Making
- **As a project team**, we want to vote on features so we prioritize the right work
- **As an event planner**, I want to collect venue preferences so we choose a location everyone can attend
- **As a family**, we want to decide on vacation activities so everyone enjoys the trip

## Non-Functional Requirements

### NFR-1: Performance
- **Response time**: UI interactions should feel instant (< 200ms)
- **Scalability**: Should handle small groups (2-20 people) efficiently
- **Database**: SQLite sufficient for expected load

### NFR-2: Usability
- **Learning curve**: Should be intuitive without documentation
- **Accessibility**: Works with standard web browsers
- **Mobile**: Should work on mobile devices (responsive design)

### NFR-3: Reliability
- **Data safety**: No data loss under normal operation
- **Error handling**: Graceful handling of duplicate submissions
- **Fallback**: Works without JavaScript (progressive enhancement)

### NFR-4: Maintainability
- **Code clarity**: Pure Python approach for simplicity
- **Testing**: Comprehensive test coverage for business logic
- **Configuration**: Terminology should be configurable for different use cases

## Future Considerations

### Potential Enhancements
- **User authentication**: Track individual users vs anonymous
- **Threshold rules**: Configure veto thresholds for automatic rejection
- **Time limits**: Set deadlines for decision-making
- **Categories**: Group properties by type/category
- **Export**: Generate summaries or reports of decisions
- **Real-time**: WebSocket updates for multi-user sessions

### Known Limitations
- **No user management**: Everyone is "anonymous"
- **No deletion**: Items accumulate forever
- **No moderation**: No way to handle abuse/spam
- **No analytics**: Limited insights into decision patterns
- **Single instance**: Not designed for multi-tenant usage

## System Boundaries

### In Scope
- Property suggestion and veto management
- Simple web interface for basic operations
- Data persistence and integrity
- Configurable terminology

### Out of Scope
- User authentication/authorization
- Real-time collaboration features
- Advanced analytics or reporting
- Mobile native apps
- Multi-language support
- Integration with external systems

## Success Criteria

A successful SAVT deployment should:
1. **Enable consensus**: Groups can identify mutually acceptable options
2. **Be intuitive**: New users understand the interface immediately
3. **Preserve choice**: All suggestions are captured and can be reconsidered
4. **Scale appropriately**: Handle expected user load without performance issues
5. **Maintain data**: No loss of decisions or preferences over time

This document should be updated as requirements evolve or new use cases emerge.
