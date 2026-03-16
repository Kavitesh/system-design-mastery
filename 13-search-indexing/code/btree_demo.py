"""
btree_demo.py
=============
A minimal B-tree implementation that supports insert, search, and range
queries. Compares indexed lookup performance against a naive linear scan
to make the O(log n) vs O(n) difference concrete.

Run:
    python btree_demo.py
"""

import time
import random

# ---------------------------------------------------------------------------
# B-Tree node and tree
# ---------------------------------------------------------------------------

MIN_DEGREE = 50  # each node holds up to 2*MIN_DEGREE - 1 keys


class BTreeNode:
    def __init__(self, leaf=True):
        self.keys = []
        self.children = []
        self.leaf = leaf


class BTree:
    """B-tree of order 2*MIN_DEGREE. Supports insert, point lookup, and
    range queries. Internal nodes keep keys sorted; leaves store the
    actual key-value pairs (here values are just the keys themselves)."""

    def __init__(self, t=MIN_DEGREE):
        self.t = t
        self.root = BTreeNode()

    def search(self, node, key):
        i = 0
        while i < len(node.keys) and key > node.keys[i]:
            i += 1
        if i < len(node.keys) and key == node.keys[i]:
            return True
        if node.leaf:
            return False
        return self.search(node.children[i], key)

    def insert(self, key):
        root = self.root
        if len(root.keys) == 2 * self.t - 1:
            new_root = BTreeNode(leaf=False)
            new_root.children.append(self.root)
            self._split_child(new_root, 0)
            self.root = new_root
        self._insert_non_full(self.root, key)

    def _insert_non_full(self, node, key):
        i = len(node.keys) - 1
        if node.leaf:
            node.keys.append(None)
            while i >= 0 and key < node.keys[i]:
                node.keys[i + 1] = node.keys[i]
                i -= 1
            node.keys[i + 1] = key
        else:
            while i >= 0 and key < node.keys[i]:
                i -= 1
            i += 1
            if len(node.children[i].keys) == 2 * self.t - 1:
                self._split_child(node, i)
                if key > node.keys[i]:
                    i += 1
            self._insert_non_full(node.children[i], key)

    def _split_child(self, parent, idx):
        t = self.t
        child = parent.children[idx]
        new_node = BTreeNode(leaf=child.leaf)
        parent.keys.insert(idx, child.keys[t - 1])
        parent.children.insert(idx + 1, new_node)
        new_node.keys = child.keys[t:]
        child.keys = child.keys[: t - 1]
        if not child.leaf:
            new_node.children = child.children[t:]
            child.children = child.children[:t]

    def range_query(self, low, high):
        results = []
        self._range_collect(self.root, low, high, results)
        return results

    def _range_collect(self, node, low, high, results):
        i = 0
        while i < len(node.keys) and node.keys[i] < low:
            i += 1
        while i < len(node.keys) and node.keys[i] <= high:
            if not node.leaf:
                self._range_collect(node.children[i], low, high, results)
            results.append(node.keys[i])
            i += 1
        if not node.leaf and i < len(node.children):
            self._range_collect(node.children[i], low, high, results)

# ---------------------------------------------------------------------------
# Linear scan baseline
# ---------------------------------------------------------------------------

def linear_search(data, key):
    for item in data:
        if item == key:
            return True
    return False

def linear_range(data, low, high):
    return [x for x in data if low <= x <= high]


# ---------------------------------------------------------------------------
# Performance comparison
# ---------------------------------------------------------------------------

def main():
    n = 10_000
    print(f"Building B-tree with {n:,} keys (MIN_DEGREE={MIN_DEGREE})...\n")

    keys = random.sample(range(n * 10), n)
    tree = BTree()
    for k in keys:
        tree.insert(k)
    sorted_keys = sorted(keys)

    search_targets = random.sample(keys, 500)

    # Point lookups - B-tree
    start = time.perf_counter()
    for k in search_targets:
        tree.search(tree.root, k)
    btree_time = time.perf_counter() - start

    # Point lookups - linear scan
    start = time.perf_counter()
    for k in search_targets:
        linear_search(sorted_keys, k)
    linear_time = time.perf_counter() - start

    print("Point lookups (500 searches):")
    print(f"  B-tree:      {btree_time * 1000:8.2f} ms")
    print(f"  Linear scan: {linear_time * 1000:8.2f} ms")
    print(f"  Speedup:     {linear_time / btree_time:8.1f}x\n")

    # Range queries
    low, high = n * 2, n * 3
    start = time.perf_counter()
    btree_results = tree.range_query(low, high)
    btree_range_time = time.perf_counter() - start

    start = time.perf_counter()
    linear_results = linear_range(sorted_keys, low, high)
    linear_range_time = time.perf_counter() - start

    print(f"Range query [{low:,}, {high:,}] ({len(btree_results):,} results):")
    print(f"  B-tree:      {btree_range_time * 1000:8.2f} ms")
    print(f"  Linear scan: {linear_range_time * 1000:8.2f} ms")
    print(f"  Speedup:     {linear_range_time / max(btree_range_time, 1e-9):8.1f}x\n")

    # Verify correctness
    assert set(btree_results) == set(linear_results), "Range query mismatch!"
    print("All results verified correct.")


if __name__ == "__main__":
    main()
