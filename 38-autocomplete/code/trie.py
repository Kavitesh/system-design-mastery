"""
Trie Data Structure for Autocomplete
=====================================
A trie (prefix tree) optimized for autocomplete. Supports insert, prefix
lookup, and top-k ranking by frequency. Each node caches the top-k results
for its subtree so lookups are O(prefix_length) with no sorting at query time.

Run: python trie.py
"""

import heapq

# ---------------------------------------------------------------------------
# Trie node and trie
# ---------------------------------------------------------------------------

class TrieNode:
    __slots__ = ("children", "is_end", "frequency", "top_k")

    def __init__(self):
        self.children: dict[str, "TrieNode"] = {}
        self.is_end = False
        self.frequency = 0
        self.top_k: list[tuple[int, str]] = []


class Trie:
    """Prefix trie with cached top-k suggestions at every node."""

    def __init__(self, k: int = 10):
        self.root = TrieNode()
        self.k = k

    def insert(self, word: str, frequency: int = 1):
        node = self.root
        for char in word:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.is_end = True
        node.frequency += frequency

    def _collect_all(self, node: TrieNode, prefix: str, results: list):
        if node.is_end:
            results.append((node.frequency, prefix))
        for char, child in node.children.items():
            self._collect_all(child, prefix + char, results)

    def build_top_k_cache(self):
        """Precompute top-k suggestions at every node via post-order traversal."""
        self._build_cache(self.root, "")

    def _build_cache(self, node: TrieNode, prefix: str):
        candidates = []
        if node.is_end:
            candidates.append((node.frequency, prefix))
        for char, child in node.children.items():
            self._build_cache(child, prefix + char)
            candidates.extend(child.top_k)
        node.top_k = heapq.nlargest(self.k, candidates, key=lambda x: x[0])

    def search_prefix(self, prefix: str) -> list[tuple[int, str]]:
        """Return cached top-k results for a prefix. O(prefix_length)."""
        node = self.root
        for char in prefix:
            if char not in node.children:
                return []
            node = node.children[char]
        return node.top_k

    def search_prefix_bruteforce(self, prefix: str) -> list[tuple[int, str]]:
        """DFS the subtree and sort - the slow way, for comparison."""
        node = self.root
        for char in prefix:
            if char not in node.children:
                return []
            node = node.children[char]
        results = []
        self._collect_all(node, prefix, results)
        results.sort(key=lambda x: x[0], reverse=True)
        return results[:self.k]

    def count_nodes(self) -> int:
        count = 0
        stack = [self.root]
        while stack:
            node = stack.pop()
            count += 1
            stack.extend(node.children.values())
        return count

    def exact_search(self, word: str) -> int:
        """Return frequency if word exists, 0 otherwise."""
        node = self.root
        for char in word:
            if char not in node.children:
                return 0
            node = node.children[char]
        return node.frequency if node.is_end else 0


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

SAMPLE_QUERIES = [
    ("weather", 1500),
    ("weather tomorrow", 900),
    ("weather radar", 600),
    ("web design", 400),
    ("website builder", 350),
    ("web developer salary", 300),
    ("python tutorial", 1200),
    ("python download", 800),
    ("python list comprehension", 500),
    ("python flask", 450),
    ("pizza near me", 2000),
    ("pizza recipe", 700),
    ("pizza hut", 1100),
    ("programming languages", 650),
    ("project management", 550),
    ("how to tie a tie", 900),
    ("how to lose weight", 1300),
    ("how to cook rice", 750),
    ("how to screenshot", 1100),
    ("how to meditate", 400),
    ("machine learning", 1000),
    ("machine learning course", 600),
    ("mac address", 350),
    ("map of the world", 500),
    ("marathon training", 280),
]


def main():
    print("=" * 60)
    print("TRIE AUTOCOMPLETE DEMO")
    print("=" * 60)

    trie = Trie(k=5)

    print(f"\nInserting {len(SAMPLE_QUERIES)} queries...")
    for query, freq in SAMPLE_QUERIES:
        trie.insert(query, freq)

    print(f"Trie built: {trie.count_nodes()} nodes")

    print("\nBuilding top-k cache at every node...")
    trie.build_top_k_cache()

    prefixes = ["we", "py", "how", "pi", "ma", "pro", "z"]

    print(f"\n{'Prefix':<10} {'Top-5 Suggestions'}")
    print("-" * 60)

    for prefix in prefixes:
        results = trie.search_prefix(prefix)
        if results:
            suggestions = [f"{word}({freq})" for freq, word in results]
            print(f"{prefix:<10} {', '.join(suggestions)}")
        else:
            print(f"{prefix:<10} (no matches)")

    print("\n" + "=" * 60)
    print("CACHED vs BRUTE-FORCE COMPARISON")
    print("=" * 60)

    import time
    test_prefix = "how"

    start = time.perf_counter()
    for _ in range(10_000):
        cached = trie.search_prefix(test_prefix)
    cached_time = time.perf_counter() - start

    start = time.perf_counter()
    for _ in range(10_000):
        brute = trie.search_prefix_bruteforce(test_prefix)
    brute_time = time.perf_counter() - start

    print(f"\nPrefix: '{test_prefix}' - 10,000 lookups each")
    print(f"  Cached top-k:     {cached_time*1000:.1f}ms total ({cached_time/10_000*1_000_000:.1f}us per lookup)")
    print(f"  Brute-force DFS:  {brute_time*1000:.1f}ms total ({brute_time/10_000*1_000_000:.1f}us per lookup)")
    print(f"  Speedup:          {brute_time/cached_time:.1f}x")

    print("\n" + "=" * 60)
    print("EXACT SEARCH")
    print("=" * 60)
    for word in ["weather", "python flask", "nonexistent query"]:
        freq = trie.exact_search(word)
        status = f"found (frequency={freq})" if freq else "not found"
        print(f"  '{word}' - {status}")


if __name__ == "__main__":
    main()
