"""
HyperLogLog - Cardinality Estimation
======================================
Estimates the number of distinct elements in a dataset
using ~12 KB of memory regardless of dataset size.

Run: python hyperloglog.py
"""

import math
import hashlib
import struct
import sys

# ---------------------------------------------------------------------------
#  HyperLogLog
# ---------------------------------------------------------------------------

class HyperLogLog:
    """Cardinality estimation using the HyperLogLog algorithm."""

    def __init__(self, precision=14):
        self.p = precision
        self.m = 1 << precision
        self.registers = bytearray(self.m)
        if self.m <= 64:
            self._alpha = {16: 0.673, 32: 0.697, 64: 0.709}[self.m]
        else:
            self._alpha = 0.7213 / (1 + 1.079 / self.m)

    def _hash(self, item):
        digest = hashlib.sha1(str(item).encode("utf-8")).digest()
        return struct.unpack("<Q", digest[:8])[0]

    @staticmethod
    def _leading_zeros(value, max_bits):
        if value == 0:
            return max_bits
        count = 0
        for i in range(max_bits - 1, -1, -1):
            if value & (1 << i):
                break
            count += 1
        return count

    def add(self, item):
        h = self._hash(item)
        bucket = h & (self.m - 1)
        lz = self._leading_zeros(h >> self.p, 64 - self.p) + 1
        self.registers[bucket] = max(self.registers[bucket], lz)

    def count(self):
        indicator = sum(2.0 ** (-r) for r in self.registers)
        raw = self._alpha * self.m * self.m / indicator
        if raw <= 2.5 * self.m:
            zeros = self.registers.count(0)
            if zeros > 0:
                return self.m * math.log(self.m / zeros)
        return raw

    def merge(self, other):
        if self.p != other.p:
            raise ValueError("Precision must match for merge")
        for i in range(self.m):
            self.registers[i] = max(self.registers[i], other.registers[i])

    def memory_bytes(self):
        return self.m

    def standard_error(self):
        return 1.04 / math.sqrt(self.m)


# ---------------------------------------------------------------------------
#  Demo
# ---------------------------------------------------------------------------

def demo_basic():
    print("=== Basic Cardinality Estimation ===\n")
    hll = HyperLogLog(precision=14)
    print(f"Buckets: {hll.m:,} | Memory: {hll.m/1024:.1f} KB | Std error: {hll.standard_error():.2%}\n")

    for i in range(100_000):
        hll.add(f"user-{i}")
    for i in range(50_000):
        hll.add(f"user-{i}")
    est = hll.count()
    print(f"100,000 unique + 50,000 duplicates")
    print(f"Actual: 100,000 | Estimated: {est:,.0f} | Error: {(est-100_000)/1000:+.2f}%")


def demo_precision_and_scale():
    print("\n=== Accuracy vs. Precision ===\n")
    actual = 50_000
    print(f"{'p':>4} {'Buckets':>10} {'Memory':>8} {'Estimated':>10} {'Error':>8} {'Theory':>8}")
    print("-" * 52)
    for p in [4, 8, 10, 12, 14]:
        hll = HyperLogLog(precision=p)
        for i in range(actual):
            hll.add(f"e-{i}")
        est = hll.count()
        mem = hll.m
        mem_s = f"{mem} B" if mem < 1024 else f"{mem/1024:.1f} KB"
        print(f"{p:>4} {hll.m:>10,} {mem_s:>8} {est:>10,.0f} {(est-actual)/actual*100:>+7.2f}% {hll.standard_error():>7.2%}")

    print(f"\n--- Fixed p=14, varying cardinality ---\n")
    print(f"{'Actual':>12} {'Estimated':>12} {'Error':>8}")
    print("-" * 35)
    for n in [100, 1_000, 10_000, 100_000, 1_000_000]:
        hll = HyperLogLog(precision=14)
        for i in range(n):
            hll.add(f"x-{i}")
        est = hll.count()
        print(f"{n:>12,} {est:>12,.0f} {(est-n)/n*100:>+7.2f}%")


def demo_merge():
    print("\n=== Distributed Counting via Merge ===\n")
    servers, per_server, overlap = 4, 25_000, 10_000
    hlls = [HyperLogLog(precision=14) for _ in range(servers)]
    for s in range(servers):
        for i in range(overlap):
            hlls[s].add(f"shared-{i}")
        for i in range(per_server - overlap):
            hlls[s].add(f"s{s}-{i}")

    actual_total = overlap + servers * (per_server - overlap)
    print(f"{'Server':<10} {'Local':>8} {'Estimated':>10} {'Error':>8}")
    print("-" * 40)
    for s in range(servers):
        est = hlls[s].count()
        print(f"Server {s:<3} {per_server:>8,} {est:>10,.0f} {(est-per_server)/per_server*100:>+7.2f}%")

    merged = HyperLogLog(precision=14)
    for hll in hlls:
        merged.merge(hll)
    est = merged.count()
    print(f"\n{'Merged':<10} {actual_total:>8,} {est:>10,.0f} {(est-actual_total)/actual_total*100:>+7.2f}%")
    print(f"De-duplicated overlapping users across {servers} servers in {servers*16} KB total")


def demo_vs_exact():
    print("\n=== Memory: HyperLogLog vs. Exact Set ===\n")
    print(f"{'Distinct':>12} {'Set (approx)':>14} {'HLL':>10} {'Ratio':>8}")
    print("-" * 48)
    for n in [1_000, 10_000, 100_000]:
        exact = {f"i-{i}" for i in range(n)}
        hll = HyperLogLog(precision=14)
        for i in range(n):
            hll.add(f"i-{i}")
        sample = list(exact)[:100]
        set_mem = sys.getsizeof(exact) + sum(sys.getsizeof(s) for s in sample) / len(sample) * n
        hll_mem = hll.memory_bytes()
        fmt = lambda b: f"{b/1024:.1f} KB" if b < 1048576 else f"{b/1048576:.1f} MB"
        print(f"{n:>12,} {fmt(set_mem):>14} {fmt(hll_mem):>10} {set_mem/hll_mem:>7.0f}x")


if __name__ == "__main__":
    print("HyperLogLog - Cardinality Estimation\n")
    demo_basic()
    demo_precision_and_scale()
    demo_merge()
    demo_vs_exact()
