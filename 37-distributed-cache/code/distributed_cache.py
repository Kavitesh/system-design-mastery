"""
Distributed Cache with Consistent Hashing
==========================================
A multi-node in-memory cache that uses consistent hashing to partition
keys across nodes. Supports GET, SET, DELETE, and demonstrates what
happens when nodes join or leave the cluster - how many keys actually
move vs the catastrophe you'd get with modulo hashing.

Run: python distributed_cache.py
"""

import hashlib
import bisect
import time
from collections import defaultdict


# ---------------------------------------------------------------------------
# Consistent hash ring
# ---------------------------------------------------------------------------

class HashRing:
    """Consistent hash ring with virtual nodes for balanced key distribution."""

    def __init__(self, nodes=None, vnodes=150):
        self._vnodes = vnodes
        self._ring = []          # sorted list of (position, node_id)
        self._positions = []     # sorted positions for bisect
        self._node_map = {}      # position -> node_id
        self._nodes = set()
        for node in (nodes or []):
            self.add_node(node)

    def _hash(self, key: str) -> int:
        return int(hashlib.md5(key.encode()).hexdigest(), 16)

    def add_node(self, node_id: str):
        self._nodes.add(node_id)
        for i in range(self._vnodes):
            vnode_key = f"{node_id}#vn{i}"
            pos = self._hash(vnode_key)
            self._node_map[pos] = node_id
            bisect.insort(self._positions, pos)

    def remove_node(self, node_id: str):
        self._nodes.discard(node_id)
        positions_to_remove = [
            pos for pos, nid in self._node_map.items() if nid == node_id
        ]
        for pos in positions_to_remove:
            del self._node_map[pos]
            self._positions.remove(pos)

    def get_node(self, key: str) -> str:
        if not self._positions:
            raise RuntimeError("No nodes in the ring")
        h = self._hash(key)
        idx = bisect.bisect_right(self._positions, h)
        if idx == len(self._positions):
            idx = 0
        return self._node_map[self._positions[idx]]

    @property
    def nodes(self):
        return set(self._nodes)


# ---------------------------------------------------------------------------
# Cache node - a single server's in-memory store
# ---------------------------------------------------------------------------

class CacheNode:
    """Simulates a single cache server with a fixed memory capacity."""

    def __init__(self, node_id: str, max_keys: int = 10000):
        self.node_id = node_id
        self.max_keys = max_keys
        self._store = {}
        self._access_order = []
        self.stats = {"hits": 0, "misses": 0, "sets": 0, "deletes": 0}

    def get(self, key: str):
        if key in self._store:
            self.stats["hits"] += 1
            return self._store[key]
        self.stats["misses"] += 1
        return None

    def set(self, key: str, value, ttl: int = 0):
        if len(self._store) >= self.max_keys and key not in self._store:
            self._evict_lru()
        self._store[key] = value
        self.stats["sets"] += 1

    def delete(self, key: str):
        if key in self._store:
            del self._store[key]
            self.stats["deletes"] += 1
            return True
        return False

    def _evict_lru(self):
        if self._store:
            oldest_key = next(iter(self._store))
            del self._store[oldest_key]

    @property
    def key_count(self):
        return len(self._store)


# ---------------------------------------------------------------------------
# Distributed cache - ties the ring and nodes together
# ---------------------------------------------------------------------------

class DistributedCache:
    """Multi-node cache using consistent hashing for key routing."""

    def __init__(self, node_ids, vnodes=150):
        self._ring = HashRing(vnodes=vnodes)
        self._nodes = {}
        for nid in node_ids:
            self._nodes[nid] = CacheNode(nid)
            self._ring.add_node(nid)

    def set(self, key: str, value, ttl: int = 0):
        node_id = self._ring.get_node(key)
        self._nodes[node_id].set(key, value, ttl)

    def get(self, key: str):
        node_id = self._ring.get_node(key)
        return self._nodes[node_id].get(key)

    def delete(self, key: str):
        node_id = self._ring.get_node(key)
        return self._nodes[node_id].delete(key)

    def add_node(self, node_id: str):
        self._nodes[node_id] = CacheNode(node_id)
        self._ring.add_node(node_id)

    def remove_node(self, node_id: str):
        self._ring.remove_node(node_id)
        del self._nodes[node_id]

    def get_distribution(self, keys):
        dist = defaultdict(int)
        for key in keys:
            node_id = self._ring.get_node(key)
            dist[node_id] += 1
        return dict(dist)

    def print_stats(self):
        print(f"\n  {'Node':<12} {'Keys':>6} {'Hits':>6} {'Misses':>6} {'Sets':>6}")
        print(f"  {'-'*42}")
        for nid, node in sorted(self._nodes.items()):
            s = node.stats
            print(f"  {nid:<12} {node.key_count:>6} {s['hits']:>6} "
                  f"{s['misses']:>6} {s['sets']:>6}")


# ---------------------------------------------------------------------------
# Demo: basic operations
# ---------------------------------------------------------------------------

def demo_basic_operations():
    print("=" * 60)
    print("DISTRIBUTED CACHE - Basic Operations")
    print("=" * 60)

    nodes = ["cache-01", "cache-02", "cache-03", "cache-04"]
    cache = DistributedCache(nodes)

    test_data = {
        "user:1001": {"name": "Alice", "plan": "premium"},
        "user:1002": {"name": "Bob", "plan": "free"},
        "session:abc": {"user_id": 1001, "expires": 3600},
        "product:42": {"title": "Widget", "price": 9.99},
        "config:features": {"dark_mode": True, "beta": False},
    }

    print("\n  Writing 5 keys...")
    for key, value in test_data.items():
        cache.set(key, value)
        target = cache._ring.get_node(key)
        print(f"    {key:<22} -> {target}")

    print("\n  Reading keys back...")
    for key in test_data:
        result = cache.get(key)
        status = "HIT" if result else "MISS"
        print(f"    {key:<22} -> {status}")

    cache.delete("session:abc")
    result = cache.get("session:abc")
    print(f"\n  After DELETE session:abc -> {'MISS' if result is None else 'HIT'}")

    cache.print_stats()


