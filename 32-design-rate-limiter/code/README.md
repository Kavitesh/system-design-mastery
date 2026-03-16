# Design a Rate Limiter - Code Lab

Hands-on demos for building a rate limiter from scratch - pluggable algorithms, configurable rules, distributed counters, and a client that respects rate limit headers.

## What's Included

| File | Description |
|------|-------------|
| `rate_limiter_service.py` | Flask API gateway with pluggable rate limiting (token bucket + sliding window) |
| `rule_engine.py` | Configurable rate limit rules with priority matching |
| `distributed_counter.py` | Simulated Redis-based distributed counter with race condition demos |
| `rate_limiter_client.py` | Client that reads rate limit headers and backs off automatically |

## Prerequisites

```bash
pip install flask requests
```

No Redis required - all demos simulate distributed state with in-memory stores and threading to keep things runnable on any machine.

## Running the Demos

### 1. Rate Limiter Service

A Flask API gateway that rate-limits incoming requests using your choice of algorithm:

```bash
python rate_limiter_service.py
```

Starts on port 5100. Hit the API and watch requests get throttled:

```
GET  http://localhost:5100/api/data         (rate-limited endpoint)
GET  http://localhost:5100/api/health        (not rate-limited)
GET  http://localhost:5100/api/stats         (view rate limiter state)
```

### 2. Rule Engine

Demonstrates configurable rate limit rules with priority-based matching:

```bash
python rule_engine.py
```

Shows how different clients (free tier, enterprise, anonymous) get different limits based on matching rules.

### 3. Distributed Counter

Simulates multiple servers sharing rate limit state - and what goes wrong without atomic operations:

```bash
python distributed_counter.py
```

Runs three scenarios: naive (racy), atomic, and the Lua-script approach. Compare the final counts.

### 4. Rate Limiter Client

A client that reads X-RateLimit-* headers and automatically backs off when throttled:

```bash
# Start the service first
python rate_limiter_service.py

# In another terminal
python rate_limiter_client.py
```

Sends a burst of requests and shows the client adapting to rate limit headers in real time.
