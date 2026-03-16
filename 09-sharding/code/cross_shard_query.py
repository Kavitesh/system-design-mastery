"""
Cross-Shard Queries - Scatter-Gather Pattern
=============================================
Sets up 4 shards with order data distributed by customer_id, then runs
single-shard targeted queries and cross-shard aggregate queries. Exposes
the classic mistake of averaging per-shard averages instead of computing
the global average from sums and counts.

    python cross_shard_query.py
"""

import hashlib
import random
import time

NUM_SHARDS = 4
NUM_CUSTOMERS = 200
NUM_ORDERS = 10_000

# ---------------------------------------------------------------------------
#   Shard Storage
# ---------------------------------------------------------------------------

class ShardCluster:
    """
    Simulates a cluster of database shards. Each shard is a plain dict
    holding a list of order records. Routing uses hash-based sharding
    on customer_id.
    """

    def __init__(self, num_shards):
        self.num_shards = num_shards
        self.shards = {i: [] for i in range(num_shards)}

    def _route(self, customer_id):
        h = int(hashlib.md5(str(customer_id).encode()).hexdigest(), 16)
        return h % self.num_shards

    def insert(self, order):
        shard_id = self._route(order["customer_id"])
        self.shards[shard_id].append(order)

    def query_single_shard(self, customer_id):
        shard_id = self._route(customer_id)
        return [o for o in self.shards[shard_id]
                if o["customer_id"] == customer_id]

    def scatter_gather(self, filter_fn):
        """
        Sends the filter function to every shard in parallel (simulated)
        and collects all matching rows.
        """
        results = []
        for shard_id in range(self.num_shards):
            matching = [o for o in self.shards[shard_id] if filter_fn(o)]
            results.extend(matching)
        return results

    def per_shard_aggregate(self, agg_fn):
        """
        Runs an aggregation function on each shard independently and
        returns per-shard results. The caller must merge them correctly.
        """
        return {sid: agg_fn(rows) for sid, rows in self.shards.items()}


# ---------------------------------------------------------------------------
#   Data Generator
# ---------------------------------------------------------------------------

def generate_orders(cluster, num_customers, num_orders):
    categories = ["electronics", "clothing", "books", "food", "home"]
    for i in range(num_orders):
        order = {
            "order_id": i,
            "customer_id": random.randint(1, num_customers),
            "total": round(random.uniform(5.0, 500.0), 2),
            "category": random.choice(categories),
        }
        cluster.insert(order)


# ---------------------------------------------------------------------------
#   Aggregation - Correct vs Wrong
# ---------------------------------------------------------------------------

def shard_count(rows):
    return len(rows)


def shard_sum(rows):
    return sum(o["total"] for o in rows)


def shard_avg(rows):
    if not rows:
        return 0.0
    return sum(o["total"] for o in rows) / len(rows)


def shard_sum_and_count(rows):
    return {"sum": sum(o["total"] for o in rows), "count": len(rows)}


def shard_top_n(rows, n=5):
    sorted_rows = sorted(rows, key=lambda o: -o["total"])
    return sorted_rows[:n]


# ---------------------------------------------------------------------------
#   Demonstrations
# ---------------------------------------------------------------------------

def demo_single_vs_scatter(cluster):
    print("--- Demo 1: Single-Shard vs Scatter-Gather ---")

    customer_id = 42
    start = time.perf_counter()
    targeted = cluster.query_single_shard(customer_id)
    single_time = time.perf_counter() - start

    start = time.perf_counter()
    scattered = cluster.scatter_gather(lambda o: o["total"] > 100)
    scatter_time = time.perf_counter() - start

    print(f"  Single-shard (customer {customer_id}): "
          f"{len(targeted)} orders in {single_time*1000:.2f}ms")
    print(f"  Scatter-gather (total > 100): "
          f"{len(scattered)} orders in {scatter_time*1000:.2f}ms")
    print(f"  Scatter-gather is {scatter_time/max(single_time, 1e-9):.1f}x slower\n")


