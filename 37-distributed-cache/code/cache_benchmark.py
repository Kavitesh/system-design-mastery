"""
Cache Benchmark
================
Measures hit ratio, latency percentiles, and throughput for different
eviction policies (LRU vs LFU) under uniform and Zipfian workloads.
Shows why LFU beats LRU for skewed access patterns and why LRU is
good enough for everything else.

Run: python cache_benchmark.py
"""

import time
import random
import bisect
from collections import OrderedDict, defaultdict


# ---------------------------------------------------------------------------
# LRU cache implementation
# ---------------------------------------------------------------------------

class LRUCache:
    def __init__(self, capacity: int):
        self._store = OrderedDict()
        self._capacity = capacity
        self.hits = 0
        self.misses = 0

    def get(self, key: str):
        if key in self._store:
            self.hits += 1
            self._store.move_to_end(key)
            return self._store[key]
        self.misses += 1
        return None

    def set(self, key: str, value):
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = value
        if len(self._store) > self._capacity:
            self._store.popitem(last=False)

    @property
    def hit_ratio(self):
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def reset(self):
        self._store.clear()
        self.hits = 0
        self.misses = 0


# ---------------------------------------------------------------------------
# LFU cache implementation
# ---------------------------------------------------------------------------

class LFUCache:
    def __init__(self, capacity: int):
        self._capacity = capacity
        self._store = {}
        self._freq = defaultdict(int)
        self._freq_buckets = defaultdict(OrderedDict)
        self._min_freq = 0
        self.hits = 0
        self.misses = 0

    def get(self, key: str):
        if key in self._store:
            self.hits += 1
            self._touch(key)
            return self._store[key]
        self.misses += 1
        return None

    def set(self, key: str, value):
        if self._capacity <= 0:
            return
        if key in self._store:
            self._store[key] = value
            self._touch(key)
            return
        if len(self._store) >= self._capacity:
            self._evict()
        self._store[key] = value
        self._freq[key] = 1
        self._freq_buckets[1][key] = True
        self._min_freq = 1

    def _touch(self, key: str):
        f = self._freq[key]
        del self._freq_buckets[f][key]
        if not self._freq_buckets[f]:
            del self._freq_buckets[f]
            if self._min_freq == f:
                self._min_freq = f + 1
        self._freq[key] = f + 1
        self._freq_buckets[f + 1][key] = True

    def _evict(self):
        bucket = self._freq_buckets[self._min_freq]
        evicted_key, _ = bucket.popitem(last=False)
        if not bucket:
            del self._freq_buckets[self._min_freq]
        del self._store[evicted_key]
        del self._freq[evicted_key]

    @property
    def hit_ratio(self):
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def reset(self):
        self._store.clear()
        self._freq.clear()
        self._freq_buckets.clear()
        self._min_freq = 0
        self.hits = 0
        self.misses = 0


# ---------------------------------------------------------------------------
# Workload generators
# ---------------------------------------------------------------------------

def uniform_workload(num_keys: int, num_ops: int):
    return [f"key:{random.randint(0, num_keys - 1)}" for _ in range(num_ops)]


def zipfian_workload(num_keys: int, num_ops: int, skew: float = 1.2):
    weights = [1.0 / (i ** skew) for i in range(1, num_keys + 1)]
    total = sum(weights)
    cumulative = []
    running = 0.0
    for w in weights:
        running += w / total
        cumulative.append(running)

    keys = []
    for _ in range(num_ops):
        r = random.random()
        idx = bisect.bisect_left(cumulative, r)
        keys.append(f"key:{idx}")
    return keys


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------

def run_benchmark(cache, keys, label: str):
    """Populate on miss, read on hit. Returns (hit_ratio, latencies)."""
    latencies = []

    for key in keys:
        start = time.perf_counter()
        result = cache.get(key)
        if result is None:
            cache.set(key, f"value-for-{key}")
        elapsed = (time.perf_counter() - start) * 1_000_000  # microseconds
        latencies.append(elapsed)

    latencies.sort()
    n = len(latencies)
    p50 = latencies[int(n * 0.50)]
    p95 = latencies[int(n * 0.95)]
    p99 = latencies[int(n * 0.99)]
    throughput = n / (sum(latencies) / 1_000_000)  # ops per second

    return {
        "label": label,
        "hit_ratio": cache.hit_ratio,
        "hits": cache.hits,
        "misses": cache.misses,
        "p50_us": p50,
        "p95_us": p95,
        "p99_us": p99,
        "throughput": throughput,
    }


# ---------------------------------------------------------------------------
# Demo: LRU vs LFU under different workloads
# ---------------------------------------------------------------------------

def demo_eviction_comparison():
    print("=" * 60)
    print("LRU vs LFU - Eviction Policy Comparison")
    print("=" * 60)

    num_keys = 10000
    cache_size = 1000  # 10% of key space
    num_ops = 100000

    random.seed(42)

    configs = [
        ("Uniform", uniform_workload(num_keys, num_ops)),
        ("Zipfian (skew=1.0)", zipfian_workload(num_keys, num_ops, skew=1.0)),
        ("Zipfian (skew=1.5)", zipfian_workload(num_keys, num_ops, skew=1.5)),
        ("Zipfian (skew=2.0)", zipfian_workload(num_keys, num_ops, skew=2.0)),
    ]

    print(f"\n  Key space: {num_keys:,} keys")
    print(f"  Cache capacity: {cache_size:,} entries ({cache_size/num_keys*100:.0f}% of key space)")
    print(f"  Operations: {num_ops:,}")

    print(f"\n  {'Workload':<22} {'Policy':<6} {'Hit Ratio':>10} "
          f"{'p50':>8} {'p99':>8} {'Throughput':>14}")
    print(f"  {'-'*72}")

    for workload_name, keys in configs:
        lru = LRUCache(cache_size)
        lfu = LFUCache(cache_size)

        lru_result = run_benchmark(lru, keys, "LRU")
        lfu_result = run_benchmark(lfu, keys, "LFU")

        for r in [lru_result, lfu_result]:
            print(f"  {workload_name:<22} {r['label']:<6} {r['hit_ratio']:>9.1%} "
                  f"{r['p50_us']:>7.1f}us {r['p99_us']:>7.1f}us "
                  f"{r['throughput']:>11,.0f} ops/s")
        print()


