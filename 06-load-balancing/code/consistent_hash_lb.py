"""
Consistent Hashing Load Balancer
==================================
Demonstrates how consistent hashing distributes requests across servers
and - critically - how it minimizes redistribution when nodes join or
leave the ring. Compares this against naive modulo hashing where adding
one server reshuffles nearly everything.

Run: python consistent_hash_lb.py
"""

import hashlib
from collections import defaultdict
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Consistent hash ring
# ---------------------------------------------------------------------------

class ConsistentHashRing:
    """
    Maps keys to servers using a virtual-node hash ring. Each physical
    server gets multiple positions on the ring (virtual nodes) to improve
    distribution evenness. Lookups walk clockwise from the key's hash
    position to the nearest server.
    """

    def __init__(self, virtual_nodes: int = 150):
        self.virtual_nodes = virtual_nodes
        self.ring: Dict[int, str] = {}
        self.sorted_keys: List[int] = []
        self.servers: set = set()

    def _hash(self, key: str) -> int:
        return int(hashlib.sha256(key.encode()).hexdigest(), 16)

    def add_server(self, server: str):
        self.servers.add(server)
        for i in range(self.virtual_nodes):
            vnode_key = f"{server}:vn{i}"
            h = self._hash(vnode_key)
            self.ring[h] = server
        self.sorted_keys = sorted(self.ring.keys())

    def remove_server(self, server: str):
        self.servers.discard(server)
        for i in range(self.virtual_nodes):
            vnode_key = f"{server}:vn{i}"
            h = self._hash(vnode_key)
            self.ring.pop(h, None)
        self.sorted_keys = sorted(self.ring.keys())

    def get_server(self, key: str) -> Optional[str]:
        if not self.ring:
            return None
        h = self._hash(key)
        for ring_key in self.sorted_keys:
            if ring_key >= h:
                return self.ring[ring_key]
        return self.ring[self.sorted_keys[0]]


# ---------------------------------------------------------------------------
# Naive modulo hashing (for comparison)
# ---------------------------------------------------------------------------

def modulo_hash(key: str, servers: List[str]) -> str:
    h = int(hashlib.sha256(key.encode()).hexdigest(), 16)
    return servers[h % len(servers)]


# ---------------------------------------------------------------------------
# Simulation helpers
# ---------------------------------------------------------------------------

def generate_keys(n: int) -> List[str]:
    return [f"request-{i}" for i in range(n)]


def distribution_stats(assignments: Dict[str, int], total: int, servers: List[str]):
    print(f"\n  {'Server':<14} {'Requests':>10} {'Share':>8} {'Distribution'}")
    print(f"  {'-' * 52}")
    for s in servers:
        c = assignments.get(s, 0)
        pct = c / total * 100
        bar = "#" * int(pct / 1.5)
        print(f"  {s:<14} {c:>10,} {pct:>7.1f}%  {bar}")


# ---------------------------------------------------------------------------
# Demo 1: Distribution across servers
# ---------------------------------------------------------------------------

def demo_distribution():
    print("=" * 60)
    print("CONSISTENT HASHING - distribution")
    print("=" * 60)

    ring = ConsistentHashRing(virtual_nodes=150)
    servers = ["web-1", "web-2", "web-3", "web-4"]
    for s in servers:
        ring.add_server(s)

    keys = generate_keys(10_000)
    counts = defaultdict(int)
    for key in keys:
        server = ring.get_server(key)
        counts[server] += 1

    print(f"\n  4 servers, 150 virtual nodes each, 10,000 requests:")
    distribution_stats(counts, len(keys), servers)


# ---------------------------------------------------------------------------
# Demo 2: Adding a server - redistribution comparison
# ---------------------------------------------------------------------------

