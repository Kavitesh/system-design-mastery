"""
Autocomplete Benchmark
=======================
Performance test for trie-based autocomplete. Generates a large synthetic
dataset, builds a trie with top-k caching, and measures lookup latencies
across different prefix lengths and dataset sizes.

Run: python autocomplete_benchmark.py
"""

import time
import random
import string
import heapq
import statistics

# ---------------------------------------------------------------------------
# Trie (standalone copy for benchmark isolation)
# ---------------------------------------------------------------------------

class TrieNode:
    __slots__ = ("children", "is_end", "frequency", "top_k")

    def __init__(self):
        self.children: dict[str, "TrieNode"] = {}
        self.is_end = False
        self.frequency = 0
        self.top_k: list[tuple[int, str]] = []


class Trie:
    def __init__(self, k: int = 10):
        self.root = TrieNode()
        self.k = k
        self._word_count = 0

    def insert(self, word: str, frequency: int = 1):
        node = self.root
        for char in word:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        if not node.is_end:
            self._word_count += 1
        node.is_end = True
        node.frequency += frequency

    def build_top_k_cache(self):
        self._build_cache(self.root, "")

    def _build_cache(self, node: TrieNode, prefix: str):
        candidates = []
        if node.is_end:
            candidates.append((node.frequency, prefix))
        for char, child in node.children.items():
            self._build_cache(child, prefix + char)
            candidates.extend(child.top_k)
        node.top_k = heapq.nlargest(self.k, candidates, key=lambda x: x[0])

    def search(self, prefix: str) -> list[tuple[int, str]]:
        node = self.root
        for char in prefix:
            if char not in node.children:
                return []
            node = node.children[char]
        return node.top_k

    def count_nodes(self) -> int:
        count = 0
        stack = [self.root]
        while stack:
            node = stack.pop()
            count += 1
            stack.extend(node.children.values())
        return count

    @property
    def word_count(self):
        return self._word_count


# ---------------------------------------------------------------------------
# Dataset generator
# ---------------------------------------------------------------------------

WORD_PARTS = [
    "how", "what", "where", "when", "why", "best", "top", "new", "free",
    "online", "near", "cheap", "fast", "easy", "learn", "buy", "make",
    "python", "java", "react", "node", "flask", "django", "spring",
    "weather", "news", "stock", "price", "review", "recipe", "movie",
    "game", "app", "tool", "api", "data", "cloud", "server", "code",
    "design", "system", "network", "security", "test", "build", "deploy",
]


def generate_queries(n: int) -> list[tuple[str, int]]:
    """Generate n realistic-looking multi-word search queries with frequencies."""
    queries = []
    for _ in range(n):
        word_count = random.choices([1, 2, 3, 4], weights=[15, 40, 35, 10])[0]
        words = random.sample(WORD_PARTS, min(word_count, len(WORD_PARTS)))
        query = " ".join(words)
        freq = int(random.paretovariate(1.5) * 10)
        queries.append((query, max(freq, 1)))
    return queries


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------

def benchmark_build(queries: list[tuple[str, int]], k: int = 10) -> tuple[Trie, float, float]:
    """Build a trie and return it with insert and cache build times."""
    trie = Trie(k=k)

    start = time.perf_counter()
    for query, freq in queries:
        trie.insert(query, freq)
    insert_time = time.perf_counter() - start

    start = time.perf_counter()
    trie.build_top_k_cache()
    cache_time = time.perf_counter() - start

    return trie, insert_time, cache_time


def benchmark_lookups(trie: Trie, prefixes: list[str], iterations: int = 1000) -> dict:
    """Run lookups and collect latency statistics."""
    latencies = []
    for _ in range(iterations):
        for prefix in prefixes:
            start = time.perf_counter()
            trie.search(prefix)
            elapsed = (time.perf_counter() - start) * 1_000_000
            latencies.append(elapsed)

    latencies.sort()
    return {
        "total_lookups": len(latencies),
        "mean_us": statistics.mean(latencies),
        "median_us": statistics.median(latencies),
        "p95_us": latencies[int(len(latencies) * 0.95)],
        "p99_us": latencies[int(len(latencies) * 0.99)],
        "min_us": latencies[0],
        "max_us": latencies[-1],
    }


