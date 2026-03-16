"""
File Chunking and Deduplication
===============================
Splits files into content-addressed blocks, reassembles them,
and shows cross-file deduplication savings.

    python chunking.py
"""

import hashlib

# ---------------------------------------------------------------------------

class BlockStore:
    def __init__(self, block_size=64):
        self.block_size = block_size
        self.blocks = {}
        self.stats = {"stored": 0, "deduped": 0, "bytes_saved": 0}

    def store(self, data: bytes) -> str:
        h = hashlib.sha256(data).hexdigest()[:16]
        if h in self.blocks:
            self.stats["deduped"] += 1
            self.stats["bytes_saved"] += len(data)
            return h
        self.blocks[h] = data
        self.stats["stored"] += 1
        return h

    def retrieve(self, h: str) -> bytes:
        return self.blocks[h]

    def unique_bytes(self) -> int:
        return sum(len(b) for b in self.blocks.values())

# ---------------------------------------------------------------------------

class FileChunker:
    def __init__(self, store: BlockStore):
        self.store = store

    def chunk(self, data: bytes) -> list[str]:
        return [self.store.store(data[i:i+self.store.block_size])
                for i in range(0, len(data), self.store.block_size)]

    def reassemble(self, recipe: list[str]) -> bytes:
        return b"".join(self.store.retrieve(h) for h in recipe)

    def diff(self, old: list[str], new: list[str]) -> dict:
        o, n = set(old), set(new)
        return {"unchanged": len(o & n), "added": len(n - o), "removed": len(o - n),
                "to_transfer": sorted(n - o)}

# ---------------------------------------------------------------------------

def demo_chunking():
    print("=" * 60)
    print("DEMO 1: Chunk, hash, reassemble")
    print("=" * 60)
    store = BlockStore(block_size=32)
    c = FileChunker(store)
    data = b"The quick brown fox jumps over the lazy dog. " * 5
    recipe = c.chunk(data)
    rebuilt = c.reassemble(recipe)
    print(f"  Original:    {len(data)} bytes")
    print(f"  Blocks:      {len(recipe)} (size {store.block_size})")
    print(f"  Reassembled: {len(rebuilt)} bytes, match={rebuilt == data}")


def demo_dedup():
    print("\n" + "=" * 60)
    print("DEMO 2: Cross-file deduplication")
    print("=" * 60)
    store = BlockStore(block_size=64)
    c = FileChunker(store)
    files = {
        "report_v1.txt": b"Q1 Revenue: $1.2M\nQ2 Revenue: $1.5M\n" * 10,
        "report_v2.txt": b"Q1 Revenue: $1.2M\nQ2 Revenue: $1.5M\n" * 8
                         + b"Q3 Revenue: $1.8M\nQ4 Revenue: $2.1M\n" * 2,
        "report_copy.txt": b"Q1 Revenue: $1.2M\nQ2 Revenue: $1.5M\n" * 10,
    }
    total = 0
    for name, data in files.items():
        recipe = c.chunk(data)
        total += len(data)
        print(f"  {name}: {len(data)} bytes -> {len(recipe)} blocks")
    savings = (1 - store.unique_bytes() / total) * 100
    print(f"\n  Logical: {total} bytes | Stored: {store.unique_bytes()} bytes")
    print(f"  Deduped blocks: {store.stats['deduped']} | Savings: {savings:.1f}%")


def demo_incremental():
    print("\n" + "=" * 60)
    print("DEMO 3: Incremental upload - only changed blocks transfer")
    print("=" * 60)
    store = BlockStore(block_size=48)
    c = FileChunker(store)
    v1 = (b"Chapter 1: Intro to distributed systems. " * 4
          + b"Chapter 2: Consistency models and trade-offs. " * 4
          + b"Chapter 3: Replication strategies. " * 4)
    r1 = c.chunk(v1)
    v2 = (b"Chapter 1: Intro to distributed systems. " * 4
          + b"Chapter 2: CAP theorem and consistency. " * 4
          + b"Chapter 3: Replication strategies. " * 4)
    r2 = c.chunk(v2)
    d = c.diff(r1, r2)
    xfer = sum(len(store.retrieve(h)) for h in d["to_transfer"])
    print(f"  v1: {len(v1)} bytes, {len(r1)} blocks")
    print(f"  v2: {len(v2)} bytes, {len(r2)} blocks")
    print(f"  Unchanged: {d['unchanged']} | New: {d['added']} | Removed: {d['removed']}")
    print(f"  Full upload: {len(v2)} bytes | Incremental: {xfer} bytes | Saved: {(1-xfer/len(v2))*100:.0f}%")


def demo_content_addressing():
    print("\n" + "=" * 60)
    print("DEMO 4: Content-addressable storage")
    print("=" * 60)
    store = BlockStore(block_size=64)
    data = b"Identical content from different users at different times"
    h1, h2, h3 = store.store(data), store.store(data), store.store(data)
    print(f"  Three uploads, same content:")
    print(f"    Hash: {h1} (all three identical: {h1 == h2 == h3})")
    print(f"    Copies stored: 1 | Deduped: {store.stats['deduped']}")
    h4 = store.store(data[:-1] + b"z")
    print(f"  One-byte change: {h4} (same={h1 == h4})")

# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("File Chunking and Deduplication Demo\n")
    demo_chunking()
    demo_dedup()
    demo_incremental()
    demo_content_addressing()
    print("\nDone.")
