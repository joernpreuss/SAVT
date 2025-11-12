# SSE Multiplayer Design

**Status**: In Development (2025-11-12)

## Overview

SAVT implements real-time multiplayer collaboration using Server-Sent Events (SSE) to broadcast feature changes to all connected clients. When one user performs an action (veto, unveto, create, delete), all other users see the update immediately without manual page refresh.

## Design Philosophy

**Real-Time Collaboration**: Extend SAVT's trust-based user system with live updates:
- All users see changes immediately as they happen
- No polling overhead - server pushes updates only when needed
- Seamless HTMX integration - no JavaScript frameworks required
- Unidirectional communication (server → clients) matches the use case

**Minimal Complexity**: Use the simplest technology that works:
- SSE instead of WebSockets (HTTP-based, auto-reconnect)
- Native HTMX support with `hx-sse` attribute
- Event broadcasting only when state changes
- No persistent connection state on server

## Architecture

### Technology Stack

- **SSE Protocol**: HTTP-based, unidirectional server → client streaming
- **sse-starlette**: FastAPI-compatible SSE library
- **HTMX SSE Extension**: Native `hx-sse` support for DOM updates
- **In-Memory Event Bus**: Simple broadcast mechanism (no Redis/message queue needed for single-server deployments)

### Event Flow

```
User A                  Server                  User B, C, D...
  │                       │                          │
  │──POST /veto──────────>│                          │
  │                       │                          │
  │<────200 OK────────────│                          │
  │                       │                          │
  │                       │──SSE: feature-update────>│
  │                       │                          │
  │                       │                          │ HTMX swaps DOM
  │                       │                          │ Update visible
```

### Components

#### 1. Event Broadcaster Service (`src/application/event_broadcaster.py`)

```python
from asyncio import Queue
from dataclasses import dataclass
from typing import AsyncIterator

@dataclass
class FeatureEvent:
    """Event representing a feature state change."""
    event_type: str  # "feature-updated", "feature-created", "feature-deleted"
    feature_id: int
    item_id: int | None = None
    timestamp: float = field(default_factory=time.time)

class EventBroadcaster:
    """In-memory event broadcaster for SSE."""

    def __init__(self):
        self._subscribers: list[Queue[FeatureEvent]] = []

    async def subscribe(self) -> AsyncIterator[FeatureEvent]:
        """Subscribe to events. Yields FeatureEvent objects."""
        queue: Queue[FeatureEvent] = Queue()
        self._subscribers.append(queue)
        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            self._subscribers.remove(queue)

    async def broadcast(self, event: FeatureEvent) -> None:
        """Broadcast event to all subscribers."""
        for queue in self._subscribers:
            await queue.put(event)

# Global singleton instance
broadcaster = EventBroadcaster()
```

#### 2. SSE Endpoint (`src/presentation/api_routes.py`)

```python
from sse_starlette.sse import EventSourceResponse
from fastapi import Request

@router.get("/events")
async def event_stream(request: Request) -> EventSourceResponse:
    """
    SSE endpoint for real-time feature updates.

    Returns Server-Sent Events stream that pushes updates when features change.
    Clients should connect using HTMX hx-sse attribute.

    Event types:
    - feature-updated: Feature was vetoed/unvetoed/modified
    - feature-created: New feature was added
    - feature-deleted: Feature was removed

    Each event includes HTML fragment for HTMX to swap into DOM.
    """
    async def event_generator():
        async for event in broadcaster.subscribe():
            if await request.is_disconnected():
                break

            # Render HTML fragment for this feature
            html = await _render_feature_fragment(event)

            yield {
                "event": event.event_type,
                "id": f"{event.feature_id}-{event.timestamp}",
                "data": html,
            }

    return EventSourceResponse(event_generator())
```

#### 3. Feature Service Integration

Modify `src/application/feature_service.py` to broadcast events:

```python
from src.application.event_broadcaster import broadcaster, FeatureEvent

async def veto_feature(
    session: Session,
    feature_id: int,
    username: str,
    item_id: int | None = None
) -> Feature:
    """Veto a feature and broadcast update."""
    feature = _veto_feature_sync(session, feature_id, username, item_id)

    # Broadcast to all connected clients
    await broadcaster.broadcast(FeatureEvent(
        event_type="feature-updated",
        feature_id=feature_id,
        item_id=item_id
    ))

    return feature
```

#### 4. HTMX Template Integration (`templates/properties.html`)

