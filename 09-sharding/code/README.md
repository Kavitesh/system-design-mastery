# Code Lab - Data Partitioning & Sharding

Hands-on Python demos that simulate sharding strategies, rebalancing, hotspot detection, and cross-shard queries. No external dependencies required - everything runs with the Python standard library.

---

## Files

| File | What It Demonstrates |
|------|---------------------|
| `sharding_strategies.py` | Range-based, hash-based, and directory-based sharding side by side |
| `shard_rebalancing.py` | Adding/removing shards with consistent hashing and data migration |
| `hotspot_demo.py` | How bad shard keys create hotspots and how salting fixes them |
| `cross_shard_query.py` | Scatter-gather pattern for queries that span multiple shards |

---

## Running the Labs

Each file is standalone. Run them in order for the best learning experience.

```bash
# Lab 1 - Compare sharding strategies
python sharding_strategies.py

# Lab 2 - Watch data migrate during rebalancing
python shard_rebalancing.py

# Lab 3 - See hotspots form and get fixed
python hotspot_demo.py

# Lab 4 - Cross-shard scatter-gather queries
python cross_shard_query.py
```

---

## Lab 1 - Sharding Strategies

Inserts 10,000 simulated user records and distributes them using three strategies: range-based (by user ID ranges), hash-based (modulo of hash), and directory-based (explicit lookup table). Prints distribution stats for each strategy so you can compare evenness.

Key observations:
- Hash-based produces the most even distribution
- Range-based creates uneven shards when IDs aren't uniformly distributed
- Directory-based gives complete control but requires maintaining the mapping

---

## Lab 2 - Shard Rebalancing

Starts with 3 shards using consistent hashing with virtual nodes, then adds a 4th shard and removes the 2nd. After each topology change, it shows how many keys migrated and which shards gained or lost data. Demonstrates why consistent hashing is superior to naive modulo - only a fraction of keys move.

Key observations:
- With consistent hashing, adding a shard moves roughly `1/N` of the data
- With naive modulo, adding a shard moves roughly `(N-1)/N` of the data
- Virtual nodes smooth out the distribution significantly

---

## Lab 3 - Hotspot Detection

Simulates a social media platform where most activity comes from a few popular accounts. First uses `user_id` as the shard key, showing extreme hotspots. Then applies key salting (`user_id:random_suffix`) to spread the load. Prints per-shard request counts to visualize the difference.

Key observations:
- A Zipfian distribution of activity creates severe hotspots
- Key salting distributes writes evenly at the cost of scatter-gather reads
- The trade-off is worth it for write-heavy workloads

---

## Lab 4 - Cross-Shard Queries

Sets up 4 shards with order data distributed by customer ID. Runs single-shard queries (fast, targeted) and cross-shard aggregate queries (scatter-gather). Demonstrates correct aggregation for COUNT, SUM, AVG, and TOP-N across shards - including the classic mistake of averaging averages.

Key observations:
- Single-shard queries are 4x faster (hit one shard instead of four)
- AVG must be computed from total sum / total count, not averaged from per-shard averages
- TOP-N requires fetching N records from each shard, then merging

---

## What You Should Try

1. In `sharding_strategies.py`, change the number of shards and see how distribution changes
2. In `shard_rebalancing.py`, adjust the virtual node count (try 1 vs 200) and compare distribution evenness
3. In `hotspot_demo.py`, change the Zipf exponent to see how skew affects hotspot severity
4. In `cross_shard_query.py`, add a `DISTINCT` aggregation that deduplicates across shards
