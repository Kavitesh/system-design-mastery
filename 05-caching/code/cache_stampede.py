"""
Cache Stampede (Thundering Herd)
=================================
Demonstrates what happens when a popular cache key expires and many
concurrent requests all miss at once. Then shows two solutions:
locking (mutex) and probabilistic early expiration.

Run: python cache_stampede.py
"""

import time
import math
import random
import threading


# ---------------------------------------------------------------------------
# Shared infrastructure
# ---------------------------------------------------------------------------

class SlowDB:
    def __init__(self):
        self._data = {"trending": "Top 10 trending posts"}
        self.queries = 0
        self.peak_concurrent = 0
        self._active = 0
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            self._active += 1
            self.peak_concurrent = max(self.peak_concurrent, self._active)
        time.sleep(0.2)
        with self._lock:
            self.queries += 1
            self._active -= 1
        return self._data.get(key)

    def reset(self):
        self.queries = 0
        self.peak_concurrent = 0


class TTLCache:
    def __init__(self):
        self._data = {}
        self._exp = {}
        self._locks = {}
        self._lock = threading.Lock()

    def get(self, key):
        if key in self._data and time.time() <= self._exp.get(key, 0):
            return self._data[key]
        self._data.pop(key, None)
        self._exp.pop(key, None)
        return None

    def set(self, key, value, ttl):
        self._data[key] = value
        self._exp[key] = time.time() + ttl

    def get_expiry(self, key):
        return self._exp.get(key, 0)

    def acquire_lock(self, key, timeout=5):
        with self._lock:
            if key not in self._locks:
                self._locks[key] = threading.Lock()
        return self._locks[key].acquire(timeout=timeout)

    def release_lock(self, key):
        if key in self._locks:
            try: self._locks[key].release()
            except RuntimeError: pass

    def clear(self):
        self._data.clear(); self._exp.clear()


# ---------------------------------------------------------------------------
# Scenario 1: No protection (the stampede)
# ---------------------------------------------------------------------------

def demo_no_protection():
    print("=" * 60)
    print("SCENARIO 1: No Stampede Protection")
    print("=" * 60)
    db, cache = SlowDB(), TTLCache()
    n = 20
    stats = {"hits": 0, "misses": 0}
    lock = threading.Lock()

    def worker():
        val = cache.get("trending")
        if val:
            with lock: stats["hits"] += 1
            return
        val = db.get("trending")
        cache.set("trending", val, ttl=10)
        with lock: stats["misses"] += 1

    print(f"\n  {n} concurrent requests hit an expired key...")
    threads = [threading.Thread(target=worker) for _ in range(n)]
    t = time.time()
    for th in threads: th.start()
    for th in threads: th.join()
    ms = (time.time()-t)*1000

    print(f"  DB queries:      {db.queries}")
    print(f"  Peak concurrent: {db.peak_concurrent}")
    print(f"  Total time:      {ms:.0f}ms")
    print(f"\n  All {n} requests hit the DB - that's the stampede.")


# ---------------------------------------------------------------------------
# Scenario 2: Locking (mutex)
# ---------------------------------------------------------------------------

def demo_locking():
    print("\n" + "=" * 60)
    print("SCENARIO 2: Locking (Mutex) Protection")
    print("=" * 60)
    db, cache = SlowDB(), TTLCache()
    n = 20
    stats = {"fetched": 0, "waited": 0}
    lock = threading.Lock()

    def worker():
        val = cache.get("trending")
        if val:
            with lock: stats["waited"] += 1
            return
        if cache.acquire_lock("trending"):
            try:
                val = cache.get("trending")
                if val:
                    with lock: stats["waited"] += 1
                    return
                val = db.get("trending")
                cache.set("trending", val, ttl=10)
                with lock: stats["fetched"] += 1
            finally:
                cache.release_lock("trending")
        else:
            time.sleep(0.05)
            with lock: stats["waited"] += 1

    print(f"\n  {n} concurrent requests hit an expired key...")
    threads = [threading.Thread(target=worker) for _ in range(n)]
    t = time.time()
    for th in threads: th.start()
    for th in threads: th.join()
    ms = (time.time()-t)*1000

    print(f"  DB queries:      {db.queries}")
    print(f"  Peak concurrent: {db.peak_concurrent}")
    print(f"  Fetched from DB: {stats['fetched']}")
    print(f"  Waited on lock:  {stats['waited']}")
    print(f"  Total time:      {ms:.0f}ms")
    print(f"\n  Only 1 request hit the DB. The rest waited for the cached result.")


# ---------------------------------------------------------------------------
# Scenario 3: Probabilistic early expiration
# ---------------------------------------------------------------------------

def demo_probabilistic():
    print("\n" + "=" * 60)
    print("SCENARIO 3: Probabilistic Early Expiration")
    print("=" * 60)
    cache = TTLCache()
    ttl, beta = 10.0, 1.0
    cache.set("trending", "Top 10 posts", ttl=ttl)

    print(f"\n  Key cached with TTL={ttl}s. Simulating reads as TTL counts down.")
    print(f"  Each read rolls the dice on whether to refresh early.\n")

    refreshes = 0
    for left in [9, 7, 5, 3, 2, 1, 0.5, 0.1]:
        fake_now = cache.get_expiry("trending") - left
        should = fake_now - (ttl * beta * math.log(random.random())) > cache.get_expiry("trending")
        refreshes += should
        tag = "<-- REFRESH" if should else ""
        print(f"  TTL remaining: {left:>5.1f}s  refresh? {'yes' if should else 'no':>3}  {tag}")

    print(f"\n  {refreshes} early refresh(es) out of 8 reads.")
    print(f"  With many concurrent readers, someone will refresh before expiry.")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def print_summary():
    print("\n" + "=" * 60)
    print("STAMPEDE PROTECTION COMPARISON")
    print("=" * 60)
    print(f"""
  {'Approach':<25} {'DB Queries':<14} {'Tradeoff'}
  {'-'*55}
  {'No protection':<25} {'N (all miss)':<14} {'DB gets hammered'}
  {'Locking (mutex)':<25} {'1':<14} {'Others wait briefly'}
  {'Probabilistic expiry':<25} {'1-2':<14} {'Occasional extra refresh'}
  {'Background refresh':<25} {'1 (scheduled)':<14} {'Must know hot keys upfront'}

  Default: use locking. It works for any key without foreknowledge.
    """)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    random.seed(42)
    demo_no_protection()
    demo_locking()
    demo_probabilistic()
    print_summary()
