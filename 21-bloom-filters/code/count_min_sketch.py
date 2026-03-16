"""
Count-Min Sketch - Frequency Estimation
========================================
Estimates element frequencies in a data stream using
sub-linear space with guaranteed one-sided error.

Run: python count_min_sketch.py
"""

import math
import hashlib
import random
from collections import Counter

# ---------------------------------------------------------------------------
#  Count-Min Sketch
# ---------------------------------------------------------------------------

class CountMinSketch:
    """Frequency estimation with bounded over-count error."""

    def __init__(self, width, depth):
        self.width = width
        self.depth = depth
        self.table = [[0] * width for _ in range(depth)]
        self.total = 0
        self._seeds = [random.randint(0, 2**32) for _ in range(depth)]

    @classmethod
    def from_error_bounds(cls, epsilon, delta):
        """Error <= epsilon*N with probability >= 1-delta."""
        width = math.ceil(math.e / epsilon)
        depth = math.ceil(math.log(1.0 / delta))
        return cls(width, depth)

    def _hash(self, item, row):
        raw = f"{self._seeds[row]}:{item}".encode("utf-8")
        return int(hashlib.md5(raw).hexdigest(), 16) % self.width

    def add(self, item, count=1):
        self.total += count
        for row in range(self.depth):
            self.table[row][self._hash(item, row)] += count

    def estimate(self, item):
        return min(self.table[row][self._hash(item, row)] for row in range(self.depth))


# ---------------------------------------------------------------------------
#  Demo
# ---------------------------------------------------------------------------

def demo_basic():
    print("=== Count-Min Sketch - Basic Usage ===\n")

    cms = CountMinSketch.from_error_bounds(epsilon=0.001, delta=0.01)
    print(f"Config: width={cms.width}, depth={cms.depth}, counters={cms.width*cms.depth:,}\n")

    events = {"login": 500, "page_view": 3000, "click": 1200, "purchase": 50, "logout": 480}
    for event, count in events.items():
        cms.add(event, count)

    print(f"{'Event':<15} {'Actual':>8} {'Estimated':>10} {'Error':>8}")
    print("-" * 45)
    for event, actual in events.items():
        est = cms.estimate(event)
        print(f"{event:<15} {actual:>8,} {est:>10,} {est-actual:>+8,}")
    print(f"\n'signup' (never added): estimated = {cms.estimate('signup')}")


def demo_zipf_stream():
    print("\n=== Zipf-Distributed Stream ===\n")

    random.seed(42)
    vocabulary = [f"word_{i}" for i in range(10_000)]
    exact = Counter()
    stream_size = 500_000
    stream = []
    for _ in range(stream_size):
        idx = min(int(random.paretovariate(1.0)), len(vocabulary) - 1)
        stream.append(vocabulary[idx])
    exact.update(stream)

    cms = CountMinSketch.from_error_bounds(epsilon=0.001, delta=0.01)
    for item in stream:
        cms.add(item)

    print(f"Stream: {stream_size:,} events, {len(exact):,} distinct")
    print(f"Sketch: {cms.width}x{cms.depth} = {cms.width*cms.depth:,} counters\n")

    print(f"{'Element':<12} {'Actual':>8} {'Estimated':>10} {'Error %':>8}")
    print("-" * 42)
    for item, actual in exact.most_common(10):
        est = cms.estimate(item)
        print(f"{item:<12} {actual:>8,} {est:>10,} {(est-actual)/actual*100:>+7.1f}%")


def demo_heavy_hitters():
    print("\n=== Heavy Hitter Detection ===\n")

    random.seed(99)
    ips = [f"192.168.1.{i}" for i in range(256)]
    attackers = ["10.0.0.1", "10.0.0.2", "10.0.0.3"]

    cms = CountMinSketch.from_error_bounds(epsilon=0.0001, delta=0.001)
    exact = Counter()
    for ip in ips:
        count = random.randint(1, 20)
        cms.add(ip, count)
        exact[ip] += count
    for attacker in attackers:
        count = random.randint(5000, 10000)
        cms.add(attacker, count)
        exact[attacker] += count

    threshold = cms.total * 0.01
    print(f"Total traffic: {cms.total:,} | Threshold (1%): {threshold:,.0f}\n")

    print(f"{'IP Address':<18} {'Estimated':>10} {'Actual':>8} {'Status':>10}")
    print("-" * 50)
    for ip in ips + attackers:
        est = cms.estimate(ip)
        if est >= threshold:
            status = "ATTACKER" if ip in attackers else "normal"
            print(f"{ip:<18} {est:>10,} {exact[ip]:>8,} {status:>10}")


def demo_sizing():
    print("\n=== Sizing Guide ===\n")

    configs = [("Loose (1%, 90%)", 0.01, 0.10), ("Medium (0.1%, 99%)", 0.001, 0.01),
               ("Tight (0.01%, 99.9%)", 0.0001, 0.001)]
    print(f"{'Config':<25} {'Width':>8} {'Depth':>6} {'Counters':>10} {'Memory':>10}")
    print("-" * 65)
    for label, eps, delta in configs:
        cms = CountMinSketch.from_error_bounds(eps, delta)
        counters = cms.width * cms.depth
        mem = counters * 4
        mem_str = f"{mem} B" if mem < 1024 else (f"{mem/1024:.1f} KB" if mem < 1048576 else f"{mem/1048576:.1f} MB")
        print(f"{label:<25} {cms.width:>8,} {cms.depth:>6} {counters:>10,} {mem_str:>10}")


if __name__ == "__main__":
    print("Count-Min Sketch - Frequency Estimation\n")
    demo_basic()
    demo_zipf_stream()
    demo_heavy_hitters()
    demo_sizing()
