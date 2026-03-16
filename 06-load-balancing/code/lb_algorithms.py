"""
Load Balancing Algorithms
=========================
Implements the four foundational load balancing algorithms from
scratch: round-robin, weighted round-robin, least-connections,
and IP hash. Each class maintains its own state and exposes a
single pick() method that returns the next server to receive a
request.

Run: python lb_algorithms.py
"""

import hashlib
from typing import List, Optional


# ---------------------------------------------------------------------------
# Server representation
# ---------------------------------------------------------------------------

class Server:
    """
    Represents a backend server with a name, weight, and connection count.
    Weight is used by weighted round-robin. Connection count is tracked
    for least-connections.
    """

    def __init__(self, name: str, weight: int = 1):
        self.name = name
        self.weight = weight
        self.connections = 0

    def __repr__(self):
        return self.name


# ---------------------------------------------------------------------------
# Round Robin
# ---------------------------------------------------------------------------

class RoundRobin:
    """Cycles through servers sequentially, one after another."""

    def __init__(self, servers: List[Server]):
        self.servers = servers
        self.index = -1

    def pick(self) -> Server:
        self.index = (self.index + 1) % len(self.servers)
        return self.servers[self.index]


# ---------------------------------------------------------------------------
# Weighted Round Robin
# ---------------------------------------------------------------------------

class WeightedRoundRobin:
    """
    Distributes requests proportional to each server's weight. A server
    with weight 3 receives three times as many requests as weight 1.
    Uses a smooth scheduling approach to avoid sending all requests to
    the heavy server in a burst.
    """

    def __init__(self, servers: List[Server]):
        self.servers = servers
        self.current_weights = [0] * len(servers)

    def pick(self) -> Server:
        total = sum(s.weight for s in self.servers)
        best_idx = 0
        for i, server in enumerate(self.servers):
            self.current_weights[i] += server.weight
            if self.current_weights[i] > self.current_weights[best_idx]:
                best_idx = i
        self.current_weights[best_idx] -= total
        return self.servers[best_idx]


# ---------------------------------------------------------------------------
# Least Connections
# ---------------------------------------------------------------------------

class LeastConnections:
    """
    Picks the server with the fewest active connections. Callers must
    call release() when a request finishes to decrement the count.
    """

    def __init__(self, servers: List[Server]):
        self.servers = servers

    def pick(self) -> Server:
        chosen = min(self.servers, key=lambda s: s.connections)
        chosen.connections += 1
        return chosen

    def release(self, server: Server):
        server.connections = max(0, server.connections - 1)


# ---------------------------------------------------------------------------
# IP Hash
# ---------------------------------------------------------------------------

class IPHash:
    """
    Hashes the client IP to deterministically route the same client
    to the same server. Guarantees session affinity as long as the
    server pool doesn't change.
    """

    def __init__(self, servers: List[Server]):
        self.servers = servers

    def pick(self, client_ip: str) -> Server:
        digest = hashlib.md5(client_ip.encode()).hexdigest()
        index = int(digest, 16) % len(self.servers)
        return self.servers[index]


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def demo_round_robin(servers: List[Server]):
    print("=" * 60)
    print("ROUND ROBIN")
    print("=" * 60)
    rr = RoundRobin(servers)
    for i in range(9):
        server = rr.pick()
        print(f"  Request {i + 1:>2} --> {server.name}")

    print(f"\n  Pattern: cycles through {len(servers)} servers equally.")


def demo_weighted_round_robin():
    print("\n" + "=" * 60)
    print("WEIGHTED ROUND ROBIN")
    print("=" * 60)
    servers = [Server("web-large", weight=5), Server("web-med", weight=3), Server("web-small", weight=1)]
    wrr = WeightedRoundRobin(servers)

    counts = {s.name: 0 for s in servers}
    total = 27
    picks = []
    for _ in range(total):
        s = wrr.pick()
        counts[s.name] += 1
        picks.append(s.name)

    for i, name in enumerate(picks[:9]):
        print(f"  Request {i + 1:>2} --> {name}")
    print(f"  ... ({total} total requests)")

    print(f"\n  Distribution over {total} requests:")
    for s in servers:
        pct = counts[s.name] / total * 100
        bar = "#" * int(pct / 2)
        print(f"    {s.name:<12} (w={s.weight}): {counts[s.name]:>3} reqs ({pct:5.1f}%) {bar}")


def demo_least_connections(servers: List[Server]):
    print("\n" + "=" * 60)
    print("LEAST CONNECTIONS")
    print("=" * 60)
    for s in servers:
        s.connections = 0

    lc = LeastConnections(servers)

    s1 = lc.pick()
    print(f"  Request 1 --> {s1.name} (conns: {s1.connections})")
    s2 = lc.pick()
    print(f"  Request 2 --> {s2.name} (conns: {s2.connections})")
    s3 = lc.pick()
    print(f"  Request 3 --> {s3.name} (conns: {s3.connections})")

    lc.release(s1)
    print(f"\n  Released {s1.name} (conns now: {s1.connections})")

    s4 = lc.pick()
    print(f"  Request 4 --> {s4.name} (conns: {s4.connections})")
    print(f"\n  Least-connections naturally adapts to variable request times.")


def demo_ip_hash(servers: List[Server]):
    print("\n" + "=" * 60)
    print("IP HASH")
    print("=" * 60)
    ih = IPHash(servers)

    ips = ["192.168.1.10", "10.0.0.42", "172.16.5.99", "192.168.1.10", "10.0.0.42"]
    for ip in ips:
        server = ih.pick(ip)
        print(f"  {ip:<16} --> {server.name}")

    print(f"\n  Same IP always maps to the same server (session affinity).")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    servers = [Server("web-1"), Server("web-2"), Server("web-3")]

    demo_round_robin(servers)
    demo_weighted_round_robin()
    demo_least_connections(servers)
    demo_ip_hash(servers)


if __name__ == "__main__":
    main()
