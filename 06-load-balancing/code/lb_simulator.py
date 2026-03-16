"""
Load Balancer Traffic Simulator
================================
Fires 10,000 simulated requests through four different load balancing
algorithms and measures how evenly each one distributes traffic across
a pool of servers. Some servers are faster than others, which reveals
how algorithms handle heterogeneous backends.

Run: python lb_simulator.py
"""

import hashlib
import random
import time
from collections import defaultdict


# ---------------------------------------------------------------------------
# Simulated server pool
# ---------------------------------------------------------------------------

SERVERS = [
    {"name": "web-1", "weight": 4, "avg_ms": 10},
    {"name": "web-2", "weight": 2, "avg_ms": 25},
    {"name": "web-3", "weight": 1, "avg_ms": 50},
    {"name": "web-4", "weight": 3, "avg_ms": 15},
]

TOTAL_REQUESTS = 10_000


# ---------------------------------------------------------------------------
# Algorithm implementations (simplified for simulation)
# ---------------------------------------------------------------------------

def round_robin(servers, _request_id, _client_ip, state):
    idx = state.get("index", -1)
    idx = (idx + 1) % len(servers)
    state["index"] = idx
    return servers[idx]


def weighted_round_robin(servers, _request_id, _client_ip, state):
    if "cw" not in state:
        state["cw"] = [0] * len(servers)
    total = sum(s["weight"] for s in servers)
    best = 0
    for i, s in enumerate(servers):
        state["cw"][i] += s["weight"]
        if state["cw"][i] > state["cw"][best]:
            best = i
    state["cw"][best] -= total
    return servers[best]


def least_connections(servers, _request_id, _client_ip, state):
    conns = state.setdefault("conns", {s["name"]: 0 for s in servers})
    chosen = min(servers, key=lambda s: conns[s["name"]])
    conns[chosen["name"]] += 1
    simulated_duration = random.expovariate(1.0 / chosen["avg_ms"])
    state.setdefault("pending", []).append((chosen["name"], simulated_duration))
    return chosen


def ip_hash(servers, _request_id, client_ip, _state):
    digest = hashlib.md5(client_ip.encode()).hexdigest()
    idx = int(digest, 16) % len(servers)
    return servers[idx]


# ---------------------------------------------------------------------------
# Simulation runner
# ---------------------------------------------------------------------------

def generate_client_ips(n):
    random.seed(42)
    return [f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}" for _ in range(n)]


def run_simulation(name, algorithm, servers, requests, client_ips):
    counts = defaultdict(int)
    state = {}

    for i in range(requests):
        if algorithm == least_connections:
            pending = state.get("pending", [])
            conns = state.get("conns", {})
            still_pending = []
            for srv_name, remaining in pending:
                remaining -= 1
                if remaining <= 0:
                    conns[srv_name] = max(0, conns.get(srv_name, 0) - 1)
                else:
                    still_pending.append((srv_name, remaining))
            state["pending"] = still_pending

        server = algorithm(servers, i, client_ips[i % len(client_ips)], state)
        counts[server["name"]] += 1

    return counts


def print_results(name, counts, servers):
    print(f"\n{'=' * 60}")
    print(f"  {name}")
    print(f"{'=' * 60}")

    total = sum(counts.values())
    ideal = total / len(servers)

    print(f"\n  {'Server':<10} {'Requests':>10} {'Share':>8} {'Distribution'}")
    print(f"  {'-' * 48}")

    for s in servers:
        c = counts[s["name"]]
        pct = c / total * 100
        bar = "#" * int(pct / 2)
        print(f"  {s['name']:<10} {c:>10,} {pct:>7.1f}%  {bar}")

    max_c = max(counts.values())
    min_c = min(counts.values())
    imbalance = (max_c - min_c) / ideal * 100
    print(f"\n  Imbalance ratio: {imbalance:.1f}% (0% = perfectly even)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Load Balancer Traffic Simulator")
    print(f"Sending {TOTAL_REQUESTS:,} requests to {len(SERVERS)} servers\n")

    print("Server pool:")
    print(f"  {'Name':<10} {'Weight':>6} {'Avg Latency':>12}")
    print(f"  {'-' * 30}")
    for s in SERVERS:
        print(f"  {s['name']:<10} {s['weight']:>6} {s['avg_ms']:>10} ms")

    client_ips = generate_client_ips(500)

    algorithms = [
        ("Round Robin", round_robin),
        ("Weighted Round Robin", weighted_round_robin),
        ("Least Connections", least_connections),
        ("IP Hash", ip_hash),
    ]

    results = {}
    for name, algo in algorithms:
        counts = run_simulation(name, algo, SERVERS, TOTAL_REQUESTS, client_ips)
        results[name] = counts
        print_results(name, counts, SERVERS)

    print(f"\n{'=' * 60}")
    print("  COMPARISON SUMMARY")
    print(f"{'=' * 60}")
    print(f"\n  {'Algorithm':<25} {'Most Loaded':>12} {'Least Loaded':>13} {'Spread':>8}")
    print(f"  {'-' * 60}")

    for name, counts in results.items():
        max_c = max(counts.values())
        min_c = min(counts.values())
        spread = max_c - min_c
        print(f"  {name:<25} {max_c:>12,} {min_c:>13,} {spread:>8,}")

    print(f"""
  Key observations:
    - Round robin ignores server capacity and request duration
    - Weighted round robin respects capacity but not current load
    - Least connections adapts to actual server response times
    - IP hash guarantees affinity but can create hotspots
""")


if __name__ == "__main__":
    main()
