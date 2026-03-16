"""
Feed Cache with Invalidation
================================

Simulates Redis sorted-set caching for news feeds. Demonstrates
write-through, invalidation, cold-start, and hit-rate stats.
"""

import time
import random
from collections import defaultdict

random.seed(42)

# ---------------------------------------------------------------------------
# Sorted set (mimics Redis ZADD / ZREVRANGE / ZREM)
# ---------------------------------------------------------------------------

class SortedSet:
    def __init__(self, cap=800):
        self.entries, self.cap = {}, cap

    def add(self, member, score):
        self.entries[member] = score
        if len(self.entries) > self.cap:
            del self.entries[min(self.entries, key=self.entries.get)]

    def remove(self, member): self.entries.pop(member, None)
    def top_n(self, n): return [m for m, _ in sorted(self.entries.items(), key=lambda x: x[1], reverse=True)[:n]]
    def __len__(self): return len(self.entries)

# ---------------------------------------------------------------------------
# Cache + DB
# ---------------------------------------------------------------------------

class FeedCache:
    def __init__(self, ttl=3600):
        self.data, self.ttl, self.accessed = defaultdict(SortedSet), ttl, {}
        self.stats = {"hits": 0, "misses": 0, "invalidations": 0}

    def get(self, uid, count=20):
        if uid in self.data and len(self.data[uid]) > 0:
            if time.time() - self.accessed.get(uid, 0) < self.ttl:
                self.stats["hits"] += 1; self.accessed[uid] = time.time()
                return self.data[uid].top_n(count), "HIT"
            del self.data[uid]
        self.stats["misses"] += 1
        return None, "MISS"

    def push(self, uid, pid, ts):
        self.data[uid].add(pid, ts); self.accessed[uid] = time.time()

    def invalidate(self, uid, pid):
        if uid in self.data:
            self.data[uid].remove(pid); self.stats["invalidations"] += 1

    def build(self, uid, posts):
        ss = SortedSet()
        for pid, ts in posts:
            ss.add(pid, ts)
        self.data[uid] = ss; self.accessed[uid] = time.time()
        return ss.top_n(20)


class PostDB:
    def __init__(self):
        self.posts, self.by_author, self.queries = {}, defaultdict(list), 0

    def insert(self, pid, author, ts):
        self.posts[pid] = {"post_id": pid, "author": author, "timestamp": ts}
        self.by_author[author].append(pid)

    def recent(self, uids, limit=50):
        self.queries += 1
        r = [(pid, self.posts[pid]["timestamp"]) for uid in uids for pid in self.by_author[uid][-limit:]]
        r.sort(key=lambda x: x[1], reverse=True)
        return r[:limit]

# ---------------------------------------------------------------------------
# Social graph + demo
# ---------------------------------------------------------------------------

fol_map, fing_map = defaultdict(set), defaultdict(set)

def setup(n=50):
    users = [f"user_{i}" for i in range(n)]
    for u in users:
        for t in random.sample([x for x in users if x != u], random.randint(5, 20)):
            fol_map[t].add(u); fing_map[u].add(t)
    return users

def main():
    print("Feed Cache with Invalidation Demo")
    print("=" * 55)
    users = setup(50)
    print(f"Graph: {len(users)} users, {sum(len(fol_map[u]) for u in users)/len(users):.1f} avg followers")

    db, now = PostDB(), time.time()
    for u in users:
        for j in range(random.randint(3, 15)):
            db.insert(f"post_{u}_{j}", u, now - random.uniform(0, 86400))
    print(f"Seeded {sum(len(v) for v in db.by_author.values())} posts")

    cache = FeedCache(ttl=3600)
    for u in users:
        cache.build(u, db.recent(list(fing_map[u]), 50))
    print(f"Cache warmed for {len(users)} users")

    # Scenario 1: write-through
    print("\n1. Write-Through on New Post")
    print("-" * 55)
    pid, ts = "post_new_001", time.time()
    db.insert(pid, "user_0", ts)
    for f in fol_map["user_0"]:
        cache.push(f, pid, ts)
    s = next(iter(fol_map["user_0"]))
    feed, status = cache.get(s, 5)
    print(f"  Fanned out to {len(fol_map['user_0'])} followers | {s} feed ({status}): new post = {pid in feed}")

    # Scenario 2: invalidation
    print("\n2. Invalidation on Post Deletion")
    print("-" * 55)
    pid2, ts2 = "post_doomed", time.time()
    db.insert(pid2, "user_1", ts2)
    for f in fol_map["user_1"]:
        cache.push(f, pid2, ts2)
    s2 = next(iter(fol_map["user_1"]))
    before, _ = cache.get(s2, 5)
    print(f"  Before: {pid2 in before}", end="")
    for f in fol_map["user_1"]:
        cache.invalidate(f, pid2)
    after, _ = cache.get(s2, 5)
    print(f" | After: {pid2 in after} | Invalidated {len(fol_map['user_1'])} caches")

    # Scenario 3: cold start
    print("\n3. Cold Start - Build from DB")
    print("-" * 55)
    cache.data.pop("user_49", None)
    cache.accessed.pop("user_49", None)
    _, st = cache.get("user_49")
    q0 = db.queries
    cache.build("user_49", db.recent(list(fing_map["user_49"]), 50))
    _, st2 = cache.get("user_49")
    print(f"  First: {st} | DB queries: {db.queries - q0} | Second: {st2}")

    # Scenario 4: hit rate
    print("\n4. Hit Rate Under Load (500 requests)")
    print("-" * 55)
    cache.stats = {"hits": 0, "misses": 0, "invalidations": 0}
    q0 = db.queries
    for _ in range(500):
        u = random.choice(users)
        feed, st = cache.get(u, 20)
        if st == "MISS":
            cache.build(u, db.recent(list(fing_map[u]), 50))
    t = cache.stats["hits"] + cache.stats["misses"]
    dq = db.queries - q0
    print(f"  Hits: {cache.stats['hits']} | Misses: {cache.stats['misses']} | Rate: {cache.stats['hits']/t*100:.1f}%")
    print(f"  DB queries: {dq} with cache vs 500 without ({(1-dq/500)*100:.0f}% reduction)")

    print("\n" + "=" * 55)
    print("Takeaways: write-through keeps feeds fresh, invalidation handles")
    print("deletes, cold start falls back to pull, cache cuts DB load 80%+.")


if __name__ == "__main__":
    main()