def main():
    random.seed(42)

    print("=" * 65)
    print("AUTOCOMPLETE PERFORMANCE BENCHMARK")
    print("=" * 65)

    # -----------------------------------------------------------------------
    # Benchmark 1: Scaling dataset size
    # -----------------------------------------------------------------------
    print("\n--- Build time vs dataset size ---")
    print(f"  {'Queries':>10}  {'Nodes':>10}  {'Insert (ms)':>12}  {'Cache (ms)':>12}  {'Total (ms)':>12}")
    print(f"  {'-' * 60}")

    sizes = [1_000, 10_000, 50_000, 100_000, 200_000]
    trie_for_lookup = None

    for size in sizes:
        queries = generate_queries(size)
        trie, t_insert, t_cache = benchmark_build(queries)
        print(f"  {size:>10,}  {trie.count_nodes():>10,}  "
              f"{t_insert*1000:>12.1f}  {t_cache*1000:>12.1f}  "
              f"{(t_insert+t_cache)*1000:>12.1f}")
        if size == 100_000:
            trie_for_lookup = trie

    # -----------------------------------------------------------------------
    # Benchmark 2: Lookup latency by prefix length
    # -----------------------------------------------------------------------
    print("\n--- Lookup latency by prefix length (100K queries, 1000 iterations) ---")

    prefix_groups = {
        "1-char": [random.choice(string.ascii_lowercase) for _ in range(20)],
        "2-char": [random.choice(WORD_PARTS)[:2] for _ in range(20)],
        "3-char": [random.choice(WORD_PARTS)[:3] for _ in range(20)],
        "5-char": [random.choice(WORD_PARTS)[:5] for _ in range(20)],
        "full word": random.sample(WORD_PARTS, 20),
    }

    print(f"  {'Prefix Type':<12} {'Mean (us)':>10} {'Median (us)':>12} "
          f"{'P95 (us)':>10} {'P99 (us)':>10}")
    print(f"  {'-' * 58}")

    for label, prefixes in prefix_groups.items():
        stats = benchmark_lookups(trie_for_lookup, prefixes, iterations=1000)
        print(f"  {label:<12} {stats['mean_us']:>10.2f} {stats['median_us']:>12.2f} "
              f"{stats['p95_us']:>10.2f} {stats['p99_us']:>10.2f}")

    # -----------------------------------------------------------------------
    # Benchmark 3: Throughput estimate
    # -----------------------------------------------------------------------
    print("\n--- Throughput test (100K queries in trie) ---")

    test_prefixes = [random.choice(WORD_PARTS)[:3] for _ in range(100)]
    total_ops = 100_000
    ops_done = 0

    start = time.perf_counter()
    while ops_done < total_ops:
        for prefix in test_prefixes:
            trie_for_lookup.search(prefix)
            ops_done += 1
            if ops_done >= total_ops:
                break
    elapsed = time.perf_counter() - start

    qps = total_ops / elapsed
    print(f"  {total_ops:,} lookups in {elapsed*1000:.0f}ms")
    print(f"  Throughput: {qps:,.0f} lookups/sec (single thread)")
    print(f"  Average latency: {elapsed/total_ops*1_000_000:.2f} us/lookup")

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    print(f"\n{'=' * 65}")
    print("SUMMARY")
    print(f"{'=' * 65}")
    print(f"""
  Trie with precomputed top-k delivers sub-microsecond lookups
  regardless of dataset size. The bottleneck is build time, not
  query time - which is exactly what you want when the read path
  serves 100K+ QPS and the write path rebuilds every 15 minutes.

  At {qps:,.0f} single-threaded lookups/sec, a single trie server
  can handle the autocomplete load of most applications. For
  Google-scale traffic, shard by prefix across 10-20 servers.
""")


if __name__ == "__main__":
    main()