# ---------------------------------------------------------------------------
# Demo: key distribution across nodes
# ---------------------------------------------------------------------------

def demo_distribution():
    print("\n" + "=" * 60)
    print("KEY DISTRIBUTION - 10,000 Keys Across 4 Nodes")
    print("=" * 60)

    nodes = ["cache-01", "cache-02", "cache-03", "cache-04"]
    cache = DistributedCache(nodes, vnodes=150)
    keys = [f"key:{i}" for i in range(10000)]

    dist = cache.get_distribution(keys)
    ideal = 10000 / len(nodes)

    print(f"\n  Ideal per node: {ideal:.0f} keys")
    print(f"\n  {'Node':<12} {'Keys':>6} {'% of Total':>10} {'Deviation':>10}")
    print(f"  {'-'*40}")
    for node_id in sorted(dist):
        count = dist[node_id]
        pct = count / 10000 * 100
        dev = (count - ideal) / ideal * 100
        print(f"  {node_id:<12} {count:>6} {pct:>9.1f}% {dev:>+9.1f}%")

    max_dev = max(abs((c - ideal) / ideal * 100) for c in dist.values())
    print(f"\n  Max deviation from ideal: {max_dev:.1f}%")
    print(f"  150 virtual nodes keeps this under ~10% for 4 physical nodes")


# ---------------------------------------------------------------------------
# Demo: node add/remove - key movement
# ---------------------------------------------------------------------------

def demo_node_changes():
    print("\n" + "=" * 60)
    print("NODE ADD/REMOVE - Key Movement")
    print("=" * 60)

    keys = [f"key:{i}" for i in range(10000)]

    # Baseline: 4 nodes
    ring_before = HashRing(["cache-01", "cache-02", "cache-03", "cache-04"], vnodes=150)
    mapping_before = {k: ring_before.get_node(k) for k in keys}

    # Add a 5th node
    ring_after = HashRing(["cache-01", "cache-02", "cache-03", "cache-04", "cache-05"], vnodes=150)
    mapping_after = {k: ring_after.get_node(k) for k in keys}

    moved = sum(1 for k in keys if mapping_before[k] != mapping_after[k])
    pct_moved = moved / len(keys) * 100
    modulo_moved = (4 / 5) * 100  # theoretical modulo hashing movement

    print(f"\n  Adding node 'cache-05' to a 4-node cluster:")
    print(f"    Keys moved (consistent hashing): {moved:,} / {len(keys):,} ({pct_moved:.1f}%)")
    print(f"    Keys moved (modulo hashing):      ~{modulo_moved:.0f}%")
    print(f"    Improvement: {modulo_moved / pct_moved:.1f}x fewer keys disrupted")

    # Remove a node
    ring_removed = HashRing(["cache-01", "cache-02", "cache-04"], vnodes=150)
    mapping_removed = {k: ring_removed.get_node(k) for k in keys}

    moved_rm = sum(1 for k in keys if mapping_before[k] != mapping_removed[k])
    pct_rm = moved_rm / len(keys) * 100

    print(f"\n  Removing node 'cache-03' from a 4-node cluster:")
    print(f"    Keys moved: {moved_rm:,} / {len(keys):,} ({pct_rm:.1f}%)")
    print(f"    Only cache-03's keys redistributed to remaining nodes")


# ---------------------------------------------------------------------------
# Demo: modulo vs consistent hashing comparison
# ---------------------------------------------------------------------------

def demo_modulo_vs_consistent():
    print("\n" + "=" * 60)
    print("MODULO vs CONSISTENT HASHING")
    print("=" * 60)

    keys = [f"item:{i}" for i in range(50000)]

    print(f"\n  {'Cluster Change':<28} {'Modulo Moved':>14} {'Consistent Moved':>18}")
    print(f"  {'-'*62}")

    for old_n, new_n, label in [
        (4, 5, "4 -> 5 nodes (add 1)"),
        (10, 11, "10 -> 11 nodes (add 1)"),
        (10, 9, "10 -> 9 nodes (remove 1)"),
        (50, 51, "50 -> 51 nodes (add 1)"),
    ]:
        ring_old = HashRing([f"n{i}" for i in range(old_n)], vnodes=150)
        ring_new = HashRing([f"n{i}" for i in range(new_n)], vnodes=150)

        modulo_moved = sum(
            1 for k in keys
            if (int(hashlib.md5(k.encode()).hexdigest(), 16) % old_n) !=
               (int(hashlib.md5(k.encode()).hexdigest(), 16) % new_n)
        )
        consistent_moved = sum(
            1 for k in keys if ring_old.get_node(k) != ring_new.get_node(k)
        )

        m_pct = modulo_moved / len(keys) * 100
        c_pct = consistent_moved / len(keys) * 100
        print(f"  {label:<28} {m_pct:>12.1f}% {c_pct:>16.1f}%")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    demo_basic_operations()
    demo_distribution()
    demo_node_changes()
    demo_modulo_vs_consistent()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("""
  Consistent hashing is what makes distributed caches practical.
  Without it, every scaling event (add/remove node) causes a
  near-total cache miss storm. With it, only K/N keys move -
  the theoretical minimum.

  Key design decisions:
  - 150 virtual nodes per physical node for balanced distribution
  - MD5 hash for good avalanche properties (not for crypto)
  - Client-side routing - no proxy in the hot path
    """)


if __name__ == "__main__":
    main()
