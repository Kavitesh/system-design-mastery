"""
Consistent Hash Ring Implementation
====================================
Full-featured consistent hash ring with virtual nodes, weighted nodes,
binary search lookup, and live node add/remove with key tracking.
"""

import hashlib
from bisect import bisect_right, insort

# ---------------------------------------------------------------------------
# Hash function
# ---------------------------------------------------------------------------

def md5_hash(key: str) -> int:
    return int(hashlib.md5(key.encode()).hexdigest(), 16)


# ---------------------------------------------------------------------------
# Consistent Hash Ring
# ---------------------------------------------------------------------------

class ConsistentHashRing:
    def __init__(self, default_vnodes: int = 150):
        self.default_vnodes = default_vnodes
        self.sorted_hashes: list[int] = []
        self.hash_to_node: dict[int, str] = {}
        self.node_vnodes: dict[str, int] = {}

    def add_node(self, node: str, vnodes: int = None, weight: float = 1.0):
        vn = int((vnodes or self.default_vnodes) * weight)
        self.node_vnodes[node] = vn
        for i in range(vn):
            h = md5_hash(f"{node}#vn{i}")
            self.hash_to_node[h] = node
            insort(self.sorted_hashes, h)

    def remove_node(self, node: str):
        vn = self.node_vnodes.pop(node, 0)
        for i in range(vn):
            h = md5_hash(f"{node}#vn{i}")
            self.hash_to_node.pop(h, None)
            idx = bisect_right(self.sorted_hashes, h) - 1
            if 0 <= idx < len(self.sorted_hashes) and self.sorted_hashes[idx] == h:
                self.sorted_hashes.pop(idx)

    def get_node(self, key: str) -> str:
        if not self.sorted_hashes:
            raise RuntimeError("Ring is empty")
        h = md5_hash(key)
        idx = bisect_right(self.sorted_hashes, h) % len(self.sorted_hashes)
        return self.hash_to_node[self.sorted_hashes[idx]]

    def get_n_nodes(self, key: str, n: int) -> list[str]:
        """Get n distinct physical nodes for replication."""
        if not self.sorted_hashes:
            raise RuntimeError("Ring is empty")
        h = md5_hash(key)
        idx = bisect_right(self.sorted_hashes, h) % len(self.sorted_hashes)
        result = []
        seen = set()
        checked = 0
        while len(result) < n and checked < len(self.sorted_hashes):
            node = self.hash_to_node[self.sorted_hashes[(idx + checked) % len(self.sorted_hashes)]]
            if node not in seen:
                seen.add(node)
                result.append(node)
            checked += 1
        return result

    @property
    def nodes(self) -> list[str]:
        return list(self.node_vnodes.keys())

    def __len__(self):
        return len(self.node_vnodes)


# ---------------------------------------------------------------------------
# Track key migrations during topology changes
# ---------------------------------------------------------------------------

def track_migrations(ring: ConsistentHashRing, keys: list[str],
                     action: str, node: str, **kwargs):
    before = {k: ring.get_node(k) for k in keys}

    if action == "add":
        ring.add_node(node, **kwargs)
    elif action == "remove":
        ring.remove_node(node)

    after = {k: ring.get_node(k) for k in keys}
    moved = {k: (before[k], after[k]) for k in keys if before[k] != after[k]}
    return moved


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def main():
    print("Consistent Hash Ring - full implementation demo")

    ring = ConsistentHashRing(default_vnodes=150)
    servers = ["cache-east-1", "cache-east-2", "cache-west-1", "cache-west-2"]

    for s in servers:
        ring.add_node(s)

    keys = [f"session:{i}" for i in range(5000)]
    distribution = {}
    for key in keys:
        node = ring.get_node(key)
        distribution[node] = distribution.get(node, 0) + 1

    print(f"\n--- Initial distribution ({len(servers)} nodes, {len(keys)} keys) ---")
    ideal = len(keys) / len(servers)
    for node, count in sorted(distribution.items()):
        diff = (count - ideal) / ideal * 100
        print(f"  {node:<16} {count:>5} keys ({diff:>+5.1f}%)")

    print(f"\n--- Adding 'cache-west-3' ---")
    moved = track_migrations(ring, keys, "add", "cache-west-3")
    print(f"  Keys moved: {len(moved)} / {len(keys)} ({len(moved)/len(keys)*100:.1f}%)")
    print(f"  Ideal (K/N): {len(keys)/5:.0f} ({1/5*100:.1f}%)")

    new_dist = {}
    for key in keys:
        node = ring.get_node(key)
        new_dist[node] = new_dist.get(node, 0) + 1

    print(f"\n--- Distribution after adding node ---")
    ideal = len(keys) / len(ring)
    for node, count in sorted(new_dist.items()):
        diff = (count - ideal) / ideal * 100
        print(f"  {node:<16} {count:>5} keys ({diff:>+5.1f}%)")

    print(f"\n--- Removing 'cache-east-1' ---")
    moved = track_migrations(ring, keys, "remove", "cache-east-1")
    print(f"  Keys moved: {len(moved)} / {len(keys)} ({len(moved)/len(keys)*100:.1f}%)")

    destinations = {}
    for k, (old, new) in moved.items():
        destinations[new] = destinations.get(new, 0) + 1
    print(f"  Keys redistributed to:")
    for node, count in sorted(destinations.items()):
        print(f"    {node:<16} received {count} keys")

    print(f"\n--- Replication: 3 replicas per key ---")
    sample_keys = ["user:alice", "user:bob", "order:9001"]
    for key in sample_keys:
        replicas = ring.get_n_nodes(key, 3)
        print(f"  {key:<16} -> {replicas}")

    print(f"\n--- Weighted nodes ---")
    weighted_ring = ConsistentHashRing(default_vnodes=100)
    weighted_ring.add_node("small-1", weight=1.0)
    weighted_ring.add_node("small-2", weight=1.0)
    weighted_ring.add_node("beefy-1", weight=3.0)

    w_dist = {}
    test_keys = [f"data:{i}" for i in range(9000)]
    for key in test_keys:
        node = weighted_ring.get_node(key)
        w_dist[node] = w_dist.get(node, 0) + 1

    print(f"  9000 keys across 2 small (1x) + 1 beefy (3x) server:")
    for node, count in sorted(w_dist.items()):
        weight = 3.0 if "beefy" in node else 1.0
        expected = 9000 * weight / 5.0
        diff = (count - expected) / expected * 100
        print(f"    {node:<12} {count:>5} keys (weight {weight}x, {diff:>+5.1f}% vs expected)")


if __name__ == "__main__":
    main()