def demo_add_server():
    print("\n" + "=" * 60)
    print("ADDING A SERVER - consistent vs modulo hashing")
    print("=" * 60)

    keys = generate_keys(10_000)
    servers_before = ["web-1", "web-2", "web-3", "web-4"]
    servers_after = ["web-1", "web-2", "web-3", "web-4", "web-5"]

    ring_before = ConsistentHashRing(virtual_nodes=150)
    for s in servers_before:
        ring_before.add_server(s)
    ring_after = ConsistentHashRing(virtual_nodes=150)
    for s in servers_after:
        ring_after.add_server(s)

    ch_moved = sum(1 for k in keys if ring_before.get_server(k) != ring_after.get_server(k))

    mod_moved = sum(
        1 for k in keys if modulo_hash(k, servers_before) != modulo_hash(k, servers_after)
    )

    print(f"\n  Adding web-5 to a 4-server pool ({len(keys):,} keys):")
    print(f"\n  {'Method':<22} {'Keys Moved':>12} {'Percent':>10}")
    print(f"  {'-' * 46}")
    print(f"  {'Consistent Hashing':<22} {ch_moved:>12,} {ch_moved / len(keys) * 100:>9.1f}%")
    print(f"  {'Modulo Hashing':<22} {mod_moved:>12,} {mod_moved / len(keys) * 100:>9.1f}%")

    ideal_moved = len(keys) / len(servers_after)
    print(f"\n  Ideal redistribution (1/N): {ideal_moved:,.0f} keys ({100 / len(servers_after):.1f}%)")
    print(f"  Consistent hashing stays close to the ideal.")
    print(f"  Modulo hashing reshuffles nearly everything.")


# ---------------------------------------------------------------------------
# Demo 3: Removing a server - failover behavior
# ---------------------------------------------------------------------------

def demo_remove_server():
    print("\n" + "=" * 60)
    print("REMOVING A SERVER - failover behavior")
    print("=" * 60)

    keys = generate_keys(10_000)
    servers_full = ["web-1", "web-2", "web-3", "web-4"]
    servers_reduced = ["web-1", "web-2", "web-4"]

    ring_full = ConsistentHashRing(virtual_nodes=150)
    for s in servers_full:
        ring_full.add_server(s)

    ring_reduced = ConsistentHashRing(virtual_nodes=150)
    for s in servers_reduced:
        ring_reduced.add_server(s)

    moved = 0
    stayed = 0
    moved_from_dead = 0
    for k in keys:
        before = ring_full.get_server(k)
        after = ring_reduced.get_server(k)
        if before != after:
            moved += 1
            if before == "web-3":
                moved_from_dead += 1
        else:
            stayed += 1

    print(f"\n  Removing web-3 from a 4-server pool ({len(keys):,} keys):")
    print(f"\n  Keys that stayed on same server:    {stayed:>6,} ({stayed / len(keys) * 100:.1f}%)")
    print(f"  Keys moved (were on web-3):         {moved_from_dead:>6,} ({moved_from_dead / len(keys) * 100:.1f}%)")
    print(f"  Keys moved (were on other servers): {moved - moved_from_dead:>6,} ({(moved - moved_from_dead) / len(keys) * 100:.1f}%)")
    print(f"\n  Only web-3's keys get redistributed. Everyone else is unaffected.")


# ---------------------------------------------------------------------------
# Demo 4: Virtual node count effect
# ---------------------------------------------------------------------------

def demo_virtual_nodes():
    print("\n" + "=" * 60)
    print("VIRTUAL NODES - effect on distribution evenness")
    print("=" * 60)

    keys = generate_keys(10_000)
    servers = ["web-1", "web-2", "web-3", "web-4"]

    print(f"\n  {'Virtual Nodes':>14} {'Std Dev':>10} {'Min Share':>11} {'Max Share':>11}")
    print(f"  {'-' * 50}")

    for vn in [1, 10, 50, 150, 500]:
        ring = ConsistentHashRing(virtual_nodes=vn)
        for s in servers:
            ring.add_server(s)

        counts = defaultdict(int)
        for k in keys:
            counts[ring.get_server(k)] += 1

        values = [counts.get(s, 0) for s in servers]
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std_dev = variance ** 0.5

        min_pct = min(values) / len(keys) * 100
        max_pct = max(values) / len(keys) * 100

        print(f"  {vn:>14} {std_dev:>10.1f} {min_pct:>10.1f}% {max_pct:>10.1f}%")

    print(f"\n  More virtual nodes = more even distribution, but more memory.")
    print(f"  150 virtual nodes per server is a good default.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    demo_distribution()
    demo_add_server()
    demo_remove_server()
    demo_virtual_nodes()


if __name__ == "__main__":
    main()
