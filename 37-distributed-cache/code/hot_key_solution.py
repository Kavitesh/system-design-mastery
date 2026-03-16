"""
Hot Key Detection and Mitigation
==================================
Simulates the hot key problem in distributed caches - where a tiny
fraction of keys receives a disproportionate share of traffic - and
demonstrates L1 local caching as the fix. A Zipfian distribution
models real-world access patterns where popularity follows a power law.

Run: python hot_key_solution.py
"""

import hashlib
import bisect
import random
import time
from collections import defaultdict, OrderedDict


# ---------------------------------------------------------------------------
# Zipfian distribution generator
# ---------------------------------------------------------------------------

def zipfian_keys(num_keys: int, num_requests: int, skew: float = 1.2):
    """Generate request keys following a Zipfian (power-law) distribution.
    Higher skew means more concentration on fewer keys."""
    weights = [1.0 / (i ** skew) for i in range(1, num_keys + 1)]
    total = sum(weights)
    probabilities = [w / total for w in weights]

    cumulative = []
    running = 0.0
    for p in probabilities:
        running += p
        cumulative.append(running)

    requests = []
    for _ in range(num_requests):
        r = random.random()
        idx = bisect.bisect_left(cumulative, r)
        requests.append(f"key:{idx}")
    return requests


# ---------------------------------------------------------------------------
# Simulated distributed cache (simplified)
# ---------------------------------------------------------------------------

class DistributedCacheNode:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self._store = {}
        self.request_count = 0

    def get(self, key: str):
        self.request_count += 1
        return self._store.get(key)

    def set(self, key: str, value):
        self._store[key] = value


class SimpleDistributedCache:
    def __init__(self, num_nodes: int = 4):
        self.nodes = {}
        for i in range(num_nodes):
            nid = f"node-{i:02d}"
            self.nodes[nid] = DistributedCacheNode(nid)
        self._node_list = list(self.nodes.keys())

    def _route(self, key: str) -> str:
        h = int(hashlib.md5(key.encode()).hexdigest(), 16)
        return self._node_list[h % len(self._node_list)]

    def get(self, key: str):
        node_id = self._route(key)
        return self.nodes[node_id].get(key)

    def set(self, key: str, value):
        node_id = self._route(key)
        self.nodes[node_id].set(key, value)

    def get_load_distribution(self):
        return {nid: node.request_count for nid, node in self.nodes.items()}

    def reset_counts(self):
        for node in self.nodes.values():
            node.request_count = 0


# ---------------------------------------------------------------------------
# L1 local cache (in-process, per app server)
# ---------------------------------------------------------------------------

class L1Cache:
    """Small in-process LRU cache that sits in front of the distributed cache.
    Short TTL ensures staleness stays bounded."""

    def __init__(self, max_size: int = 100, ttl_seconds: float = 5.0):
        self._store = OrderedDict()
        self._timestamps = {}
        self._max_size = max_size
        self._ttl = ttl_seconds
        self.hits = 0
        self.misses = 0

    def get(self, key: str):
        if key in self._store:
            age = time.time() - self._timestamps[key]
            if age < self._ttl:
                self.hits += 1
                self._store.move_to_end(key)
                return self._store[key]
            else:
                del self._store[key]
                del self._timestamps[key]
        self.misses += 1
        return None

    def set(self, key: str, value):
        self._store[key] = value
        self._timestamps[key] = time.time()
        self._store.move_to_end(key)
        if len(self._store) > self._max_size:
            oldest = next(iter(self._store))
            del self._store[oldest]
            del self._timestamps[oldest]

    @property
    def hit_ratio(self):
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


# ---------------------------------------------------------------------------
# Demo: hot key problem
# ---------------------------------------------------------------------------

def demo_hot_key_problem():
    print("=" * 60)
    print("HOT KEY PROBLEM - Zipfian Traffic Distribution")
    print("=" * 60)

    cache = SimpleDistributedCache(num_nodes=4)
    num_keys = 1000
    num_requests = 50000

    for i in range(num_keys):
        cache.set(f"key:{i}", f"value-{i}")

    requests = zipfian_keys(num_keys, num_requests, skew=1.2)

    key_freq = defaultdict(int)
    for key in requests:
        cache.get(key)
        key_freq[key] += 1

    print(f"\n  {num_requests:,} requests across {num_keys} keys (Zipfian skew=1.2)")

    top_keys = sorted(key_freq.items(), key=lambda x: -x[1])[:10]
    print(f"\n  Top 10 hottest keys:")
    print(f"  {'Key':<12} {'Requests':>10} {'% of Total':>12}")
    print(f"  {'-'*36}")
    for key, count in top_keys:
        print(f"  {key:<12} {count:>10,} {count/num_requests*100:>11.1f}%")

    top_10_total = sum(c for _, c in top_keys)
    print(f"\n  Top 10 keys handle {top_10_total/num_requests*100:.1f}% of all requests")

    load = cache.get_load_distribution()
    print(f"\n  Load per cache node:")
    print(f"  {'Node':<12} {'Requests':>10} {'% of Total':>12}")
    print(f"  {'-'*36}")
    max_load = max(load.values())
    min_load = min(load.values())
    for nid in sorted(load):
        count = load[nid]
        print(f"  {nid:<12} {count:>10,} {count/num_requests*100:>11.1f}%")

    imbalance = max_load / min_load if min_load > 0 else float('inf')
    print(f"\n  Load imbalance: {imbalance:.1f}x (max/min)")
    print(f"  The node holding hot keys gets crushed while others idle.")

    return requests, cache


