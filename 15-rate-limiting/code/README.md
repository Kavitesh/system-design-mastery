# Rate Limiting & Throttling - Code Lab

Hands-on demos implementing the four major rate limiting algorithms, a Flask API with rate limiting middleware, distributed rate limiting across multiple nodes, and a visual comparison of how each algorithm handles burst traffic.

## What's Included

| File | Description |
|------|-------------|
| `rate_limiters.py` | Token bucket, leaky bucket, fixed window, and sliding window algorithms from scratch |
| `rate_limit_server.py` | Flask API with configurable rate limiting middleware and proper HTTP 429 responses |
| `distributed_rate_limiter.py` | Simulates distributed rate limiting with multiple nodes and a shared counter store |
| `rate_limit_comparison.py` | Visual comparison of how each algorithm handles identical burst traffic patterns |

## Prerequisites

```bash
pip install flask
```

No Redis needed - all demos use in-memory stores to focus on the algorithms.

## Running the Demos

### 1. Rate Limiting Algorithms

See how each algorithm makes allow/deny decisions differently:

```bash
python rate_limiters.py
```

### 2. Flask API with Rate Limiting

A working API server with rate limiting middleware, proper headers, and HTTP 429 responses:

```bash
python rate_limit_server.py
```

Then test it:

```bash
curl http://localhost:5060/api/data
curl http://localhost:5060/api/data -H "X-API-Key: user-alice"
```

### 3. Distributed Rate Limiting

Watch multiple server nodes coordinate rate limits through a shared store:

```bash
python distributed_rate_limiter.py
```

### 4. Algorithm Comparison

Visual side-by-side of how each algorithm handles the same burst traffic:

```bash
python rate_limit_comparison.py
```