```html
<!-- SSE Connection -->
<div hx-ext="sse"
     sse-connect="/api/v1/events"
     sse-swap="feature-updated"
     hx-swap="none">

  <!-- Feature lists will be updated via targeted swaps -->
  <div id="global-features-list">
    {% for feature in global_features %}
      <div id="feature-{{ feature.id }}"
           sse-swap="feature-updated"
           hx-swap="outerHTML">
        {{ macros.standalone_feature_item(feature, username) }}
      </div>
    {% endfor %}
  </div>

  <!-- Item features similarly -->
  {% for item in items %}
    <div id="item-{{ item.id }}-features">
      {% for feature in item.features %}
        <div id="item-{{ item.id }}-feature-{{ feature.id }}"
             sse-swap="feature-updated"
             hx-swap="outerHTML">
          {{ macros.item_feature_item_with_move(item, feature, items, username) }}
        </div>
      {% endfor %}
    </div>
  {% endfor %}
</div>
```

### Data Flow

#### Veto Operation Example

1. **User A clicks "Veto" button**
   - HTMX sends POST to `/user/Alice/veto/feature/123`
   - Server processes veto in `feature_service.veto_feature()`

2. **Server broadcasts event**
   - `broadcaster.broadcast(FeatureEvent("feature-updated", 123))`
   - Event queued for all connected SSE clients

3. **All clients receive SSE event**
   - HTMX receives event on `sse-swap="feature-updated"`
   - Matches target element by ID: `#feature-123`
   - Swaps HTML fragment into DOM

4. **Result**
   - User A sees immediate response from their POST
   - Users B, C, D see live update via SSE
   - No manual refresh needed

### Rendering HTML Fragments

Helper function to render feature HTML for SSE events:

```python
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")

async def _render_feature_fragment(event: FeatureEvent) -> str:
    """Render HTML fragment for a feature event."""
    with Session(engine) as session:
        feature = get_feature(session, event.feature_id)

        if event.item_id:
            item = get_item(session, event.item_id)
            items = get_items(session)  # Needed for move dropdown
            return templates.get_template("macros.html").module.item_feature_item_with_move(
                item, feature, items, username="SSE"
            )
        else:
            return templates.get_template("macros.html").module.standalone_feature_item(
                feature, username="SSE"
            )
```

**Note**: Username in SSE fragments is not used for actions (only display), since each client has their own username cookie for actual POST requests.

## Implementation Decisions

### Why SSE Over WebSockets?

| Criteria | SSE | WebSockets |
|----------|-----|------------|
| **Complexity** | Low (HTTP-based) | High (protocol upgrade) |
| **HTMX Support** | Native `hx-sse` | Requires extension |
| **Use Case Fit** | Perfect (unidirectional) | Overkill (bidirectional) |
| **Reconnection** | Automatic | Manual logic needed |
| **Proxy/Firewall** | Works everywhere (HTTP) | Often blocked |
| **Browser Support** | All modern browsers | All modern browsers |

**Decision**: SSE is simpler and sufficient for server → client updates.

### Why In-Memory Event Bus?

**For single-server deployments** (current SAVT setup):
- ✅ Simple: Just a list of queues
- ✅ Fast: No network/serialization overhead
- ✅ Reliable: No external dependencies (Redis/RabbitMQ)

**Limitations**:
- ❌ Does not scale to multiple servers (sticky sessions required)
- ❌ Lost on server restart (acceptable - clients auto-reconnect)

**Future**: If horizontal scaling needed, swap in Redis pub/sub without API changes.

### Why Async Feature Service?

SSE requires async/await for event streaming. Options:

1. **Make entire feature_service async** - Large refactor
2. **Separate async wrapper layer** - Duplication
3. **Background task for broadcasting** - Adds complexity

**Decision**: Start with option 2 (async wrappers for veto/unveto operations only). Re-evaluate if more operations need real-time updates.

### Why HTML Fragments in SSE?

**Alternative 1**: Send JSON, let client re-fetch HTML
```json
{"event": "feature-updated", "feature_id": 123}
```
- ❌ Requires extra HTTP request per client
- ❌ More complex client logic

**Alternative 2**: Send HTML directly in SSE
```html
<div id="feature-123">...[rendered HTML]...</div>
```
- ✅ HTMX swaps immediately (zero extra requests)
- ✅ Server controls rendering (consistent with HTMX philosophy)
- ⚠️ Larger payload (~1-2KB per event vs ~50 bytes JSON)

**Decision**: Send HTML. Bandwidth is negligible for small teams, and simplicity wins.

## Edge Cases & Error Handling

### Client Disconnection
- **Browser tab closed**: SSE connection drops, server cleans up queue
- **Network interruption**: Browser auto-reconnects (SSE spec)
- **Server restart**: All clients reconnect, fetch fresh state

### Race Conditions
- **User A vetos while User B's SSE update arrives**:
  - User A sees instant feedback from POST response
  - SSE update merges or is ignored (DOM already updated)
  - No conflict - eventual consistency is fine

### Stale Updates
- **Client receives update for deleted feature**:
  - Target element `#feature-123` not found in DOM
  - HTMX silently ignores (expected behavior)

### Performance
- **100 connected clients, 1 veto/second**:
  - 100 HTML fragments sent per second (~150KB/s)
  - Well within FastAPI/Uvicorn capacity (1000s of concurrent SSE connections)

