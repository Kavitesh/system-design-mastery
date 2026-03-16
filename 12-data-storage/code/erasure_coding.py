"""
erasure_coding.py - Erasure Coding for Fault Tolerance
=======================================================
Demonstrates how erasure coding protects data against disk failures
with less storage overhead than full replication. Uses XOR-based
parity for clarity - production systems use Reed-Solomon codes, but
the principle is identical.
"""

import hashlib

# ---------------------------------------------------------------------------
# XOR Parity Helpers
# ---------------------------------------------------------------------------

def xor_bytes(a, b):
    return bytes(x ^ y for x, y in zip(a, b))

def pad_to_length(data, length):
    if len(data) >= length:
        return data[:length]
    return data + b'\x00' * (length - len(data))

# ---------------------------------------------------------------------------
# Erasure Coding Engine
# ---------------------------------------------------------------------------

class ErasureCoder:
    """Splits data into k data chunks and produces p parity chunks using
    XOR-based coding. This simplified scheme recovers 1 lost chunk per
    parity group. Production Reed-Solomon codes handle p losses."""

    def __init__(self, data_chunks=4, parity_chunks=2):
        self.k = data_chunks
        self.p = parity_chunks

    def encode(self, data):
        chunk_size = (len(data) + self.k - 1) // self.k
        chunks = []
        for i in range(self.k):
            chunk = data[i * chunk_size:(i + 1) * chunk_size]
            chunks.append(pad_to_length(chunk, chunk_size))

        p0 = chunks[0]
        for c in chunks[1:]:
            p0 = xor_bytes(p0, c)
        parity = [p0]

        if self.p >= 2:
            p1 = chunks[0]
            for c in chunks[1:]:
                p1 = xor_bytes(p1, c[1:] + c[:1])
            parity.append(p1)

        return chunks, parity, chunk_size, len(data)

    def decode(self, chunks, parity, chunk_size, original_length, lost_indices):
        if len(lost_indices) > 1:
            print(f"  WARNING: XOR parity recovers 1 chunk. Reed-Solomon handles {self.p}.")
            lost_indices = lost_indices[:1]
        recovered = list(chunks)
        for idx in lost_indices:
            result = parity[0]
            for i, c in enumerate(recovered):
                if i != idx and c is not None:
                    result = xor_bytes(result, c)
            recovered[idx] = result
        return b''.join(recovered)[:original_length]

# ---------------------------------------------------------------------------
# Storage Overhead Comparison
# ---------------------------------------------------------------------------

def compare_overhead(data_size_mb):
    print(f"\n{'Strategy':<30s} {'Raw (MB)':<10s} {'Stored (MB)':<13s} {'Overhead':<10s}")
    print("-" * 63)
    strategies = [
        ("3x Replication",       3,      1),
        ("Erasure Coding (4,2)", 6 / 4,  1),
        ("Erasure Coding (10,4)", 14 / 10, 1),
    ]
    for name, factor, _ in strategies:
        total = data_size_mb * factor
        overhead = (factor - 1) * 100
        print(f"{name:<30s} {data_size_mb:<10.0f} {total:<13.1f} {overhead:<10.0f}%")
    savings = data_size_mb * 3 - data_size_mb * 1.4
    print(f"\n(10,4) saves {savings:.0f} MB vs 3x replication per {data_size_mb:.0f} MB of data.")

# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def run_demo():
    print("=" * 65)
    print("Erasure Coding Demo")
    print("=" * 65)

    original = b"Erasure coding saves petabytes at Facebook and Google. " * 20
    orig_hash = hashlib.sha256(original).hexdigest()[:16]
    print(f"\nOriginal data: {len(original)} bytes (SHA-256: {orig_hash})")

    coder = ErasureCoder(data_chunks=4, parity_chunks=2)
    chunks, parity, chunk_size, orig_len = coder.encode(original)

    print(f"Encoded: {len(chunks)} data + {len(parity)} parity chunks ({chunk_size} bytes each)")
    for i, c in enumerate(chunks):
        print(f"  Data   {i}: {hashlib.sha256(c).hexdigest()[:12]}...")
    for i, p in enumerate(parity):
        print(f"  Parity {i}: {hashlib.sha256(p).hexdigest()[:12]}...")

    total = sum(len(c) for c in chunks) + sum(len(p) for p in parity)
    print(f"\nStored: {total} bytes ({((total - len(original)) / len(original)) * 100:.0f}% overhead)")
    print(f"3x replication: {len(original) * 3} bytes (200% overhead)")

    print("\n--- Simulating Disk Failure ---")
    print("Destroying data chunk 2...")
    damaged = list(chunks)
    damaged[2] = None
    recovered = coder.decode(damaged, parity, chunk_size, orig_len, [2])
    status = "SUCCESS" if recovered == original else "FAILURE"
    print(f"{status}: {hashlib.sha256(recovered).hexdigest()[:16]}")

    print("\n--- Simulating Two Disk Failures ---")
    damaged2 = list(chunks)
    damaged2[1] = None
    damaged2[3] = None
    print("Destroying chunks 1 and 3...")
    coder.decode(damaged2, parity, chunk_size, orig_len, [1, 3])
    print("Reed-Solomon (production) would recover both.")

    print("\n--- Storage Overhead Comparison ---")
    compare_overhead(1000)

    print("\n" + "-" * 65)
    print("Erasure coding cuts overhead from 200% to 40-50%.")
    print("Use replication for hot data, erasure coding for cold data.")
    print("-" * 65)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run_demo()