# ---------------------------------------------------------------------------
# Demo: cache size vs hit ratio
# ---------------------------------------------------------------------------

def demo_cache_sizing():
    print("=" * 60)
    print("CACHE SIZING - How Capacity Affects Hit Ratio")
    print("=" * 60)

    num_keys = 10000
    num_ops = 50000
    random.seed(42)

    keys = zipfian_workload(num_keys, num_ops, skew=1.2)
    sizes = [100, 250, 500, 1000, 2000, 3000, 5000, 8000]

    print(f"\n  Key space: {num_keys:,} keys, Zipfian skew=1.2")
    print(f"\n  {'Cache Size':>12} {'% of Keys':>10} {'LRU Hit%':>10} {'LFU Hit%':>10} {'Winner':>8}")
    print(f"  {'-'*52}")

    for size in sizes:
        lru = LRUCache(size)
        lfu = LFUCache(size)

        for key in keys:
            if lru.get(key) is None:
                lru.set(key, "v")
            if lfu.get(key) is None:
                lfu.set(key, "v")

        lru_hr = lru.hit_ratio
        lfu_hr = lfu.hit_ratio
        winner = "LFU" if lfu_hr > lru_hr + 0.001 else ("LRU" if lru_hr > lfu_hr + 0.001 else "tie")

        print(f"  {size:>12,} {size/num_keys*100:>9.0f}% {lru_hr:>9.1%} "
              f"{lfu_hr:>9.1%} {winner:>8}")

    print(f"""
  The Pareto effect is clear: caching just 10% of the key space
  captures 80%+ of requests under Zipfian traffic. Doubling cache
  size beyond that gives diminishing returns. Size your cache based
  on your working set, not your total data set.
    """)


# ---------------------------------------------------------------------------
# Demo: scan pollution (LRU weakness)
# ---------------------------------------------------------------------------

def demo_scan_pollution():
    print("=" * 60)
    print("SCAN POLLUTION - LRU's Achilles Heel")
    print("=" * 60)

    cache_size = 500
    num_hot_keys = 200
    num_ops = 20000
    scan_size = 2000

    random.seed(42)

    hot_keys = [f"hot:{i}" for i in range(num_hot_keys)]

    # Phase 1: warm up with hot keys
    print(f"\n  Phase 1: Warm up cache with {num_hot_keys} hot keys ({num_ops:,} ops)")
    lru = LRUCache(cache_size)
    lfu = LFUCache(cache_size)

    for _ in range(num_ops):
        key = random.choice(hot_keys)
        if lru.get(key) is None:
            lru.set(key, "v")
        if lfu.get(key) is None:
            lfu.set(key, "v")

    lru_before = lru.hit_ratio
    lfu_before = lfu.hit_ratio
    print(f"  LRU hit ratio: {lru_before:.1%}")
    print(f"  LFU hit ratio: {lfu_before:.1%}")

    # Phase 2: sequential scan (batch job reads every key once)
    print(f"\n  Phase 2: Sequential scan of {scan_size} cold keys (batch job)")
    lru.hits = 0
    lru.misses = 0
    lfu.hits = 0
    lfu.misses = 0

    for i in range(scan_size):
        cold_key = f"scan:{i}"
        if lru.get(cold_key) is None:
            lru.set(cold_key, "v")
        if lfu.get(cold_key) is None:
            lfu.set(cold_key, "v")

    # Phase 3: go back to hot keys
    print(f"\n  Phase 3: Resume hot key access ({num_ops:,} ops)")
    lru.hits = 0
    lru.misses = 0
    lfu.hits = 0
    lfu.misses = 0

    for _ in range(num_ops):
        key = random.choice(hot_keys)
        if lru.get(key) is None:
            lru.set(key, "v")
        if lfu.get(key) is None:
            lfu.set(key, "v")

    print(f"  LRU hit ratio after scan: {lru.hit_ratio:.1%}")
    print(f"  LFU hit ratio after scan: {lfu.hit_ratio:.1%}")

    print(f"""
  The sequential scan evicted all hot keys from LRU (they were
  'least recently used' during the scan). LFU kept them because
  they had high frequency counts that a single scan access can't
  overcome. This is why Redis added LFU eviction in version 4.0.
    """)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    demo_eviction_comparison()
    demo_cache_sizing()
    demo_scan_pollution()

    print("=" * 60)
    print("RECOMMENDATIONS")
    print("=" * 60)
    print("""
  1. Start with LRU. It works for most workloads and is simpler
     to reason about. Redis defaults to allkeys-lru for a reason.

  2. Switch to LFU if you see scan pollution in your metrics -
     periodic hit ratio drops that correlate with batch jobs.

  3. Size your cache at 10-20% of your key space for Zipfian
     traffic. Going bigger has diminishing returns.

  4. Always measure. These benchmarks use synthetic data -
     your actual access patterns may look completely different.
    """)


if __name__ == "__main__":
    main()
