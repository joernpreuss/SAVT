# SAVT Concurrency Scaling Plan - 33 Simultaneous Users

**Created**: 2025-09-18
**Updated**: 2025-09-23
**Target**: Support 33 simultaneous users without performance degradation
**Current State**: SQLite with single-threaded writes, full page reloads, no connection pooling

> **IMPORTANT NOTE (2025-09-23)**: Data migration FROM SQLite TO PostgreSQL will never be needed because SQLite will always only contain test data. Production deployments start fresh with PostgreSQL - no data migration tooling required.

## Problem Analysis

### Current Bottlenecks at 33 Users

#### 1. Database Concurrency Issues
```python
# Current Problem: SQLite Write Lock Contention
def create_item(session: Session, item: Item):
    session.add(item)
    session.commit()  # <- All 33 users block here during writes
```

**Impact**:
- Write operations serialize completely
- Users experience 1-5 second delays during concurrent item creation
- Database locks cause request timeouts

#### 2. Connection Management Problems
```python
# Current Problem: No Connection Pooling
def get_session():
    with Session(engine) as session:
        yield session  # 33 parallel connections = resource exhaustion
```

**Impact**:
- Each request creates new DB connection
- Connection overhead adds 100-200ms per request
- Potential connection exhaustion under load

#### 3. Inefficient Page Rendering
```python
# Current Problem: Full Page Reloads
return render_full_page_response(request, session)
# Every HTMX request loads: ALL items + ALL features + UI state
```

**Impact**:
- 33 users × full page data = unnecessary database load
- Large response payloads (10KB+ per request)
- Slower perceived performance

## Solution Architecture

### Phase 1: Database Scaling (CRITICAL - Week 1)

#### 1.1 PostgreSQL Migration
```python
# Target Architecture
DATABASE_URL = "postgresql+asyncpg://user:password@localhost:5432/savt"

# Migration Strategy:
# 1. Add asyncpg dependency: uv add asyncpg
# 2. Create PostgreSQL schemas matching SQLite
# 3. Data migration script
# 4. Update connection configuration
```

**Benefits**:
- True concurrent writes (MVCC instead of locks)
- Better performance under load
- Prepared for horizontal scaling

#### 1.2 Async Database Operations
```python
# Current (Blocking)
def create_item(session: Session, item: Item) -> Item:
    session.add(item)
    session.commit()
    return item

# Target (Non-blocking)
async def create_item_async(session: AsyncSession, item: Item) -> Item:
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item
```

**Benefits**:
- Non-blocking I/O operations
- Better CPU utilization
- Reduced response times under load

#### 1.3 Connection Pooling
```python
# Target Configuration
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,              # Core pool size
    max_overflow=15,           # Additional connections during peaks
    pool_recycle=3600,         # Recycle connections every hour
    pool_pre_ping=True,        # Validate connections
    echo=False                 # Disable SQL logging in production
)

async def get_async_session():
    async with AsyncSession(engine) as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

**Benefits**:
- Reuse existing connections
- Controlled resource usage
- Better performance characteristics

### Phase 2: Response Optimization (HIGH - Week 2)

#### 2.1 Partial HTMX Updates
```python
# Current: Full Page Response
@router.post("/create/item/")
async def route_create_item(...):
    create_item(session, item)
    return render_full_page_response(request, session)  # ~10KB response

# Target: Partial Updates
@router.post("/create/item/")
async def route_create_item(...):
    item = await create_item_async(session, item)

    # Return only the new item fragment
    return templates.TemplateResponse(
        request,
        "fragments/item_row.html",
        {"item": item, "settings": settings}
    )  # ~0.5KB response
```

**Template Changes**:
```html
<!-- New fragment: templates/fragments/item_row.html -->
<div class="item-row" id="item-{{ item.id }}">
  <span class="item-name">{{ item.name }}</span>
  <span class="item-kind">{{ item.kind }}</span>
  <!-- item controls -->
</div>

<!-- Updated: templates/properties.html -->
<div id="items-container" hx-target="this" hx-swap="afterend">
  {% for item in items %}
    {% include "fragments/item_row.html" %}
  {% endfor %}
</div>
```

#### 2.2 Concurrent Page Loading
```python
async def render_full_page_response(request, session):
    """Load page data concurrently instead of sequentially."""
    async with asyncio.TaskGroup() as tg:
        items_task = tg.create_task(get_items_async(session))
        features_task = tg.create_task(get_features_async(session))
        stats_task = tg.create_task(get_dashboard_stats_async(session))

    return templates.TemplateResponse(
        request,
        "properties.html",
        {
            "items": items_task.result(),
            "features": features_task.result(),
            "stats": stats_task.result(),
            "settings": settings
        }
    )
```

**Benefits**:
- Parallel data loading reduces page load time by 40-60%
- Better user experience during peak usage
- More efficient database utilization

### Phase 3: Caching Strategy (MEDIUM - Week 3)

#### 3.1 Application-Level Caching
```python
from functools import lru_cache
from datetime import datetime, timedelta