## Security Considerations

### Threat Model
SSE inherits SAVT's trust-based security model:
- ❌ No authentication on SSE endpoint
- ❌ Anyone can connect and see all updates
- ✅ Acceptable for co-located teams in trusted environments

### Potential Issues
- **DOS via connection flooding**: Rate limit SSE endpoint (future)
- **Data leakage**: All connected clients see all changes (by design)
- **Cookie stealing**: Use `HttpOnly` cookies (already implemented)

### Mitigations (Future)
- Add rate limiting: `slowapi` or nginx
- Add authentication: Require username cookie to connect
- Add filtering: Only send relevant updates per client

## Testing Strategy

### Unit Tests (`tests/test_event_broadcaster.py`)
```python
@pytest.mark.asyncio
async def test_event_broadcaster_single_subscriber():
    """Test single subscriber receives event."""
    broadcaster = EventBroadcaster()
    events = []

    async for event in broadcaster.subscribe():
        events.append(event)
        if len(events) >= 1:
            break

    await broadcaster.broadcast(FeatureEvent("test", 123))
    assert len(events) == 1
    assert events[0].feature_id == 123
```

### Integration Tests (`tests/test_sse_integration.py`)
```python
def test_sse_endpoint_connection(client: TestClient):
    """Test SSE endpoint returns event stream."""
    with client.stream("GET", "/api/v1/events") as response:
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream"

@pytest.mark.asyncio
async def test_veto_broadcasts_event(client: TestClient):
    """Test veto operation broadcasts SSE event."""
    # Connect SSE stream
    # Perform veto via POST
    # Verify SSE event received with correct HTML
```

### Manual Testing
- Open two browser windows side-by-side
- Veto in Window A → verify instant update in Window B
- Check DevTools Network tab for SSE connection
- Verify auto-reconnection after server restart

## Performance Impact

### Expected Overhead
- **Memory**: ~10KB per connected client (queue + connection state)
- **CPU**: Minimal (async event broadcasting)
- **Network**: ~1-2KB per event × number of clients
- **Latency**: <100ms from action to all clients seeing update

### Load Testing
- Test with 50 concurrent SSE connections
- Simulate 10 veto operations/second
- Measure: P95 event delivery latency, memory usage, CPU %

## Migration & Rollout

### Phase 1: Core Implementation (This PR)
- [ ] Add `sse-starlette` dependency
- [ ] Implement `EventBroadcaster` service
- [ ] Create `/api/v1/events` SSE endpoint
- [ ] Add async wrappers for veto/unveto operations
- [ ] Integrate HTMX SSE extension in templates

### Phase 2: Testing & Refinement
- [ ] Unit tests for event broadcaster
- [ ] Integration tests for SSE endpoint
- [ ] Manual testing with multiple clients
- [ ] Performance testing under load

### Phase 3: Documentation & Polish
- [ ] Update README with multiplayer feature
- [ ] Add troubleshooting guide for SSE
- [ ] Document browser compatibility
- [ ] Add demo video/screenshots

### Backwards Compatibility
- ✅ No breaking changes to existing routes
- ✅ SSE is progressive enhancement (works without it)
- ✅ Clients without SSE extension still work (manual refresh)

## Future Enhancements

### Short Term (Next Release)
- **Presence indicators**: "3 users online" (via SSE heartbeat)
- **Action notifications**: Toast "Alice vetoed Feature X"
- **Optimistic UI**: Disable veto button while waiting for SSE confirmation

### Medium Term
- **Redis pub/sub**: For multi-server deployments
- **Event filtering**: Only send relevant updates per client
- **Compressed events**: Gzip SSE stream for bandwidth savings

### Long Term
- **Operational transforms**: Collaborative text editing for feature descriptions
- **Undo/redo**: Broadcast undo events across clients
- **Conflict resolution**: Automatic merge when two users edit simultaneously

## References

- **SSE Specification**: [MDN Web Docs - Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
- **sse-starlette**: [GitHub Repository](https://github.com/sysid/sse-starlette)
- **HTMX SSE**: [HTMX SSE Extension](https://htmx.org/extensions/server-sent-events/)
- **FastAPI Background Tasks**: [FastAPI Docs](https://fastapi.tiangolo.com/tutorial/background-tasks/)

## Open Questions

1. **Event retention**: Should we keep last N events for late-joining clients?
2. **Event IDs**: Use feature.id or generate unique event IDs for deduplication?
3. **Reconnection strategy**: Send full state diff on reconnect or rely on client refresh?
4. **Rate limiting**: Per-IP or per-cookie? What threshold?

## Success Metrics

- ✅ Two users can veto/unveto simultaneously without refresh
- ✅ Updates appear in <200ms on all connected clients
- ✅ No test regressions (all 111+ tests still pass)
- ✅ No performance degradation with 10 concurrent SSE connections
- ✅ Auto-reconnection works after network interruption
