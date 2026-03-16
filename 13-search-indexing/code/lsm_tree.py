"""
lsm_tree.py
===========
Simulates a Log-Structured Merge tree with an in-memory memtable,
SSTable flushes, and size-tiered compaction. Demonstrates the write
path, read path (checking memtable then levels), and how compaction
merges overlapping SSTables.

Run:
    python lsm_tree.py
"""

import time
import bisect
from collections import OrderedDict

# ---------------------------------------------------------------------------
# SSTable - an immutable sorted run on "disk"
# ---------------------------------------------------------------------------

class SSTable:
    """An immutable sorted key-value store representing a flushed segment.
    In a real system this would be a file on disk. Here it's a sorted list
    of (key, value) pairs with binary search for lookups."""

    def __init__(self, data):
        self.entries = sorted(data.items())
        self.keys = [k for k, _ in self.entries]
        self.size = len(self.entries)

    def get(self, key):
        i = bisect.bisect_left(self.keys, key)
        if i < self.size and self.keys[i] == key:
            return self.entries[i][1]
        return None

    def __repr__(self):
        return f"SSTable({self.size} entries)"

# ---------------------------------------------------------------------------
# LSM Tree
# ---------------------------------------------------------------------------

MEMTABLE_THRESHOLD = 50   # flush after this many entries
LEVEL_RATIO = 4           # each level is ~4x the size of the previous
MAX_LEVEL = 3

class LSMTree:
    """A simplified LSM tree with a sorted memtable, multiple SSTable levels,
    and size-tiered compaction. Tombstones (deletes) use a sentinel value."""

    TOMBSTONE = "__DELETED__"

    def __init__(self):
        self.memtable = OrderedDict()
        self.levels = [[] for _ in range(MAX_LEVEL)]
        self.stats = {"writes": 0, "flushes": 0, "compactions": 0, "reads": 0}

    def put(self, key, value):
        self.memtable[key] = value
        self.stats["writes"] += 1
        if len(self.memtable) >= MEMTABLE_THRESHOLD:
            self._flush()

    def delete(self, key):
        self.put(key, self.TOMBSTONE)

    def get(self, key):
        self.stats["reads"] += 1
        if key in self.memtable:
            val = self.memtable[key]
            return None if val == self.TOMBSTONE else val
        for level in self.levels:
            for sstable in reversed(level):
                val = sstable.get(key)
                if val is not None:
                    return None if val == self.TOMBSTONE else val
        return None

    def _flush(self):
        if not self.memtable:
            return
        sstable = SSTable(dict(self.memtable))
        self.levels[0].append(sstable)
        self.memtable.clear()
        self.stats["flushes"] += 1
        self._maybe_compact(0)

    def _maybe_compact(self, level):
        max_tables = LEVEL_RATIO ** (level + 1)
        if len(self.levels[level]) < max_tables:
            return
        if level + 1 >= MAX_LEVEL:
            return
        merged = {}
        for sst in self.levels[level]:
            for k, v in sst.entries:
                merged[k] = v
        for sst in self.levels[level + 1]:
            for k, v in sst.entries:
                if k not in merged:
                    merged[k] = v
        # Remove tombstones at the deepest merge
        if level + 1 == MAX_LEVEL - 1:
            merged = {k: v for k, v in merged.items() if v != self.TOMBSTONE}
        self.levels[level] = []
        self.levels[level + 1] = [SSTable(merged)]
        self.stats["compactions"] += 1
        self._maybe_compact(level + 1)

    def level_summary(self):
        parts = []
        for i, level in enumerate(self.levels):
            total = sum(sst.size for sst in level)
            parts.append(f"L{i}: {len(level)} SSTables, {total} entries")
        return " | ".join(parts)

# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def main():
    tree = LSMTree()
    print(f"Memtable threshold: {MEMTABLE_THRESHOLD}, Level ratio: {LEVEL_RATIO}\n")

    # Phase 1 - bulk writes
    print("--- Phase 1: Writing 500 key-value pairs ---")
    start = time.perf_counter()
    for i in range(500):
        tree.put(f"key_{i:04d}", f"value_{i}")
    write_time = time.perf_counter() - start
    print(f"Write time: {write_time * 1000:.1f} ms")
    print(f"Levels:     {tree.level_summary()}")
    print(f"Stats:      {tree.stats}\n")

    # Phase 2 - point reads
    print("--- Phase 2: Reading 100 keys ---")
    start = time.perf_counter()
    hits, misses = 0, 0
    for i in range(0, 500, 5):
        val = tree.get(f"key_{i:04d}")
        if val is not None:
            hits += 1
        else:
            misses += 1
    read_time = time.perf_counter() - start
    print(f"Read time:  {read_time * 1000:.1f} ms ({hits} hits, {misses} misses)")
    print(f"Stats:      {tree.stats}\n")

    # Phase 3 - overwrites trigger compaction
    print("--- Phase 3: Overwriting 200 keys ---")
    start = time.perf_counter()
    for i in range(200):
        tree.put(f"key_{i:04d}", f"updated_{i}")
    overwrite_time = time.perf_counter() - start
    print(f"Write time: {overwrite_time * 1000:.1f} ms")
    print(f"Levels:     {tree.level_summary()}")
    print(f"Stats:      {tree.stats}\n")

    # Phase 4 - deletes
    print("--- Phase 4: Deleting 50 keys ---")
    for i in range(50):
        tree.delete(f"key_{i:04d}")
    tree._flush()  # force flush to show tombstones
    print(f"Levels:     {tree.level_summary()}")

    deleted = tree.get("key_0010")
    existing = tree.get("key_0300")
    print(f"Get deleted key_0010: {deleted}")
    print(f"Get existing key_0300: {existing}")
    print(f"\nFinal stats: {tree.stats}")


if __name__ == "__main__":
    main()
