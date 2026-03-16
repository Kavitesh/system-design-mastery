"""
Fan-Out Strategy Comparison
==============================

Benchmarks fan-out-on-write vs fan-out-on-read vs hybrid.
Simulates a social network with celebrities, measures write cost and read latency.
"""

import time
import random
from collections import defaultdict

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

NUM_USERS, NUM_CELEBS, CELEB_FOLLOWERS = 1_000, 5, 500
NUM_POSTS, FEED_SIZE = 200, 50
random.seed(42)

# ---------------------------------------------------------------------------
# Social graph
# ---------------------------------------------------------------------------

def build_graph():
    fol, fing = defaultdict(set), defaultdict(set)
    users = [f"user_{i}" for i in range(NUM_USERS)]
    celebs = users[:NUM_CELEBS]
    normals = users[NUM_CELEBS:]
    for c in celebs:
        for f in random.sample(normals, CELEB_FOLLOWERS):
            fol[c].add(f); fing[f].add(c)
    for u in normals:
        others = [x for x in normals if x != u]
        for f in random.sample(others, min(random.randint(5, 40), len(others))):
            fol[f].add(u); fing[u].add(f)
    return users, celebs, fol, fing

# ---------------------------------------------------------------------------
# Simulations
# ---------------------------------------------------------------------------

def sim_push(users, fol, fing, posts):
    cache, writes = defaultdict(list), 0
    t0 = time.perf_counter()
    for pid, author in posts:
        for f in fol[author]:
            cache[f].append(pid); writes += 1
    wt = (time.perf_counter() - t0) * 1000
    reads = []
    for r in random.sample(users, 100):
        t = time.perf_counter()
        _ = list(reversed(cache[r][-FEED_SIZE:]))
        reads.append(time.perf_counter() - t)
    return writes, wt, reads


def sim_pull(users, fol, fing, posts):
    up = defaultdict(list)
    t0 = time.perf_counter()
    for pid, author in posts:
        up[author].append((pid, time.perf_counter()))
    wt = (time.perf_counter() - t0) * 1000
    reads = []
    for r in random.sample(users, 100):
        t = time.perf_counter()
        merged = []
        for fe in fing[r]:
            merged.extend(up[fe][-FEED_SIZE:])
        merged.sort(key=lambda x: x[1], reverse=True)
        _ = merged[:FEED_SIZE]
        reads.append(time.perf_counter() - t)
    return len(posts), wt, reads


def sim_hybrid(users, celebs, fol, fing, posts):
    cs = set(celebs)
    cache, up, writes = defaultdict(list), defaultdict(list), 0
    t0 = time.perf_counter()
    for pid, author in posts:
        up[author].append((pid, time.perf_counter()))
        if author not in cs:
            for f in fol[author]:
                cache[f].append(pid); writes += 1
        writes += 1
    wt = (time.perf_counter() - t0) * 1000
    reads = []
    for r in random.sample(users, 100):
        t = time.perf_counter()
        cached = [(pid, 0) for pid in cache[r][-FEED_SIZE:]]
        celeb = []
        for fe in fing[r]:
            if fe in cs:
                celeb.extend(up[fe][-FEED_SIZE:])
        all_p = cached + celeb
        all_p.sort(key=lambda x: x[1], reverse=True)
        _ = all_p[:FEED_SIZE]
        reads.append(time.perf_counter() - t)
    return writes, wt, reads

# ---------------------------------------------------------------------------
# Run benchmarks
# ---------------------------------------------------------------------------

def pr(writes, wt, reads):
    avg = sum(reads) / len(reads) * 1e6
    p99 = sorted(reads)[int(len(reads) * 0.99)] * 1e6
    print(f"  Writes: {writes:>8,} | Write time: {wt:>6.2f} ms | Avg read: {avg:>7.1f} us | p99: {p99:>7.1f} us")


def main():
    print("Fan-Out Strategy Comparison")
    print("=" * 70)
    print(f"Users: {NUM_USERS} ({NUM_CELEBS} celebrities, {CELEB_FOLLOWERS} followers each)")
    print(f"Posts: {NUM_POSTS} | Feed size: {FEED_SIZE}\n")

    users, celebs, fol, fing = build_graph()
    posts = [(f"post_{i}", random.choice(users)) for i in range(NUM_POSTS)]
    cp = sum(1 for _, a in posts if a in celebs)
    print(f"Post mix: {cp} celebrity, {NUM_POSTS - cp} normal\n")

    print("Strategy 1: Fan-Out on Write (push)")
    w1, wt1, r1 = sim_push(users, fol, fing, posts); pr(w1, wt1, r1)

    print("\nStrategy 2: Fan-Out on Read (pull)")
    w2, wt2, r2 = sim_pull(users, fol, fing, posts); pr(w2, wt2, r2)

    print("\nStrategy 3: Hybrid (push normal, pull celebrities)")
    w3, wt3, r3 = sim_hybrid(users, celebs, fol, fing, posts); pr(w3, wt3, r3)

    print("\n" + "=" * 70)
    print("Summary")
    avg1, avg2 = sum(r1)/len(r1), sum(r2)/len(r2)
    print(f"  Push does {w1/w2:.0f}x more writes than pull")
    print(f"  Pull has {avg2/max(avg1, 1e-9):.1f}x higher read latency than push")
    print(f"  Hybrid cuts writes by {(1 - w3/w1)*100:.0f}% vs pure push")
    print("\nTakeaway: hybrid gives you cheap celebrity writes + fast reads for everyone.")


if __name__ == "__main__":
    main()
