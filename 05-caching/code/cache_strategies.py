"""
Caching Strategies
===================
Implements cache-aside, write-through, write-back, and write-around
side by side with a simulated slow database (100ms latency) so the
performance difference between cache hits and misses is obvious.

Run: python cache_strategies.py
"""

import time
from collections import OrderedDict


# ---------------------------------------------------------------------------
# Simulated slow database and simple LRU cache
# ---------------------------------------------------------------------------

class SlowDB:
    def __init__(self):
        self._data = {
            "user:1": {"name": "Alice", "email": "alice@example.com"},
            "user:2": {"name": "Bob", "email": "bob@example.com"},
            "user:3": {"name": "Charlie", "email": "charlie@example.com"},
        }
        self.reads = 0
        self.writes = 0

    def get(self, key):
        time.sleep(0.1)
        self.reads += 1
        return self._data.get(key)

    def put(self, key, value):
        time.sleep(0.1)
        self.writes += 1
        self._data[key] = value


class Cache:
    def __init__(self):
        self._data = OrderedDict()
        self.hits = 0
        self.misses = 0

    def get(self, key):
        if key in self._data:
            self.hits += 1
            self._data.move_to_end(key)
            return self._data[key]
        self.misses += 1
        return None

    def set(self, key, value):
        self._data[key] = value

    def delete(self, key):
        self._data.pop(key, None)


# ---------------------------------------------------------------------------
# Strategy demos
# ---------------------------------------------------------------------------

def demo_cache_aside():
    print("=" * 60)
    print("STRATEGY 1: Cache-Aside (Lazy Loading)")
    print("=" * 60)
    db, cache = SlowDB(), Cache()

    def read(key):
        val = cache.get(key)
        if val is not None:
            return val
        val = db.get(key)
        if val is not None:
            cache.set(key, val)
        return val

    t = time.time(); r = read("user:1"); ms1 = (time.time()-t)*1000
    print(f"\n  First read (MISS):  {r['name']:<10} {ms1:.0f}ms")
    t = time.time(); r = read("user:1"); ms2 = (time.time()-t)*1000
    print(f"  Second read (HIT):  {r['name']:<10} {ms2:.1f}ms")
    print(f"  Speedup: {ms1/max(ms2,0.001):.0f}x faster from cache")

    db.put("user:1", {"name": "Alicia", "email": "alicia@example.com"})
    cache.delete("user:1")
    t = time.time(); r = read("user:1"); ms3 = (time.time()-t)*1000
    print(f"  After write (MISS): {r['name']:<10} {ms3:.0f}ms (refetched)")
    print(f"\n  DB reads: {db.reads}, writes: {db.writes} | hits: {cache.hits}, misses: {cache.misses}")


def demo_write_through():
    print("\n" + "=" * 60)
    print("STRATEGY 2: Write-Through")
    print("=" * 60)
    db, cache = SlowDB(), Cache()

    t = time.time()
    cache.set("user:1", {"name": "Alicia", "email": "alicia@example.com"})
    db.put("user:1", {"name": "Alicia", "email": "alicia@example.com"})
    ms = (time.time()-t)*1000
    print(f"\n  Write time: {ms:.0f}ms (writes to BOTH cache and DB)")

    t = time.time(); r = cache.get("user:1"); ms = (time.time()-t)*1000
    print(f"  Read after write (HIT): {r['name']:<10} {ms:.1f}ms")
    print(f"  Cache is always consistent - zero stale data window")
    print(f"  Tradeoff: every write pays double latency")


def demo_write_back():
    print("\n" + "=" * 60)
    print("STRATEGY 3: Write-Back (Write-Behind)")
    print("=" * 60)
    db, cache, queue = SlowDB(), Cache(), []

    t = time.time()
    for name, email in [("Alicia","alicia@e.com"),("Robert","rob@e.com"),("Chuck","chuck@e.com")]:
        val = {"name": name, "email": email}
        cache.set(f"user:{name}", val)
        queue.append((f"user:{name}", val))
    ms = (time.time()-t)*1000
    print(f"\n  3 writes in: {ms:.1f}ms (cache only, instant)")
    print(f"  DB writes: {db.writes} (zero - still queued)")

    t = time.time()
    while queue:
        k, v = queue.pop(0)
        db.put(k, v)
    ms = (time.time()-t)*1000
    print(f"  Flushed 3 writes in: {ms:.0f}ms (batched to DB)")
    print(f"  DB writes after flush: {db.writes}")
    print(f"\n  WARNING: If cache crashed before flush, those writes are gone")


def demo_write_around():
    print("\n" + "=" * 60)
    print("STRATEGY 4: Write-Around")
    print("=" * 60)
    db, cache = SlowDB(), Cache()

    t = time.time(); db.put("log:1", {"level": "INFO", "msg": "login"}); ms = (time.time()-t)*1000
    print(f"\n  Write: {ms:.0f}ms (DB only, cache untouched)")

    t = time.time()
    val = cache.get("log:1")
    if val is None:
        val = db.get("log:1")
        cache.set("log:1", val)
    ms = (time.time()-t)*1000
    print(f"  First read (MISS): {ms:.0f}ms")

    t = time.time(); cache.get("log:1"); ms = (time.time()-t)*1000
    print(f"  Second read (HIT): {ms:.1f}ms")
    print(f"\n  Best for write-heavy data rarely re-read (logs, audit trails)")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def print_summary():
    print("\n" + "=" * 60)
    print("STRATEGY COMPARISON")
    print("=" * 60)
    print(f"""
  {'Strategy':<20} {'Write Speed':<15} {'Read After Write':<20} {'Data Loss Risk'}
  {'-'*70}
  {'Cache-Aside':<20} {'Fast (DB)':<15} {'Miss (invalidated)':<20} {'None'}
  {'Write-Through':<20} {'Slow (both)':<15} {'Hit (always fresh)':<20} {'None'}
  {'Write-Back':<20} {'Instant':<15} {'Hit (from cache)':<20} {'YES (unflushed)'}
  {'Write-Around':<20} {'Fast (DB)':<15} {'Miss (not cached)':<20} {'None'}

  Default: Cache-Aside. Simple, safe, works for most apps.
    """)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    demo_cache_aside()
    demo_write_through()
    demo_write_back()
    demo_write_around()
    print_summary()
