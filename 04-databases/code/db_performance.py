"""
Database Performance Benchmarks
================================
Compares read and write performance across different data models:
relational (SQLite), key-value (dict), and document (list-of-dicts).
Demonstrates why you pick different stores for different access
patterns - the numbers speak for themselves.

Run: python db_performance.py
"""

import sqlite3
import time
import random
import string
import os

DB_FILE = "perf_bench.db"
NUM_RECORDS = 10_000
NUM_LOOKUPS = 5_000


def random_email():
    name = "".join(random.choices(string.ascii_lowercase, k=8))
    return f"{name}@example.com"


# ---------------------------------------------------------------------------
# Setup each data model with identical data
# ---------------------------------------------------------------------------

def setup_sqlite() -> sqlite3.Connection:
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    conn = sqlite3.connect(DB_FILE)
    conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)")
    conn.execute("CREATE INDEX idx_email ON users(email)")
    rows = [(i, f"user_{i}", random_email()) for i in range(NUM_RECORDS)]
    conn.executemany("INSERT INTO users VALUES (?, ?, ?)", rows)
    conn.commit()
    return conn, [r[2] for r in rows]


def setup_keyvalue(emails):
    store = {}
    for i in range(NUM_RECORDS):
        store[emails[i]] = {"id": i, "name": f"user_{i}", "email": emails[i]}
    return store


def setup_document(emails):
    docs = []
    for i in range(NUM_RECORDS):
        docs.append({"id": i, "name": f"user_{i}", "email": emails[i]})
    return docs


# ---------------------------------------------------------------------------
# Benchmarks
# ---------------------------------------------------------------------------

def bench_write_sqlite(conn, n):
    start = time.perf_counter()
    rows = [(NUM_RECORDS + i, f"new_{i}", random_email()) for i in range(n)]
    conn.executemany("INSERT INTO users VALUES (?, ?, ?)", rows)
    conn.commit()
    return time.perf_counter() - start


def bench_write_kv(store, n):
    start = time.perf_counter()
    for i in range(n):
        email = random_email()
        store[email] = {"id": NUM_RECORDS + i, "name": f"new_{i}", "email": email}
    return time.perf_counter() - start


def bench_write_doc(docs, n):
    start = time.perf_counter()
    for i in range(n):
        docs.append({"id": NUM_RECORDS + i, "name": f"new_{i}", "email": random_email()})
    return time.perf_counter() - start


def bench_read_by_key_sqlite(conn, emails, n):
    targets = random.choices(emails, k=n)
    start = time.perf_counter()
    for email in targets:
        conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    return time.perf_counter() - start


def bench_read_by_key_kv(store, emails, n):
    targets = random.choices(emails, k=n)
    start = time.perf_counter()
    for email in targets:
        _ = store.get(email)
    return time.perf_counter() - start


def bench_read_by_key_doc(docs, emails, n):
    targets = random.choices(emails, k=n)
    start = time.perf_counter()
    for email in targets:
        _ = next((d for d in docs if d["email"] == email), None)
    return time.perf_counter() - start


def bench_scan_sqlite(conn):
    start = time.perf_counter()
    conn.execute("SELECT COUNT(*) FROM users WHERE name LIKE 'user_1%'").fetchone()
    return time.perf_counter() - start


def bench_scan_doc(docs):
    start = time.perf_counter()
    _ = sum(1 for d in docs if d["name"].startswith("user_1"))
    return time.perf_counter() - start


# ---------------------------------------------------------------------------
# Run and report
# ---------------------------------------------------------------------------

def fmt(seconds):
    if seconds < 0.001:
        return f"{seconds * 1_000_000:.0f} us"
    if seconds < 1:
        return f"{seconds * 1000:.1f} ms"
    return f"{seconds:.2f} s"


def main():
    print("=" * 65)
    print(f"DATABASE PERFORMANCE BENCHMARKS ({NUM_RECORDS:,} records)")
    print("=" * 65)

    conn, emails = setup_sqlite()
    kv = setup_keyvalue(emails)
    docs = setup_document(emails)

    write_n = 1000
    print(f"\n--- WRITE {write_n:,} records ---")
    print(f"  {'SQLite (indexed):':<25} {fmt(bench_write_sqlite(conn, write_n))}")
    print(f"  {'Key-Value (dict):':<25} {fmt(bench_write_kv(kv, write_n))}")
    print(f"  {'Document (list):':<25} {fmt(bench_write_doc(docs, write_n))}")

    print(f"\n--- READ BY KEY ({NUM_LOOKUPS:,} lookups) ---")
    print(f"  {'SQLite (indexed):':<25} {fmt(bench_read_by_key_sqlite(conn, emails, NUM_LOOKUPS))}")
    print(f"  {'Key-Value (dict):':<25} {fmt(bench_read_by_key_kv(kv, emails, NUM_LOOKUPS))}")
    print(f"  {'Document (scan):':<25} {fmt(bench_read_by_key_doc(docs, emails, 100))}"
          f"  (100 lookups - full scan is slow)")

    print(f"\n--- SCAN / FILTER ---")
    print(f"  {'SQLite (LIKE query):':<25} {fmt(bench_scan_sqlite(conn))}")
    print(f"  {'Document (list comp):':<25} {fmt(bench_scan_doc(docs))}")

    conn.close()
    os.remove(DB_FILE)

    print(f"\n{'='*65}")
    print("TAKEAWAYS")
    print(f"{'='*65}")
    print("  Key-value wins on point lookups by 10-100x.")
    print("  SQLite with indexes beats unindexed scans massively.")
    print("  Document scan is O(n) per lookup - fine for small data,")
    print("  catastrophic at scale. That's why MongoDB builds indexes too.")


if __name__ == "__main__":
    main()
