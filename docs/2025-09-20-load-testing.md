# Frontend Load Testing for 33 Concurrent Users
*Documentation updated: 2025-09-20*

This document describes the load testing implementation for validating that SAVT can handle 33 concurrent users as required.

## Overview

The load testing system simulates realistic user behavior patterns:

- **33 concurrent users** performing simultaneous actions
- **Realistic interaction patterns** based on actual UI workflows
- **HTMX-aware requests** matching frontend behavior
- **Comprehensive metrics** including response times, throughput, and success rates

## Test Scenarios

### Primary User Actions (Weighted by Likelihood)
1. **Veto/Unveto Features** (65%) - Primary use case
2. **Homepage Refresh** (15%) - Checking current state
3. **Create Features** (12%) - Adding new content
4. **Create Items** (8%) - Organizing features

### User Session Flow
1. Load homepage and parse current state
2. Create personal item and feature
3. Perform weighted random actions for 60 seconds
4. Include realistic "think time" between actions
5. Handle errors gracefully

## Files

### Core Load Testing
- `tests/load_test_realistic.py` - Main load testing implementation
- `tests/load_test_frontend.py` - Alternative comprehensive test
- `tests/run_load_test.py` - Quick runner with dependency checks

### Automation
- `scripts/load_test.sh` - Full automated test (PostgreSQL + server startup)

## Usage

### Quick Test (Manual Server Start)
```bash
# Terminal 1: Start server
TEST_DATABASE=postgresql DATABASE_URL=postgresql://savt_user:savt_password@localhost:5432/savt \
uvicorn src.main:app --reload

# Terminal 2: Run test
python tests/load_test_realistic.py
```

### Automated Test (Everything Included)
```bash
./scripts/load_test.sh
```

### Configuration Options
You can modify test parameters in the load test files:

```python
# Number of concurrent users (default: 33)
NUM_USERS = 33

# Test duration in seconds (default: 60)
DURATION = 60

# Server URL (default: localhost:8000)
BASE_URL = "http://localhost:8000"
```

## Metrics Collected

### Performance Metrics
- **Response Times**: Average, median, 95th, 99th percentiles
- **Throughput**: Total requests/second and successful requests/second
- **Success Rate**: Percentage of successful requests
- **Error Analysis**: Breakdown of failure types

### Action-Specific Metrics
- Response times per action type (veto, unveto, create, etc.)
- Success rates per action type
- Request volume per action type

### Real-World Validation
- **Database Connection Usage**: Validates our 35-connection pool
- **Concurrent HTMX Requests**: Tests frontend responsiveness
- **Error Recovery**: Ensures graceful degradation under load

## Expected Performance

Based on our infrastructure:

### Target Metrics
- **Success Rate**: >99% (allows for occasional network issues)
- **Average Response**: <500ms (good user experience)
- **95th Percentile**: <1000ms (acceptable for peak loads)
- **Throughput**: >50 successful requests/sec (handles burst traffic)

### Infrastructure Capacity
- **PostgreSQL**: 35 connections (20 core + 15 overflow)
- **FastAPI**: Async/await handles thousands of connections
- **Connection Pool**: Optimized for realistic usage patterns

## Interpreting Results

### 🟢 Excellent Performance
- Success rate >99%
- Average response <200ms
- High throughput >100 req/sec

### 🟡 Good Performance
- Success rate >95%
- Average response <500ms
- Moderate throughput >50 req/sec

### 🔴 Needs Investigation
- Success rate <95%
- Average response >500ms
- Low throughput <50 req/sec

## Load Test Architecture

### RealisticUser Class
Simulates individual user sessions with:
- HTMX request headers
- State tracking (current items/features)
- Weighted action selection
- Realistic think times

### LoadTestCoordinator Class
Manages concurrent execution:
- Coordinates 33 simultaneous users
- Aggregates performance metrics
- Generates comprehensive reports
- Handles error scenarios

### Realistic Behavior Patterns
- Users don't act simultaneously (natural distribution)
- Variable think times (0.2s - 4.0s based on action)
- Error resilience (continues testing despite failures)
- Session persistence (users build on their own data)

## Future Enhancements

### Additional Scenarios
- Mixed user types (power users vs casual users)
- Peak usage simulations (lunch time, end of day)
- Sustained load testing (hours instead of minutes)
- Geographic distribution simulation

### Enhanced Metrics
- Database query performance tracking
- Memory usage monitoring
- Connection pool utilization
- HTMX-specific performance metrics

This load testing framework validates that our 33-user concurrency requirement is met with excellent user experience and system stability.
