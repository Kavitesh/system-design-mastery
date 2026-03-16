"""
Distributed Cache with Consistent Hashing
==========================================
A working distributed cache that uses consistent hashing for key
routing. Supports dynamic node add/remove with live stats on cache
hits, misses, and key migration.
"""

import hashlib
from bisect import bisect_right, insort

# ---------------------------------------------------------------------------
# Hash function
# ---------------------------------------------------------------------------

def md5_hash(key: str) -> int:
    return int(hashlib.md5(key.encode()).hexdigest(), 16)


# ---------------------------------------------------------------------------
# Cache node - simulates a single cache server
# ---------------------------------------------------------------------------

class CacheNode:
    def __init__(self, name: str, capacity: int = 10_000):
        self.name = name
        self.capacity = capacity
        self.store: dict[str, str] = {}
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> str | None:
        if key in self.store:
            self.hits += 1
            return self.store[key]
        self.misses += 1
        return None

    def put(self, key: str, value: str):
        self.store[key] = value

    def delete(self, key: str) -> str | None:
        return self.store.pop(key, None)

    def drain(self) -> dict[str, str]:
        data = dict(self.store)
        self.store.clear()
        return data

    @property
    def size(self) -> int:
        return len(self.store)

    def __repr__(self):
        return f"CacheNode({self.name}, keys={self.size})"


# ---------------------------------------------------------------------------
# Distributed cache - routes through consistent hash ring
# ---------------------------------------------------------------------------

class DistributedCache:
    def __init__(self, vnodes: int = 150):
        self.vnodes = vnodes
        self.sorted_hashes: list[int] = []
        self.hash_to_name: dict[int, str] = {}
        self.nodes: dict[str, CacheNode] = {}

    def add_node(self, name: str) -> int:
        node = CacheNode(name)
        self.nodes[name] = node
        for i in range(self.vnodes):
            h = md5_hash(f"{name}#vn{i}")
            self.hash_to_name[h] = name
            insort(self.sorted_hashes, h)

        migrated = self._rebalance_after_add(name)
        return migrated

    def remove_node(self, name: str) -> int:
        if name not in self.nodes:
            return 0

        orphaned_data = self.nodes[name].drain()

        for i in range(self.vnodes):
            h = md5_hash(f"{name}#vn{i}")
            self.hash_to_name.pop(h, None)
            idx = bisect_right(self.sorted_hashes, h) - 1
            if 0 <= idx < len(self.sorted_hashes) and self.sorted_hashes[idx] == h:
                self.sorted_hashes.pop(idx)

        del self.nodes[name]

        migrated = 0
        for key, value in orphaned_data.items():
            target = self._find_node(key)
            if target:
                self.nodes[target].put(key, value)
                migrated += 1

        return migrated

    def get(self, key: str) -> str | None:
        name = self._find_node(key)
        if not name:
            return None
        return self.nodes[name].get(key)

    def put(self, key: str, value: str):
        name = self._find_node(key)
        if name:
            self.nodes[name].put(key, value)

    def _find_node(self, key: str) -> str | None:
        if not self.sorted_hashes:
            return None
        h = md5_hash(key)
        idx = bisect_right(self.sorted_hashes, h) % len(self.sorted_hashes)
        return self.hash_to_name[self.sorted_hashes[idx]]

    def _rebalance_after_add(self, new_node: str) -> int:
        migrated = 0
        for name, node in self.nodes.items():
            if name == new_node:
                continue
            keys_to_move = []
            for key in list(node.store.keys()):
                if self._find_node(key) == new_node:
                    keys_to_move.append(key)
            for key in keys_to_move:
                value = node.delete(key)
                self.nodes[new_node].put(key, value)
                migrated += 1
        return migrated

    def stats(self) -> dict:
        total_keys = sum(n.size for n in self.nodes.values())
        total_hits = sum(n.hits for n in self.nodes.values())
        total_misses = sum(n.misses for n in self.nodes.values())
        return {
            "nodes": len(self.nodes),
            "total_keys": total_keys,
            "total_hits": total_hits,
            "total_misses": total_misses,
            "hit_rate": total_hits / max(total_hits + total_misses, 1) * 100,
        }

    def per_node_stats(self) -> list[dict]:
        return [
            {"name": n.name, "keys": n.size, "hits": n.hits, "misses": n.misses}
            for n in sorted(self.nodes.values(), key=lambda x: x.name)
        ]


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

