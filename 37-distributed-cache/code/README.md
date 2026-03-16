# Design a Distributed Cache - Code Lab

Hands-on demos covering distributed cache mechanics: consistent hashing for partitioning, replication with failover, hot key mitigation, and performance benchmarking.

## What's Included

| File | Description |
|------|-------------|
| `distributed_cache.py` | Multi-node cache with consistent hashing ring, GET/SET/DELETE, and live node add/remove |
| `cache_cluster.py` | Replicated cache cluster with automatic failover when a primary goes down |
| `hot_key_solution.py` | Detects hot keys and mitigates them with a local L1 cache layer |
| `cache_benchmark.py` | Benchmarks hit ratio, latency percentiles, and throughput under Zipfian and uniform workloads |

## Prerequisites

Python 3.8+ with no external dependencies. Everything runs on the standard library.

## Running the Demos

### 1. Distributed Cache

See how consistent hashing distributes keys across nodes and handles node additions/removals with minimal key movement:

```bash
python distributed_cache.py
```

Shows the hash ring layout, per-node key distribution, and the percentage of keys that move when a node joins or leaves.

### 2. Cache Cluster with Replication

Watch a replicated cache cluster handle a primary node failure:

```bash
python cache_cluster.py
```

Writes data to the cluster, kills a primary, promotes a replica, and verifies data availability after failover.

### 3. Hot Key Solution

Demonstrates the hot key problem and how an L1 local cache fixes it:

```bash
python hot_key_solution.py
```

Generates Zipfian traffic where a few keys dominate, then shows the request distribution with and without L1 caching.

### 4. Cache Benchmark

Measures hit ratio, latency, and throughput under different workloads and eviction policies:

```bash
python cache_benchmark.py
```

Compares LRU vs LFU eviction under uniform and Zipfian (power-law) access patterns.