class CacheManager:
    def __init__(self):
        self._cache = {}
        self._timestamps = {}

    async def get_or_compute(self, key: str, compute_fn, ttl: int = 60):
        """Get from cache or compute with TTL."""
        now = datetime.now()

        if key in self._cache:
            if now - self._timestamps[key] < timedelta(seconds=ttl):
                return self._cache[key]

        # Cache miss or expired
        result = await compute_fn()
        self._cache[key] = result
        self._timestamps[key] = now
        return result

cache_manager = CacheManager()

@router.get("/")
async def list_features(...):
    items = await cache_manager.get_or_compute(
        "items_list",
        lambda: get_items_async(session),
        ttl=30  # Cache for 30 seconds
    )
```

#### 3.2 Smart Cache Invalidation
```python
@router.post("/create/item/")
async def route_create_item(...):
    item = await create_item_async(session, item)

    # Invalidate relevant caches
    cache_manager.invalidate("items_list")
    cache_manager.invalidate("dashboard_stats")

    return partial_response(item)
```

### Phase 4: Load Testing & Monitoring (Week 4)

#### 4.1 Load Testing Setup
```python
# tests/load_testing/concurrent_users_test.py
import asyncio
import aiohttp
import time
from dataclasses import dataclass
from typing import List

@dataclass
class UserAction:
    endpoint: str
    data: dict
    expected_response_time: float

class UserSimulator:
    def __init__(self, base_url: str, user_id: int):
        self.base_url = base_url
        self.user_id = user_id
        self.session = None
        self.metrics = []

    async def start_session(self):
        self.session = aiohttp.ClientSession()

    async def close_session(self):
        await self.session.close()

    async def perform_action(self, action: UserAction):
        start_time = time.time()

        async with self.session.post(
            f"{self.base_url}{action.endpoint}",
            data=action.data
        ) as response:
            duration = time.time() - start_time
            success = response.status == 200

            self.metrics.append({
                "action": action.endpoint,
                "duration": duration,
                "success": success,
                "user_id": self.user_id
            })

            return success, duration

async def simulate_typical_user(user_id: int, duration_minutes: int = 5):
    """Simulate typical user behavior for specified duration."""
    simulator = UserSimulator("http://localhost:8000", user_id)
    await simulator.start_session()

    actions = [
        UserAction("/create/item/", {"name": f"Pizza-{user_id}-{i}", "kind": "Margherita"}, 0.5),
        UserAction("/create/feature/", {"name": f"Topping-{user_id}-{i}", "amount": 2}, 0.3),
        UserAction("/", {}, 0.8),  # Page refresh
    ]

    end_time = time.time() + (duration_minutes * 60)

    while time.time() < end_time:
        for action in actions:
            success, duration = await simulator.perform_action(action)

            if duration > action.expected_response_time:
                print(f"SLOW: User {user_id} - {action.endpoint} took {duration:.2f}s")

            # Wait between actions (realistic user behavior)
            await asyncio.sleep(random.uniform(2, 8))

    await simulator.close_session()
    return simulator.metrics

async def load_test_33_users(duration_minutes: int = 5):
    """Run load test with 33 concurrent users."""
    print(f"Starting load test: 33 users for {duration_minutes} minutes")

    # Start all users simultaneously
    user_tasks = [
        simulate_typical_user(user_id, duration_minutes)
        for user_id in range(1, 34)
    ]

    start_time = time.time()
    all_metrics = await asyncio.gather(*user_tasks)
    total_time = time.time() - start_time

    # Analyze results
    analyze_load_test_results(all_metrics, total_time)

def analyze_load_test_results(all_metrics: List[List[dict]], total_time: float):
    """Analyze and report load test results."""
    flat_metrics = [metric for user_metrics in all_metrics for metric in user_metrics]

    total_requests = len(flat_metrics)
    successful_requests = sum(1 for m in flat_metrics if m["success"])
    failed_requests = total_requests - successful_requests

    avg_response_time = sum(m["duration"] for m in flat_metrics) / total_requests
    max_response_time = max(m["duration"] for m in flat_metrics)

    print(f"\n=== Load Test Results ===")
    print(f"Duration: {total_time:.2f} seconds")
    print(f"Total Requests: {total_requests}")
    print(f"Successful: {successful_requests} ({successful_requests/total_requests*100:.1f}%)")
    print(f"Failed: {failed_requests} ({failed_requests/total_requests*100:.1f}%)")
    print(f"Average Response Time: {avg_response_time:.3f}s")
    print(f"Max Response Time: {max_response_time:.3f}s")
    print(f"Requests per Second: {total_requests/total_time:.2f}")

    # Performance targets
    if avg_response_time > 1.0:
        print("❌ FAIL: Average response time > 1.0s")
    if failed_requests > total_requests * 0.01:  # > 1% failure rate
        print("❌ FAIL: Failure rate > 1%")
    if max_response_time > 5.0:
        print("❌ FAIL: Max response time > 5.0s")

    print("\n=== Performance by Endpoint ===")
    by_endpoint = {}
    for m in flat_metrics:
        endpoint = m["action"]
        if endpoint not in by_endpoint:
            by_endpoint[endpoint] = []
        by_endpoint[endpoint].append(m["duration"])

    for endpoint, durations in by_endpoint.items():
        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)
        print(f"{endpoint}: avg={avg_duration:.3f}s, max={max_duration:.3f}s, count={len(durations)}")

