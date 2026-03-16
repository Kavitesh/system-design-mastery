"""
storage_types.py - Block, File, and Object Storage Simulation
=============================================================
Simulates the three fundamental storage models to show how each one
handles reads, writes, and metadata differently. Runs entirely in
memory with no external dependencies.
"""

import time
import hashlib
import json

# ---------------------------------------------------------------------------
# Block Storage Simulation
# ---------------------------------------------------------------------------

class BlockStorage:
    """Simulates a raw block device with fixed-size blocks and no metadata."""

    BLOCK_SIZE = 4096

    def __init__(self, num_blocks=1024):
        self.blocks = [None] * num_blocks

    def write_block(self, index, data):
        self.blocks[index] = data.ljust(self.BLOCK_SIZE, b'\x00')

    def read_block(self, index):
        return self.blocks[index]

    def write_data(self, data, start_block=0):
        indices = []
        for offset in range(0, len(data), self.BLOCK_SIZE):
            chunk = data[offset:offset + self.BLOCK_SIZE]
            self.write_block(start_block + len(indices), chunk)
            indices.append(start_block + len(indices))
        return indices

    def read_data(self, indices):
        return b''.join(self.read_block(i) for i in indices)

# ---------------------------------------------------------------------------
# File Storage Simulation
# ---------------------------------------------------------------------------

class FileStorage:
    """Simulates a hierarchical filesystem with directories, paths, and
    basic POSIX-style metadata."""

    def __init__(self):
        self.files = {}

    def write_file(self, path, data):
        self.files[path] = {
            "data": data,
            "meta": {"size": len(data), "created": time.time(), "permissions": "rw-r--r--"},
        }

    def read_file(self, path):
        if path not in self.files:
            raise FileNotFoundError(f"No such file: {path}")
        return self.files[path]["data"]

    def stat(self, path):
        if path not in self.files:
            raise FileNotFoundError(f"No such file: {path}")
        return self.files[path]["meta"]

# ---------------------------------------------------------------------------
# Object Storage Simulation
# ---------------------------------------------------------------------------

class ObjectStorage:
    """Simulates S3-style object storage with a flat namespace, custom
    metadata, and content-based ETags."""

    def __init__(self):
        self.objects = {}

    def put_object(self, key, data, metadata=None):
        etag = hashlib.md5(data).hexdigest()
        self.objects[key] = {
            "data": data, "metadata": metadata or {},
            "etag": etag, "size": len(data), "last_modified": time.time(),
        }
        return etag

    def get_object(self, key):
        if key not in self.objects:
            raise KeyError(f"NoSuchKey: {key}")
        return self.objects[key]["data"], self.objects[key]["metadata"]

    def head_object(self, key):
        if key not in self.objects:
            raise KeyError(f"NoSuchKey: {key}")
        obj = self.objects[key]
        return {k: v for k, v in obj.items() if k != "data"}

# ---------------------------------------------------------------------------
# Performance Comparison
# ---------------------------------------------------------------------------

def benchmark_storage():
    payload = b"System design is the art of making tradeoffs." * 100
    iterations = 1000

    print("=" * 65)
    print("Storage Types - Performance Comparison")
    print("=" * 65)
    print(f"Payload size: {len(payload)} bytes | Iterations: {iterations}\n")

    bs = BlockStorage(num_blocks=4096)
    t0 = time.perf_counter()
    for i in range(iterations):
        indices = bs.write_data(payload, start_block=(i * 2) % 2048)
    write_t = time.perf_counter() - t0
    t0 = time.perf_counter()
    for _ in range(iterations):
        bs.read_data(indices)
    read_t = time.perf_counter() - t0
    print(f"Block Storage   | write: {write_t:.4f}s | read: {read_t:.4f}s")
    print(f"                | no metadata, no naming, raw blocks only")

    fs = FileStorage()
    t0 = time.perf_counter()
    for i in range(iterations):
        fs.write_file(f"/data/bench/file_{i}.bin", payload)
    write_t = time.perf_counter() - t0
    t0 = time.perf_counter()
    for i in range(iterations):
        fs.read_file(f"/data/bench/file_{i}.bin")
    read_t = time.perf_counter() - t0
    meta = json.dumps(fs.stat("/data/bench/file_0.bin"), indent=None)
    print(f"File Storage    | write: {write_t:.4f}s | read: {read_t:.4f}s")
    print(f"                | POSIX metadata: {meta}")

    os_ = ObjectStorage()
    t0 = time.perf_counter()
    for i in range(iterations):
        os_.put_object(f"bench/obj_{i}", payload, {"experiment": "perf-test"})
    write_t = time.perf_counter() - t0
    t0 = time.perf_counter()
    for i in range(iterations):
        os_.get_object(f"bench/obj_{i}")
    read_t = time.perf_counter() - t0
    head = os_.head_object("bench/obj_0")
    print(f"Object Storage  | write: {write_t:.4f}s | read: {read_t:.4f}s")
    print(f"                | etag: {head['etag']} | custom metadata: {head['metadata']}")

    print("\n" + "-" * 65)
    print("Block is fastest (no overhead), Object is richest (metadata +")
    print("etag), File sits in between with POSIX semantics.")
    print("-" * 65)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    benchmark_storage()
