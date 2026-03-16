"""
Latency Comparison
==================
Measures real-world latency of different operations to build
intuition about networking costs in system design.

Run: python latency_comparison.py
"""

import socket
import time
import os
import tempfile


def measure(label: str, func, iterations: int = 10) -> float:
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        func()
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
    avg = sum(times) / len(times)
    return avg


def dns_lookup():
    socket.gethostbyname("google.com")


def tcp_connect():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    try:
        sock.connect(("google.com", 80))
    finally:
        sock.close()


def tcp_localhost():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    port = server.getsockname()[1]
    server.listen(1)

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(("127.0.0.1", port))
    conn, _ = server.accept()

    conn.close()
    client.close()
    server.close()


def disk_write_read():
    data = b"x" * 1024
    path = os.path.join(tempfile.gettempdir(), "latency_test.tmp")
    with open(path, "wb") as f:
        f.write(data)
    with open(path, "rb") as f:
        f.read()
    os.remove(path)


def memory_operation():
    data = list(range(1000))
    _ = sum(data)


def main():
    print("=" * 65)
    print("  LATENCY COMPARISON - Real-World Measurements")
    print("=" * 65)
    print()
    print("Measuring average latency across 10 iterations each...")
    print()

    results = []

    # Memory
    print("  [1/5] Memory operation (sum 1000 integers)...", end="", flush=True)
    t = measure("Memory operation", memory_operation, iterations=100)
    results.append(("Memory (sum 1000 ints)", t))
    print(f" {t:.4f}ms")

    # Disk
    print("  [2/5] Disk write + read (1KB)...", end="", flush=True)
    t = measure("Disk write+read 1KB", disk_write_read)
    results.append(("Disk write+read (1KB)", t))
    print(f" {t:.2f}ms")

    # TCP localhost
    print("  [3/5] TCP connect (localhost)...", end="", flush=True)
    t = measure("TCP localhost", tcp_localhost)
    results.append(("TCP connect (localhost)", t))
    print(f" {t:.2f}ms")

    # DNS lookup
    print("  [4/5] DNS lookup (google.com)...", end="", flush=True)
    t = measure("DNS lookup", dns_lookup)
    results.append(("DNS lookup (google.com)", t))
    print(f" {t:.2f}ms")

    # TCP remote
    print("  [5/5] TCP connect (google.com:80)...", end="", flush=True)
    t = measure("TCP remote", tcp_connect, iterations=5)
    results.append(("TCP connect (google.com)", t))
    print(f" {t:.2f}ms")

    # Display results
    print()
    print("=" * 65)
    print("  RESULTS")
    print("=" * 65)
    print()

    max_time = max(r[1] for r in results)
    bar_width = 40

    for label, ms in results:
        bar_len = max(1, int((ms / max_time) * bar_width))
        bar = "#" * bar_len
        print(f"  {label:<30} {ms:>8.3f}ms  |{bar}")

    print()
    print("-" * 65)
    print()

    # Reference numbers
    print("REFERENCE LATENCY NUMBERS (every developer should know):")
    print()
    print(f"  {'Operation':<40} {'Latency':>12}")
    print(f"  {'-'*40} {'-'*12}")
    reference = [
        ("L1 cache reference", "1 ns"),
        ("L2 cache reference", "4 ns"),
        ("RAM reference", "100 ns"),
        ("SSD random read", "16 us"),
        ("HDD random read", "2 ms"),
        ("Network round trip (same DC)", "0.5 ms"),
        ("Network round trip (cross-continent)", "150 ms"),
        ("DNS lookup (uncached)", "20-120 ms"),
        ("TLS handshake", "10-200 ms"),
        ("HTTP request (same region)", "20-80 ms"),
    ]
    for op, lat in reference:
        print(f"  {op:<40} {lat:>12}")

    print()
    print("KEY INSIGHT:")
    print("  Network operations are 1000x+ slower than memory operations.")
    print("  This is why caching, connection pooling, and minimizing")
    print("  round trips are critical in system design.")
    print("=" * 65)


if __name__ == "__main__":
    main()
