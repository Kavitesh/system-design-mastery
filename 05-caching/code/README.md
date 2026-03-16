# Caching Strategies - Code Lab

Hands-on demos showing caching strategies, eviction policies, a Flask cache server, and the thundering herd problem with solutions.

## What's Included

| File | Description |
|------|-------------|
| `cache_strategies.py` | Cache-aside, write-through, write-back, and write-around with a simulated DB |
| `eviction_policies.py` | LRU, LFU, FIFO cache implementations with performance comparison |
| `cache_server.py` | Flask app with an in-memory cache layer (no Redis required) |
| `cache_stampede.py` | Thundering herd problem and solutions (locking, probabilistic early expiration) |

## Prerequisites

```bash
pip install flask
```

No Redis required - all demos use in-memory caches to focus on the concepts.

## Running the Demos

### 1. Caching Strategies

See how each strategy handles reads and writes differently:

```bash
python cache_strategies.py
```

Shows the latency difference between cache hits (sub-millisecond) and misses (100ms), and how each strategy decides when to write to the cache vs the database.

### 2. Eviction Policies

Watch LRU, LFU, and FIFO decide which items to evict when the cache is full:

```bash
python eviction_policies.py
```

Runs identical access patterns through each policy so you can compare the eviction decisions side by side.

### 3. Cache Server

A Flask app serving product data with a built-in cache layer:

```bash
python cache_server.py
```

Then hit the endpoints:

- `http://localhost:5055/product/1` - Fetch a product (cache-aside)
- `http://localhost:5055/product/1` - Same request again (cache hit)
- `http://localhost:5055/benchmark` - Automated latency comparison
- `http://localhost:5055/cache/stats` - Hit/miss statistics

### 4. Cache Stampede

Simulates the thundering herd problem and demonstrates two solutions:

```bash
python cache_stampede.py
```

Watch 20 concurrent requests hit an expired cache key, then see how locking and probabilistic early expiration each prevent the stampede.