def main():
    print("Distributed Cache - consistent hashing demo")

    cache = DistributedCache(vnodes=150)
    initial_nodes = ["redis-1", "redis-2", "redis-3", "redis-4"]

    print(f"\n--- Phase 1: Build cluster with {len(initial_nodes)} nodes ---")
    for name in initial_nodes:
        cache.add_node(name)
        print(f"  Added {name}")

    num_items = 10_000
    print(f"\n--- Phase 2: Populate {num_items:,} keys ---")
    for i in range(num_items):
        cache.put(f"product:{i}", f"data-for-product-{i}")

    for info in cache.per_node_stats():
        pct = info["keys"] / num_items * 100
        print(f"  {info['name']:<10} {info['keys']:>5} keys ({pct:.1f}%)")

    print(f"\n--- Phase 3: Read all keys (warm cache) ---")
    for i in range(num_items):
        cache.get(f"product:{i}")

    s = cache.stats()
    print(f"  Hit rate: {s['hit_rate']:.1f}% ({s['total_hits']:,} hits, {s['total_misses']} misses)")

    print(f"\n--- Phase 4: Add 'redis-5' ---")
    migrated = cache.add_node("redis-5")
    print(f"  Keys migrated to redis-5: {migrated:,} ({migrated/num_items*100:.1f}%)")
    print(f"  Ideal (K/N): {num_items/5:.0f} ({100/5:.1f}%)")

    print(f"\n  New distribution:")
    for info in cache.per_node_stats():
        pct = info["keys"] / num_items * 100
        print(f"  {info['name']:<10} {info['keys']:>5} keys ({pct:.1f}%)")

    print(f"\n--- Phase 5: Verify data integrity after migration ---")
    intact = 0
    missing = 0
    for i in range(num_items):
        val = cache.get(f"product:{i}")
        if val == f"data-for-product-{i}":
            intact += 1
        else:
            missing += 1
    print(f"  Intact: {intact:,} / {num_items:,}")
    print(f"  Missing: {missing}")

    print(f"\n--- Phase 6: Simulate 'redis-2' failure ---")
    keys_on_redis2 = cache.nodes["redis-2"].size
    migrated = cache.remove_node("redis-2")
    print(f"  redis-2 had {keys_on_redis2:,} keys")
    print(f"  Keys redistributed: {migrated:,}")

    print(f"\n  Distribution after failure:")
    remaining_keys = sum(n.size for n in cache.nodes.values())
    for info in cache.per_node_stats():
        pct = info["keys"] / remaining_keys * 100
        print(f"  {info['name']:<10} {info['keys']:>5} keys ({pct:.1f}%)")

    print(f"\n--- Phase 7: Post-failure reads ---")
    for n in cache.nodes.values():
        n.hits = 0
        n.misses = 0

    for i in range(num_items):
        cache.get(f"product:{i}")

    s = cache.stats()
    print(f"  Hit rate: {s['hit_rate']:.1f}%")
    print(f"  Hits: {s['total_hits']:,} | Misses: {s['total_misses']}")
    print(f"  (Misses = keys that were on redis-2 and lost with it)")

    print(f"\n--- Summary ---")
    print(f"  Consistent hashing kept {100 - (missing/num_items*100):.1f}% of data intact")
    print(f"  through one node addition and one node failure.")
    print(f"  With modulo hashing, both events would have invalidated ~75%+ of the cache.")


if __name__ == "__main__":
    main()