if __name__ == "__main__":
    asyncio.run(load_test_33_users(duration_minutes=5))
```

#### 4.2 Performance Monitoring
```python
# src/middleware/performance.py
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        response = await call_next(request)

        duration = time.time() - start_time

        # Log slow requests
        if duration > 1.0:
            logger.warning(
                "Slow request detected",
                path=request.url.path,
                method=request.method,
                duration=duration,
                status_code=response.status_code
            )

        # Add performance headers
        response.headers["X-Response-Time"] = f"{duration:.3f}s"

        return response

# src/main.py - Add middleware
app.add_middleware(PerformanceMonitoringMiddleware)
```

## Implementation Timeline

### Week 1: Database Migration (CRITICAL)
- [ ] **Day 1-2**: PostgreSQL setup and schema migration
- [ ] **Day 3-4**: Convert all services to async operations
- [ ] **Day 5**: Connection pooling configuration
- [ ] **Day 6-7**: Integration testing and bug fixes

**Deliverables**:
- PostgreSQL database operational
- All CRUD operations using async/await
- Connection pooling configured
- Basic load test passing

### Week 2: Response Optimization (HIGH)
- [ ] **Day 1-2**: Create partial HTMX update fragments
- [ ] **Day 3-4**: Implement concurrent page loading
- [ ] **Day 5**: Update all routes to use partial responses
- [ ] **Day 6-7**: UI testing and refinement

**Deliverables**:
- Partial HTMX updates for all operations
- Reduced response sizes (>80% reduction)
- Improved perceived performance
- 33-user load test shows improvement

### Week 3: Caching Strategy (MEDIUM)
- [ ] **Day 1-2**: Application-level caching implementation
- [ ] **Day 3-4**: Smart cache invalidation
- [ ] **Day 5**: Cache performance tuning
- [ ] **Day 6-7**: Load testing with caching

**Deliverables**:
- In-memory caching operational
- Cache hit rates > 70% for read operations
- Further performance improvements demonstrated

### Week 4: Testing & Monitoring (MEDIUM)
- [ ] **Day 1-2**: Comprehensive load testing suite
- [ ] **Day 3-4**: Performance monitoring dashboard
- [ ] **Day 5**: Stress testing (50+ users)
- [ ] **Day 6-7**: Performance tuning and optimization

**Deliverables**:
- Automated load testing
- Performance monitoring in place
- 33-user target consistently met
- Documentation and runbooks

## Success Metrics

### Performance Targets
| Metric | Current | Target | Critical |
|--------|---------|--------|----------|
| Avg Response Time | 2.5s | < 0.5s | < 1.0s |
| 95th Percentile | 8s | < 1.5s | < 3.0s |
| Concurrent Users | 5 | 33 | 25 |
| Failure Rate | 5% | < 0.5% | < 2% |
| Database Connections | 50+ | < 25 | < 40 |

### Acceptance Criteria
- [ ] **33 users can operate simultaneously for 5 minutes**
- [ ] **Average response time < 0.5 seconds under load**
- [ ] **Zero database lock timeouts**
- [ ] **Failure rate < 0.5%**
- [ ] **UI remains responsive during concurrent operations**
- [ ] **No degradation in user experience**

## Risk Assessment

### High Risk
- **PostgreSQL Migration Complexity**: Data migration could cause downtime
  - *Mitigation*: Staged migration with rollback plan
- **Async Conversion Breaking Changes**: Major refactoring of service layer
  - *Mitigation*: Comprehensive test suite, gradual conversion

### Medium Risk
- **HTMX Partial Updates**: UI complexity increase
  - *Mitigation*: Extensive frontend testing
- **Performance Testing Environment**: Load testing infrastructure needed
  - *Mitigation*: Use cloud-based load testing tools

### Low Risk
- **Caching Invalidation**: Cache consistency issues
  - *Mitigation*: Conservative TTL values, monitoring

## Rollback Plan

### Database Migration Rollback
1. Keep SQLite database as backup during transition
2. Migration scripts can reverse all schema changes
3. Application can switch back to sync operations

### Code Rollback
1. Feature flags for async operations
2. Git branches for each phase
3. Automated deployment with health checks

## Resources Required

### Infrastructure
- PostgreSQL server (local development + production)
- Load testing environment
- Monitoring tools setup

### Development Time
- **40 hours** total estimated effort
- **1 developer** primary implementation
- **Phase 1 critical path** - must complete before Phase 2

### Dependencies
- `asyncpg` - PostgreSQL async driver
- `redis` (optional) - for advanced caching
- `locust` or similar - load testing framework

---

**Success Definition**: 33 users can simultaneously create items, features, and navigate the UI with sub-second response times and zero failures for sustained periods.

**Next Steps**: Begin with PostgreSQL migration and async conversion - this is the foundation for all other optimizations.
