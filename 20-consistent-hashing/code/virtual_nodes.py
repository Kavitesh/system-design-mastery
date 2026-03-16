"""
Virtual Nodes - Distribution Uniformity
========================================
Shows how increasing the number of virtual nodes per server
dramatically improves load distribution across the hash ring.
"""

import hashlib
import math
from bisect import bisect_right
from collections import defaultdict

# ---------------------------------------------------------------------------
# Hash function
# ---------------------------------------------------------------------------

def md5_hash(key: str) -> int:
    return int(hashlib.md5(key.encode()).hexdigest(), 16)


# ---------------------------------------------------------------------------
# Consistent hash ring with configurable vnodes
# ---------------------------------------------------------------------------

class HashRing:
    def __init__(self, servers: list[str], vnodes_per_server: int):
        self.vnodes = vnodes_per_server
        self.ring: list[tuple[int, str]] = []
        for server in servers:
            for i in range(vnodes_per_server):
                h = md5_hash(f"{server}#vn{i}")
                self.ring.append((h, server))
        self.ring.sort()
        self._positions = [entry[0] for entry in self.ring]

    def lookup(self, key: str) -> str:
        h = md5_hash(key)
        idx = bisect_right(self._positions, h) % len(self.ring)
        return self.ring[idx][1]


# ---------------------------------------------------------------------------
# Distribution analysis
# ---------------------------------------------------------------------------

def analyze_distribution(servers: list[str], vnodes: int, num_keys: int) -> dict:
    ring = HashRing(servers, vnodes)
    counts = defaultdict(int)

    for i in range(num_keys):
        server = ring.lookup(f"key:{i}")
        counts[server] += 1

    ideal = num_keys / len(servers)
    values = [counts[s] for s in servers]
    mean = sum(values) / len(values)
    std_dev = (sum((v - mean) ** 2 for v in values) / len(values)) ** 0.5
    min_load = min(values)
    max_load = max(values)
    imbalance = (max_load - min_load) / ideal * 100

    return {
        "vnodes": vnodes,
        "counts": dict(counts),
        "std_dev": std_dev,
        "std_dev_pct": std_dev / ideal * 100,
        "min_load": min_load,
        "max_load": max_load,
        "imbalance": imbalance,
        "ideal": ideal,
    }


# ---------------------------------------------------------------------------
# Visual bar chart
# ---------------------------------------------------------------------------

def print_bar(label: str, value: int, max_value: int, width: int = 40):
    bar_len = int(value / max_value * width)
    bar = "#" * bar_len
    print(f"    {label:<12} {value:>6} |{bar}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Virtual Nodes - distribution uniformity analysis")

    servers = [f"node-{i}" for i in range(6)]
    num_keys = 50_000
    vnode_counts = [1, 3, 10, 25, 50, 100, 150, 250, 500]

    print(f"\n{'='*70}")
    print(f"  {len(servers)} servers, {num_keys:,} keys")
    print(f"  Testing vnode counts: {vnode_counts}")
    print(f"{'='*70}")

    results = []
    for vn in vnode_counts:
        stats = analyze_distribution(servers, vn, num_keys)
        results.append(stats)

    print(f"\n  {'Vnodes':>8}  {'Std Dev':>10}  {'Min':>7}  {'Max':>7}  {'Ideal':>7}  {'Imbalance':>10}")
    print(f"  {'-'*8}  {'-'*10}  {'-'*7}  {'-'*7}  {'-'*7}  {'-'*10}")

    for r in results:
        print(f"  {r['vnodes']:>8}  {r['std_dev']:>9.1f}  "
              f"{r['min_load']:>7,}  {r['max_load']:>7,}  "
              f"{r['ideal']:>7,.0f}  {r['imbalance']:>9.1f}%")

    print(f"\n--- Detailed view: 1 vnode per server (worst case) ---")
    worst = results[0]
    max_val = max(worst["counts"].values())
    for server in sorted(worst["counts"].keys()):
        print_bar(server, worst["counts"][server], max_val)

    best_idx = -1
    for i, vn in enumerate(vnode_counts):
        if vn == 150:
            best_idx = i
            break
    if best_idx == -1:
        best_idx = len(results) - 2

    print(f"\n--- Detailed view: {results[best_idx]['vnodes']} vnodes per server ---")
    good = results[best_idx]
    max_val = max(good["counts"].values())
    for server in sorted(good["counts"].keys()):
        print_bar(server, good["counts"][server], max_val)

    print(f"\n--- Diminishing returns analysis ---")
    print(f"  Going from 1 to 10 vnodes:    std dev drops {results[0]['std_dev_pct']:.1f}% -> {results[2]['std_dev_pct']:.1f}%")
    print(f"  Going from 10 to 100 vnodes:  std dev drops {results[2]['std_dev_pct']:.1f}% -> {results[5]['std_dev_pct']:.1f}%")
    print(f"  Going from 100 to 500 vnodes: std dev drops {results[5]['std_dev_pct']:.1f}% -> {results[8]['std_dev_pct']:.1f}%")

    print(f"\n--- Ring size vs vnode count ---")
    print(f"  {'Vnodes':>8}  {'Ring Points':>13}  {'Lookup Cost':>13}")
    print(f"  {'-'*8}  {'-'*13}  {'-'*13}")
    for vn in vnode_counts:
        ring_size = vn * len(servers)
        lookup_steps = math.ceil(math.log2(ring_size)) if ring_size > 0 else 0
        print(f"  {vn:>8}  {ring_size:>13,}  {lookup_steps:>10} steps")

    print(f"\n  Takeaway: 100-200 vnodes is the sweet spot.")
    print(f"  Below 50: uneven distribution. Above 300: diminishing returns,")
    print(f"  larger ring, slower membership changes.")


if __name__ == "__main__":
    main()