def demo_aggregation(cluster):
    print("--- Demo 2: Cross-Shard Aggregation ---")

    counts = cluster.per_shard_aggregate(shard_count)
    total_count = sum(counts.values())
    print(f"  COUNT: per-shard {dict(counts)} -> total = {total_count}")

    sums = cluster.per_shard_aggregate(shard_sum)
    total_sum = sum(sums.values())
    print(f"  SUM:   per-shard totals summed -> ${total_sum:,.2f}")

    print(f"\n  --- AVG: The Classic Mistake ---")
    per_shard_avgs = cluster.per_shard_aggregate(shard_avg)
    wrong_avg = sum(per_shard_avgs.values()) / len(per_shard_avgs)

    sum_counts = cluster.per_shard_aggregate(shard_sum_and_count)
    global_sum = sum(sc["sum"] for sc in sum_counts.values())
    global_count = sum(sc["count"] for sc in sum_counts.values())
    correct_avg = global_sum / global_count

    print(f"  Per-shard averages:")
    for sid in sorted(per_shard_avgs):
        print(f"    shard_{sid}: ${per_shard_avgs[sid]:.2f}")
    print(f"  WRONG (average of averages): ${wrong_avg:.2f}")
    print(f"  RIGHT (total sum / total count): ${correct_avg:.2f}")
    print(f"  Error: ${abs(wrong_avg - correct_avg):.2f} "
          f"({abs(wrong_avg - correct_avg) / correct_avg * 100:.2f}%)\n")


def demo_top_n(cluster):
    print("--- Demo 3: Cross-Shard TOP-N ---")

    n = 5
    per_shard_tops = {}
    for sid, rows in cluster.shards.items():
        per_shard_tops[sid] = shard_top_n(rows, n)

    candidates = []
    for tops in per_shard_tops.values():
        candidates.extend(tops)
    global_top = sorted(candidates, key=lambda o: -o["total"])[:n]

    print(f"  Top {n} orders across all shards (merge-sorted):")
    print(f"  {'Order ID':>10} {'Customer':>10} {'Total':>10} {'Category':<12}")
    print(f"  {'-'*45}")
    for o in global_top:
        print(f"  {o['order_id']:>10} {o['customer_id']:>10} "
              f"${o['total']:>8.2f} {o['category']:<12}")

    print(f"\n  Strategy: fetch top {n} from each of {NUM_SHARDS} shards "
          f"({n * NUM_SHARDS} candidates), then merge-sort and take top {n}.\n")


def demo_distribution(cluster):
    print("--- Demo 4: Data Distribution Across Shards ---")
    print(f"  {'Shard':<10} {'Orders':>8} {'Percent':>8}")
    print(f"  {'-'*28}")
    total = sum(len(rows) for rows in cluster.shards.values())
    for sid in sorted(cluster.shards):
        count = len(cluster.shards[sid])
        pct = count / total * 100
        print(f"  shard_{sid:<4} {count:>8} {pct:>7.1f}%")
    print()


# ---------------------------------------------------------------------------
#   Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Cross-Shard Queries - Scatter-Gather Pattern")
    print("=" * 50)
    print(f"Shards: {NUM_SHARDS}  |  Customers: {NUM_CUSTOMERS}  "
          f"|  Orders: {NUM_ORDERS:,}\n")

    random.seed(99)
    cluster = ShardCluster(NUM_SHARDS)
    generate_orders(cluster, NUM_CUSTOMERS, NUM_ORDERS)

    demo_distribution(cluster)
    demo_single_vs_scatter(cluster)
    demo_aggregation(cluster)
    demo_top_n(cluster)

    print("--- Summary ---")
    print("  1. Single-shard queries are fast - design your shard key to maximize them")
    print("  2. Scatter-gather works but hits every shard - use sparingly")
    print("  3. Never average the averages - always aggregate from sums and counts")
    print("  4. TOP-N across shards requires fetching N from each shard, then merging")
    print()
