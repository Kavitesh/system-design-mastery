"""
Cache Eviction Policies
========================
Implements LRU, LFU, and FIFO caches from scratch, then runs a
Zipf-distributed workload through each to compare hit rates.
LRU wins for most real-world workloads.

Run: python eviction_policies.py
"""

import random
from collections import OrderedDict, defaultdict


# ---------------------------------------------------------------------------
# LRU Cache (Least Recently Used)
# ---------------------------------------------------------------------------

class LRUCache:
    def __init__(self, capacity):
        self.capacity = capacity
        self._data = OrderedDict()

    def get(self, key):
        if key in self._data:
            self._data.move_to_end(key)
            return self._data[key]
        return None

    def put(self, key, value):
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = value
        if len(self._data) > self.capacity:
            evicted, _ = self._data.popitem(last=False)
            return evicted
        return None

    def contents(self):
        return list(self._data.keys())


# ---------------------------------------------------------------------------
# LFU Cache (Least Frequently Used)
# ---------------------------------------------------------------------------

class LFUCache:
    def __init__(self, capacity):
        self.capacity = capacity
        self._data = {}
        self._freq = defaultdict(int)
        self._order = []

    def get(self, key):
        if key in self._data:
            self._freq[key] += 1
            return self._data[key]
        return None

    def put(self, key, value):
        if self.capacity <= 0:
            return None
        if key in self._data:
            self._data[key] = value
            self._freq[key] += 1
            return None
        evicted = None
        if len(self._data) >= self.capacity:
            min_f = min(self._freq[k] for k in self._data)
            for k in self._order:
                if k in self._data and self._freq[k] == min_f:
                    evicted = k
                    del self._data[k]
                    del self._freq[k]
                    self._order.remove(k)
                    break
        self._data[key] = value
        self._freq[key] = 1
        self._order.append(key)
        return evicted

    def contents(self):
        return [(k, self._freq[k]) for k in self._data]


# ---------------------------------------------------------------------------
# FIFO Cache (First In, First Out)
# ---------------------------------------------------------------------------

class FIFOCache:
    def __init__(self, capacity):
        self.capacity = capacity
        self._data = OrderedDict()

    def get(self, key):
        return self._data.get(key)

    def put(self, key, value):
        if key in self._data:
            self._data[key] = value
            return None
        self._data[key] = value
        if len(self._data) > self.capacity:
            evicted, _ = self._data.popitem(last=False)
            return evicted
        return None

    def contents(self):
        return list(self._data.keys())


# ---------------------------------------------------------------------------
# Interactive demos
# ---------------------------------------------------------------------------

def demo_lru():
    print("=" * 60)
    print("LRU (Least Recently Used) - Capacity: 3")
    print("=" * 60)
    cache = LRUCache(3)
    for op, key, val in [("PUT","A","a"),("PUT","B","b"),("PUT","C","c"),
                          ("GET","A",None),("PUT","D","d"),("PUT","E","e")]:
        if op == "PUT":
            ev = cache.put(key, val)
            evmsg = f" -> evicted '{ev}'" if ev else ""
            print(f"  PUT '{key}'{evmsg:<20} cache: {cache.contents()}")
        else:
            r = cache.get(key)
            print(f"  GET '{key}' = {'HIT' if r else 'MISS':<20} cache: {cache.contents()}")
    print("\n  Accessing 'A' saved it. 'B' was evicted as least recently used.")


def demo_lfu():
    print("\n" + "=" * 60)
    print("LFU (Least Frequently Used) - Capacity: 3")
    print("=" * 60)
    cache = LFUCache(3)
    cache.put("A", "a"); cache.put("B", "b"); cache.put("C", "c")
    for _ in range(5): cache.get("A")
    for _ in range(2): cache.get("B")
    print(f"  Access counts: A=5x, B=2x, C=1x")
    print(f"  Contents: {cache.contents()}")
    ev = cache.put("D", "d")
    print(f"  PUT 'D' -> evicted '{ev}' (lowest freq)")
    ev = cache.put("E", "e")
    print(f"  PUT 'E' -> evicted '{ev}' (next lowest)")
    print(f"  Contents: {cache.contents()}")
    print("\n  'A' survived because it was accessed 5 times.")


def demo_fifo():
    print("\n" + "=" * 60)
    print("FIFO (First In, First Out) - Capacity: 3")
    print("=" * 60)
    cache = FIFOCache(3)
    for op, key, val in [("PUT","A","a"),("PUT","B","b"),("PUT","C","c"),
                          ("GET","A",None),("GET","A",None),("PUT","D","d")]:
        if op == "PUT":
            ev = cache.put(key, val)
            evmsg = f" -> evicted '{ev}'" if ev else ""
            print(f"  PUT '{key}'{evmsg:<20} cache: {cache.contents()}")
        else:
            r = cache.get(key)
            print(f"  GET '{key}' = {'HIT' if r else 'MISS':<20} cache: {cache.contents()}")
    print("\n  FIFO evicted 'A' despite 2 accesses. It ignores usage patterns.")


# ---------------------------------------------------------------------------
# Performance comparison with Zipf workload
# ---------------------------------------------------------------------------

def performance_comparison():
    print("\n" + "=" * 60)
    print("HIT RATE COMPARISON - Zipf workload (2000 ops, 50 keys, cache=10)")
    print("=" * 60)
    random.seed(42)
    keys = [f"k:{i}" for i in range(50)]
    weights = [1.0 / (i + 1) for i in range(50)]
    sequence = random.choices(keys, weights=weights, k=2000)

    caches = {"LRU": LRUCache(10), "LFU": LFUCache(10), "FIFO": FIFOCache(10)}
    hits = {n: 0 for n in caches}

    for key in sequence:
        for name, c in caches.items():
            if c.get(key) is not None:
                hits[name] += 1
            else:
                c.put(key, key)

    print(f"\n  {'Policy':<8} {'Hits':>6} {'Hit Rate':>10}")
    print(f"  {'-'*28}")
    for name in caches:
        ratio = hits[name] / len(sequence)
        bar = "#" * int(ratio * 30)
        print(f"  {name:<8} {hits[name]:>6} {ratio:>9.1%}  {bar}")
    print(f"\n  LRU and LFU handle skewed distributions well.")
    print(f"  FIFO trails because it ignores which keys are popular.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    demo_lru()
    demo_lfu()
    demo_fifo()
    performance_comparison()
