"""
Bloom Filter - Probabilistic Membership Testing
=================================================
Implements a Bloom filter with configurable false positive rate,
optimal hash function count, and fill rate monitoring.

Run: python bloom_filter.py
"""

import math
import hashlib

# ---------------------------------------------------------------------------
#  Bloom Filter
# ---------------------------------------------------------------------------

class BloomFilter:
    """Space-efficient probabilistic set membership testing."""

    def __init__(self, expected_items, fp_rate=0.01):
        self.expected_items = expected_items
        self.fp_rate = fp_rate
        self.size = int(-expected_items * math.log(fp_rate) / (math.log(2) ** 2))
        self.num_hashes = max(1, int((self.size / expected_items) * math.log(2)))
        self.bit_array = bytearray(math.ceil(self.size / 8))
        self.items_added = 0

    def _get_bit_positions(self, item):
        """Kirsch-Mitzenmacher: h_i = h1 + i*h2 for k hashes from two base hashes."""
        raw = str(item).encode("utf-8")
        h1 = int(hashlib.md5(raw).hexdigest(), 16)
        h2 = int(hashlib.sha1(raw).hexdigest(), 16)
        return [(h1 + i * h2) % self.size for i in range(self.num_hashes)]

    def add(self, item):
        for pos in self._get_bit_positions(item):
            self.bit_array[pos // 8] |= 1 << (pos % 8)
        self.items_added += 1

    def __contains__(self, item):
        return all(self.bit_array[pos // 8] & (1 << (pos % 8)) for pos in self._get_bit_positions(item))

    def fill_rate(self):
        set_bits = sum(bin(byte).count("1") for byte in self.bit_array)
        return set_bits / self.size

    def estimated_fp_rate(self):
        return self.fill_rate() ** self.num_hashes

    def memory_bytes(self):
        return len(self.bit_array)


# ---------------------------------------------------------------------------
#  Demo
# ---------------------------------------------------------------------------

def demo_basic():
    print("=== Bloom Filter - Basic Usage ===\n")

    bf = BloomFilter(expected_items=10_000, fp_rate=0.01)
    print(f"Config: {bf.expected_items:,} items, {bf.fp_rate:.0%} target FP rate")
    print(f"Bit array: {bf.size:,} bits ({bf.memory_bytes():,} bytes)")
    print(f"Hash functions: {bf.num_hashes} | Bits/element: {bf.size / bf.expected_items:.1f}\n")

    fruits = ["apple", "banana", "cherry", "date", "elderberry"]
    for f in fruits:
        bf.add(f)

    print("Membership tests:")
    for item in ["apple", "banana", "fig", "grape", "cherry"]:
        status = "probably yes" if item in bf else "definitely no"
        truth = "inserted" if item in fruits else "not inserted"
        match = "correct" if (item in bf) == (item in fruits) else "FALSE POSITIVE"
        print(f"  '{item}': {status} ({truth}) [{match}]")


def demo_sizing():
    print("\n=== Sizing: FP Rate vs. Configuration ===\n")

    configs = [(1000, 0.10), (1000, 0.01), (1000, 0.001), (10_000, 0.01), (100_000, 0.01)]
    print(f"{'Items':>8} {'Target FP':>10} {'Bits':>10} {'Hashes':>7} {'Memory':>10} {'Bits/elem':>10}")
    print("-" * 60)
    for n, p in configs:
        bf = BloomFilter(n, p)
        print(f"{n:>8,} {p:>10.1%} {bf.size:>10,} {bf.num_hashes:>7} {bf.memory_bytes():>8,} B {bf.size/n:>10.1f}")


def demo_measured_fp_rate():
    print("\n=== Measured vs. Theoretical FP Rate ===\n")

    n = 10_000
    bf = BloomFilter(expected_items=n, fp_rate=0.01)
    for i in range(n):
        bf.add(f"item-{i}")

    false_positives = 0
    test_count = 100_000
    for i in range(test_count):
        if f"nonexistent-{i}" in bf:
            false_positives += 1

    measured = false_positives / test_count
    print(f"Inserted: {n:,} | Tested: {test_count:,} non-existent items")
    print(f"False positives: {false_positives:,}")
    print(f"Measured FP rate: {measured:.4%}")
    print(f"Target FP rate:   {bf.fp_rate:.4%}")
    print(f"Fill rate:        {bf.fill_rate():.2%}")


def demo_degradation():
    print("\n=== Degradation When Overfilled ===\n")

    print(f"Sized for 1,000 items at 1% FP rate\n")
    print(f"{'Items Added':>12} {'Fill Rate':>10} {'Est. FP':>10} {'Measured FP':>12}")
    print("-" * 48)

    for load in [500, 1000, 2000, 5000, 10_000]:
        bf = BloomFilter(expected_items=1000, fp_rate=0.01)
        for i in range(load):
            bf.add(f"item-{i}")
        fp_count = sum(1 for i in range(50_000) if f"check-{i}" in bf)
        measured = fp_count / 50_000
        print(f"{load:>12,} {bf.fill_rate():>10.1%} {bf.estimated_fp_rate():>10.2%} {measured:>12.2%}")


if __name__ == "__main__":
    print("Bloom Filter - Probabilistic Membership Testing\n")
    demo_basic()
    demo_sizing()
    demo_measured_fp_rate()
    demo_degradation()