# ---------------------------------------------------------------------------
# Demo: L1 cache solution
# ---------------------------------------------------------------------------

def demo_l1_solution(requests):
    print("\n" + "=" * 60)
    print("L1 LOCAL CACHE - Hot Key Mitigation")
    print("=" * 60)

    cache = SimpleDistributedCache(num_nodes=4)
    num_keys = 1000
    for i in range(num_keys):
        cache.set(f"key:{i}", f"value-{i}")

    l1 = L1Cache(max_size=200, ttl_seconds=30.0)

    for key in requests:
        value = l1.get(key)
        if value is None:
            value = cache.get(key)
            if value is not None:
                l1.set(key, value)

    print(f"\n  L1 cache stats:")
    print(f"    Size: 200 entries, TTL: 30s")
    print(f"    Hits:   {l1.hits:>8,}")
    print(f"    Misses: {l1.misses:>8,}")
    print(f"    Hit ratio: {l1.hit_ratio:.1%}")

    load_with_l1 = cache.get_load_distribution()
    total_l2_requests = sum(load_with_l1.values())

    print(f"\n  Distributed cache load (after L1 absorbs hot keys):")
    print(f"  {'Node':<12} {'Requests':>10} {'% of Total':>12}")
    print(f"  {'-'*36}")
    max_load = max(load_with_l1.values())
    min_load = min(load_with_l1.values())
    for nid in sorted(load_with_l1):
        count = load_with_l1[nid]
        print(f"  {nid:<12} {count:>10,} {count/total_l2_requests*100:>11.1f}%")

    imbalance = max_load / min_load if min_load > 0 else float('inf')
    reduction = (1 - total_l2_requests / len(requests)) * 100

    print(f"\n  Load imbalance: {imbalance:.1f}x (max/min)")
    print(f"  Total L2 requests reduced by: {reduction:.1f}%")
    print(f"  L1 absorbed {len(requests) - total_l2_requests:,} requests "
          f"that would have hit the distributed cache")


# ---------------------------------------------------------------------------
# Demo: hot key detection
# ---------------------------------------------------------------------------

def demo_hot_key_detection():
    print("\n" + "=" * 60)
    print("HOT KEY DETECTION - Finding Keys That Need Attention")
    print("=" * 60)

    num_requests = 20000
    requests = zipfian_keys(500, num_requests, skew=1.5)

    window_size = 5000
    threshold_pct = 2.0

    key_counts = defaultdict(int)
    hot_keys_detected = set()

    print(f"\n  Scanning {num_requests:,} requests in windows of {window_size:,}")
    print(f"  Threshold: any key exceeding {threshold_pct}% of window is 'hot'")
    print(f"\n  {'Window':<10} {'Hot Keys Found':>16} {'Hottest Key':>14} {'Its %':>8}")
    print(f"  {'-'*50}")

    for i, key in enumerate(requests):
        key_counts[key] += 1

        if (i + 1) % window_size == 0:
            window_hot = []
            for k, c in key_counts.items():
                pct = c / window_size * 100
                if pct > threshold_pct:
                    window_hot.append((k, pct))
                    hot_keys_detected.add(k)

            window_hot.sort(key=lambda x: -x[1])
            hottest = window_hot[0] if window_hot else ("none", 0)
            window_num = (i + 1) // window_size
            print(f"  {window_num:<10} {len(window_hot):>16} "
                  f"{hottest[0]:>14} {hottest[1]:>7.1f}%")
            key_counts.clear()

    print(f"\n  Total unique hot keys detected: {len(hot_keys_detected)}")
    print(f"  These keys should be promoted to L1 local caches or")
    print(f"  replicated across multiple nodes to spread the load.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    random.seed(42)
    requests, _ = demo_hot_key_problem()
    demo_l1_solution(requests)
    demo_hot_key_detection()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("""
  Real traffic follows Zipfian distributions - a few keys get
  hammered while most sit quietly. The L1 local cache is the
  simplest and most effective defense:

  - No network hop for hot keys (served from app server memory)
  - Distributed cache load drops dramatically
  - Node imbalance drops from extreme to manageable
  - Trade-off: L1 data can be stale for up to TTL seconds
    """)


if __name__ == "__main__":
    main()
