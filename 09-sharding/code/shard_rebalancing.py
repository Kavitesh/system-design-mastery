"""
Shard Rebalancing with Consistent Hashing
==========================================
Demonstrates adding and removing shards from a consistent hash ring
with virtual nodes. Compares data migration cost against naive modulo
hashing to show why consistent hashing is essential for production
sharding.

    python shard_rebalancing.py
"""

import hashlib
import bisect

# ---------------------------------------------------------------------------
#   Consistent Hash Ring
# ---------------------------------------------------------------------------

class ConsistentHashRing:
    """
    A consistent hash ring with configurable virtual nodes per physical
    shard. More virtual nodes means better distribution at the cost of
    slightly more memory for the ring.
    """

    def __init__(self, virtual_nodes=150):
        self.virtual_nodes = virtual_nodes
        self.ring = []
        self.ring_map = {}
        self.shards = set()

    def _hash(self, key):
        return int(hashlib.sha256(key.encode()).hexdigest(), 16)

    def add_shard(self, shard_name):
        self.shards.add(shard_name)
        for i in range(self.virtual_nodes):
            vnode_key = f"{shard_name}:vn{i}"
            h = self._hash(vnode_key)
            self.ring_map[h] = shard_name
            bisect.insort(self.ring, h)

    def remove_shard(self, shard_name):
        self.shards.discard(shard_name)
        to_remove = []
        for h, s in self.ring_map.items():
            if s == shard_name:
                to_remove.append(h)
        for h in to_remove:
            del self.ring_map[h]
            self.ring.remove(h)

    def get_shard(self, key):
        if not self.ring:
            return None
        h = self._hash(str(key))
        idx = bisect.bisect_right(self.ring, h)
        if idx == len(self.ring):
            idx = 0
        return self.ring_map[self.ring[idx]]

    def get_distribution(self, keys):
        dist = {s: 0 for s in self.shards}
        for key in keys:
            shard = self.get_shard(key)
            dist[shard] += 1
        return dist


# ---------------------------------------------------------------------------
#   Naive Modulo Hashing (for comparison)
# ---------------------------------------------------------------------------

def naive_modulo_shard(key, num_shards):
    h = int(hashlib.sha256(str(key).encode()).hexdigest(), 16)
    return f"shard_{h % num_shards}"


# ---------------------------------------------------------------------------
#   Rebalancing Simulation
# ---------------------------------------------------------------------------

def print_distribution(dist, label=""):
    total = sum(dist.values())
    if label:
        print(f"\n  {label}")
    print(f"  {'Shard':<12} {'Keys':>7} {'Percent':>8}")
    print(f"  {'-'*30}")
    for shard in sorted(dist):
        count = dist[shard]
        pct = count / total * 100 if total else 0
        bar = "#" * int(pct / 2)
        print(f"  {shard:<12} {count:>7} {pct:>7.1f}%  {bar}")


def compare_migrations(keys, old_mapping, new_mapping):
    moved = sum(1 for k in keys if old_mapping[k] != new_mapping[k])
    pct = moved / len(keys) * 100
    return moved, pct


def build_mapping(ring, keys):
    return {k: ring.get_shard(k) for k in keys}


def build_naive_mapping(keys, num_shards):
    return {k: naive_modulo_shard(k, num_shards) for k in keys}


# ---------------------------------------------------------------------------
#   Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    NUM_KEYS = 50_000
    keys = [f"user:{i}" for i in range(NUM_KEYS)]

    print("Shard Rebalancing - Consistent Hashing vs Naive Modulo")
    print("=" * 55)
    print(f"Keys: {NUM_KEYS:,}  |  Virtual nodes per shard: 150\n")

    ring = ConsistentHashRing(virtual_nodes=150)

    # Phase 1: Start with 3 shards
    print("--- Phase 1: Initial state (3 shards) ---")
    for i in range(3):
        ring.add_shard(f"shard_{i}")
    dist_3 = ring.get_distribution(keys)
    mapping_3 = build_mapping(ring, keys)
    naive_3 = build_naive_mapping(keys, 3)
    print_distribution(dist_3, "Consistent Hash Ring")

    # Phase 2: Add a 4th shard
    print("\n--- Phase 2: Add shard_3 (3 -> 4 shards) ---")
    ring.add_shard("shard_3")
    dist_4 = ring.get_distribution(keys)
    mapping_4 = build_mapping(ring, keys)
    naive_4 = build_naive_mapping(keys, 4)
    print_distribution(dist_4, "After adding shard_3")

    ch_moved, ch_pct = compare_migrations(keys, mapping_3, mapping_4)
    naive_moved, naive_pct = compare_migrations(keys, naive_3, naive_4)

    print(f"\n  Migration cost (3 -> 4 shards):")
    print(f"    Consistent hashing:  {ch_moved:>6,} keys moved ({ch_pct:.1f}%)")
    print(f"    Naive modulo:        {naive_moved:>6,} keys moved ({naive_pct:.1f}%)")
    print(f"    Consistent hashing moved {naive_moved / max(ch_moved, 1):.1f}x fewer keys")

    # Phase 3: Remove shard_1
    print("\n--- Phase 3: Remove shard_1 (4 -> 3 shards) ---")
    ring.remove_shard("shard_1")
    dist_after_remove = ring.get_distribution(keys)
    mapping_after_remove = build_mapping(ring, keys)
    naive_after_remove = build_naive_mapping(keys, 3)
    print_distribution(dist_after_remove, "After removing shard_1")

    ch_moved_r, ch_pct_r = compare_migrations(keys, mapping_4, mapping_after_remove)
    naive_moved_r, naive_pct_r = compare_migrations(keys, naive_4, naive_after_remove)

    print(f"\n  Migration cost (4 -> 3 shards, removing shard_1):")
    print(f"    Consistent hashing:  {ch_moved_r:>6,} keys moved ({ch_pct_r:.1f}%)")
    print(f"    Naive modulo:        {naive_moved_r:>6,} keys moved ({naive_pct_r:.1f}%)")

    # Virtual node comparison
    print("\n--- Bonus: Virtual Node Count vs Distribution Evenness ---")
    for vn_count in [1, 10, 50, 150, 500]:
        test_ring = ConsistentHashRing(virtual_nodes=vn_count)
        for i in range(4):
            test_ring.add_shard(f"shard_{i}")
        test_dist = test_ring.get_distribution(keys)
        ideal = NUM_KEYS / 4
        max_dev = max(abs(v - ideal) / ideal * 100 for v in test_dist.values())
        print(f"  vnodes={vn_count:<4}  max deviation: {max_dev:>5.1f}%")

    print()
