"""
NoSQL Comparison - Three Data Models Side by Side
==================================================
Simulates document store, key-value store, and column-family
store patterns using pure Python. No external databases needed -
the goal is to show how each model organizes data and what
trade-offs come with that organization.

Run: python nosql_comparison.py
"""

import time


# ---------------------------------------------------------------------------
# Document store (like MongoDB)
# ---------------------------------------------------------------------------

class DocumentStore:
    """
    Stores JSON-like documents in named collections. Each document can
    have a completely different shape - a laptop and a t-shirt coexist
    in the same collection without a shared schema.
    """

    def __init__(self):
        self._collections = {}

    def insert(self, collection: str, doc: dict):
        self._collections.setdefault(collection, []).append(doc)

    def find(self, collection: str, query: dict) -> list:
        results = []
        for doc in self._collections.get(collection, []):
            if all(doc.get(k) == v for k, v in query.items()):
                results.append(doc)
        return results

    def find_nested(self, collection: str, path: str, value) -> list:
        keys = path.split(".")
        results = []
        for doc in self._collections.get(collection, []):
            obj = doc
            for k in keys:
                obj = obj.get(k, {}) if isinstance(obj, dict) else None
            if obj == value:
                results.append(doc)
        return results


# ---------------------------------------------------------------------------
# Key-value store (like Redis)
# ---------------------------------------------------------------------------

class KeyValueStore:
    """
    Pure key-based lookups with optional TTL. O(1) get/set but no way
    to query by value - you need the exact key.
    """

    def __init__(self):
        self._data = {}
        self._expires = {}

    def set(self, key: str, value, ttl: float = None):
        self._data[key] = value
        if ttl:
            self._expires[key] = time.time() + ttl

    def get(self, key: str):
        if key in self._expires and time.time() > self._expires[key]:
            del self._data[key]
            del self._expires[key]
            return None
        return self._data.get(key)


# ---------------------------------------------------------------------------
# Column-family store (like Cassandra)
# ---------------------------------------------------------------------------

class ColumnFamilyStore:
    """
    Data organized as rows with column families. Each row can have
    different columns, and reads target specific column families
    rather than entire rows. Optimized for known query patterns.
    """

    def __init__(self):
        self._rows = {}

    def put(self, row_key: str, family: str, columns: dict):
        self._rows.setdefault(row_key, {}).setdefault(family, {}).update(columns)

    def get_family(self, row_key: str, family: str) -> dict:
        return self._rows.get(row_key, {}).get(family, {})

    def get_row(self, row_key: str) -> dict:
        return self._rows.get(row_key, {})


# ---------------------------------------------------------------------------
# Demos
# ---------------------------------------------------------------------------

def demo_document():
    print("=" * 60)
    print("DOCUMENT STORE (like MongoDB)")
    print("=" * 60)

    ds = DocumentStore()
    ds.insert("products", {
        "sku": "LAPTOP-001", "name": "ThinkPad X1", "price": 1299.99,
        "specs": {"cpu": "i7", "ram_gb": 16, "storage_gb": 512},
    })
    ds.insert("products", {
        "sku": "TEE-001", "name": "Dev Tee", "price": 29.99,
        "sizes": ["S", "M", "L"], "material": "cotton",
    })

    print("\nAll products:")
    for doc in ds.find("products", {}):
        print(f"  {doc['sku']}: {doc['name']} - ${doc['price']}")
        extra = [k for k in doc if k not in ("sku", "name", "price")]
        print(f"    unique fields: {extra}")

    print("\nQuery nested field (specs.cpu = 'i7'):")
    for doc in ds.find_nested("products", "specs.cpu", "i7"):
        print(f"  {doc['name']} - {doc['specs']}")

    print("\n  Takeaway: each document has its own shape. No migrations needed.")


def demo_keyvalue():
    print("\n" + "=" * 60)
    print("KEY-VALUE STORE (like Redis)")
    print("=" * 60)

    kv = KeyValueStore()
    kv.set("session:abc", {"user_id": 42, "role": "admin"}, ttl=2.0)
    kv.set("config:retries", 3)
    kv.set("cache:user:42", {"name": "Alice", "email": "a@b.com"})

    print(f"\n  GET session:abc   -> {kv.get('session:abc')}")
    print(f"  GET config:retries -> {kv.get('config:retries')}")
    print(f"  GET cache:user:42 -> {kv.get('cache:user:42')}")
    print(f"  GET nonexistent   -> {kv.get('nonexistent')}")

    print("\n  Waiting 2.5s for session TTL to expire...")
    time.sleep(2.5)
    print(f"  GET session:abc   -> {kv.get('session:abc')} (expired)")

    print("\n  Takeaway: O(1) speed, but you can only look up by exact key.")


def demo_columnfamily():
    print("\n" + "=" * 60)
    print("COLUMN-FAMILY STORE (like Cassandra)")
    print("=" * 60)

    cf = ColumnFamilyStore()
    cf.put("user:alice", "profile", {"name": "Alice", "email": "alice@dev.io"})
    cf.put("user:alice", "activity", {"last_login": "2025-03-15", "posts": 42})
    cf.put("user:alice", "prefs", {"theme": "dark", "lang": "en"})

    cf.put("user:bob", "profile", {"name": "Bob", "email": "bob@dev.io"})
    cf.put("user:bob", "activity", {"last_login": "2025-03-14"})

    print("\nRead just Alice's profile (single column family):")
    print(f"  {cf.get_family('user:alice', 'profile')}")

    print("\nRead Alice's entire row (all column families):")
    for family, cols in cf.get_row("user:alice").items():
        print(f"  [{family}] {cols}")

    print("\nBob's row has fewer column families - that's fine:")
    for family, cols in cf.get_row("user:bob").items():
        print(f"  [{family}] {cols}")

    print("\n  Takeaway: reads target specific column families. Each row")
    print("  can have different columns. Great for wide, sparse data.")


def summary():
    print("\n" + "=" * 60)
    print("COMPARISON SUMMARY")
    print("=" * 60)
    print(f"\n  {'Model':<18} {'Query By':<20} {'Best For'}")
    print(f"  {'-'*18} {'-'*20} {'-'*25}")
    print(f"  {'Document':<18} {'Any field':<20} {'Varied schemas, APIs'}")
    print(f"  {'Key-Value':<18} {'Exact key only':<20} {'Cache, sessions, config'}")
    print(f"  {'Column-Family':<18} {'Row key + family':<20} {'Time-series, wide data'}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    demo_document()
    demo_keyvalue()
    demo_columnfamily()
    summary()


if __name__ == "__main__":
    main()
