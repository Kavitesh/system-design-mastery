# Chapter 20 - Consistent Hashing - Code Labs

Hands-on Python demos for consistent hashing concepts.

## Labs

| # | File                      | What You'll See                                            |
|---|---------------------------|------------------------------------------------------------|
| 1 | `naive_vs_consistent.py`  | Modulo hashing vs consistent hashing - key redistribution  |
| 2 | `hash_ring.py`            | Full hash ring implementation with vnodes and weighting    |
| 3 | `virtual_nodes.py`        | Impact of vnode count on load distribution uniformity      |
| 4 | `distributed_cache.py`    | Working distributed cache with dynamic node management     |

## Running the Labs

```bash
python naive_vs_consistent.py
python hash_ring.py
python virtual_nodes.py
python distributed_cache.py
```

## Requirements

- Python 3.8+
- No external dependencies (stdlib only)

## What Each Lab Teaches

### Lab 1: naive_vs_consistent.py
Shows the rehashing catastrophe firsthand. With modulo hashing, adding one server remaps
most keys. With consistent hashing, only a fraction of keys move. Prints exact counts so
you can see the difference.

### Lab 2: hash_ring.py
A production-style consistent hash ring supporting virtual nodes, weighted nodes, and
efficient O(log N) lookups via binary search. Add servers, remove servers, and watch
which keys move.

### Lab 3: virtual_nodes.py
Demonstrates why virtual nodes matter. Runs the same workload with 1, 5, 25, 100, and
250 vnodes per server, showing how standard deviation of load drops as vnode count rises.

### Lab 4: distributed_cache.py
Puts it all together - a distributed cache that routes gets/sets through a consistent
hash ring. Simulates node failures and additions, showing cache hit rates and key
migration counts.
