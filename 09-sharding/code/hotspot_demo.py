"""
Hotspot Detection and Mitigation
=================================
Simulates a social media platform where a few celebrity accounts generate
most of the write traffic. Demonstrates how naive sharding by user_id
creates hotspots, and how key salting spreads the load.

    python hotspot_demo.py
"""

import hashlib
import random

NUM_SHARDS = 6
NUM_USERS = 1_000
NUM_REQUESTS = 100_000

# ---------------------------------------------------------------------------
#   Traffic Generator (Zipfian Distribution)
# ---------------------------------------------------------------------------

def zipf_distribution(num_users, num_requests, exponent=1.5):
    """
    Generates request counts following a Zipf distribution. A small number
    of users (celebrities) generate a disproportionate share of traffic,
    which is exactly what happens on real social platforms.
    """
    weights = [1.0 / (rank ** exponent) for rank in range(1, num_users + 1)]
    total_weight = sum(weights)
    normalized = [w / total_weight for w in weights]

    user_ids = list(range(1, num_users + 1))
    requests = random.choices(user_ids, weights=normalized, k=num_requests)
    return requests


# ---------------------------------------------------------------------------
#   Sharding Without Salting (Hotspot-Prone)
# ---------------------------------------------------------------------------

def shard_by_user_id(user_id, num_shards):
    h = int(hashlib.md5(str(user_id).encode()).hexdigest(), 16)
    return h % num_shards


def run_unsalted(requests):
    shard_load = {i: 0 for i in range(NUM_SHARDS)}
    for user_id in requests:
        shard = shard_by_user_id(user_id, NUM_SHARDS)
        shard_load[shard] += 1
    return shard_load


# ---------------------------------------------------------------------------
#   Sharding With Key Salting (Hotspot-Resistant)
# ---------------------------------------------------------------------------

def shard_by_salted_key(user_id, num_shards, salt_range=10):
    """
    Appends a random salt to the shard key before hashing. This spreads
    writes for a single user across multiple shards. Reads must scatter
    across salt_range shards and gather results - a trade-off that's
    worth it for write-heavy celebrity accounts.
    """
    salt = random.randint(0, salt_range - 1)
    salted_key = f"{user_id}:{salt}"
    h = int(hashlib.md5(salted_key.encode()).hexdigest(), 16)
    return h % num_shards


def run_salted(requests, salt_range=10):
    shard_load = {i: 0 for i in range(NUM_SHARDS)}
    for user_id in requests:
        shard = shard_by_salted_key(user_id, NUM_SHARDS, salt_range)
        shard_load[shard] += 1
    return shard_load


# ---------------------------------------------------------------------------
#   Selective Salting (Only Salt Hot Keys)
# ---------------------------------------------------------------------------

def detect_hot_keys(requests, threshold_pct=5.0):
    """
    Identifies users whose traffic exceeds a percentage threshold.
    In production, you'd track this with a sliding window counter
    rather than analyzing a full batch.
    """
    counts = {}
    for uid in requests:
        counts[uid] = counts.get(uid, 0) + 1

    threshold = len(requests) * (threshold_pct / 100)
    hot = {uid: c for uid, c in counts.items() if c > threshold}
    return hot


def run_selective_salting(requests, hot_keys, salt_range=10):
    shard_load = {i: 0 for i in range(NUM_SHARDS)}
    for user_id in requests:
        if user_id in hot_keys:
            shard = shard_by_salted_key(user_id, NUM_SHARDS, salt_range)
        else:
            shard = shard_by_user_id(user_id, NUM_SHARDS)
        shard_load[shard] += 1
    return shard_load


# ---------------------------------------------------------------------------
#   Output
# ---------------------------------------------------------------------------

def print_shard_load(load, label):
    total = sum(load.values())
    ideal = total / len(load)
    max_load = max(load.values())
    min_load = min(load.values())
    skew_ratio = max_load / max(min_load, 1)

    print(f"\n  {label}")
    print(f"  {'Shard':<10} {'Requests':>9} {'Percent':>8}  {'Load Bar'}")
    print(f"  {'-'*50}")
    for shard in sorted(load):
        count = load[shard]
        pct = count / total * 100
        bar_len = int(count / max_load * 30)
        bar = "#" * bar_len
        marker = " << HOT" if count > ideal * 1.5 else ""
        print(f"  shard_{shard:<4} {count:>9,} {pct:>7.1f}%  {bar}{marker}")
    print(f"  Skew ratio (max/min): {skew_ratio:.1f}x")


# ---------------------------------------------------------------------------
#   Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Hotspot Detection and Mitigation")
    print("=" * 50)
    print(f"Users: {NUM_USERS:,}  |  Requests: {NUM_REQUESTS:,}  |  Shards: {NUM_SHARDS}")

    random.seed(42)
    requests = zipf_distribution(NUM_USERS, NUM_REQUESTS, exponent=1.5)

    top_users = {}
    for uid in requests:
        top_users[uid] = top_users.get(uid, 0) + 1
    top_5 = sorted(top_users.items(), key=lambda x: -x[1])[:5]
    print(f"\n  Top 5 users by traffic:")
    for uid, count in top_5:
        print(f"    user_{uid}: {count:,} requests ({count/NUM_REQUESTS*100:.1f}%)")

    # Scenario 1: No salting
    print("\n--- Scenario 1: Naive Sharding (no salting) ---")
    unsalted_load = run_unsalted(requests)
    print_shard_load(unsalted_load, "Unsalted Distribution")

    # Scenario 2: Salt everything
    print("\n--- Scenario 2: Universal Salting (all keys salted) ---")
    salted_load = run_salted(requests, salt_range=10)
    print_shard_load(salted_load, "Salted Distribution")

    # Scenario 3: Selective salting
    print("\n--- Scenario 3: Selective Salting (only hot keys) ---")
    hot_keys = detect_hot_keys(requests, threshold_pct=2.0)
    print(f"  Detected {len(hot_keys)} hot key(s)")
    selective_load = run_selective_salting(requests, hot_keys, salt_range=10)
    print_shard_load(selective_load, "Selective Salting Distribution")

    print("\n--- Verdict ---")
    unsalted_skew = max(unsalted_load.values()) / max(min(unsalted_load.values()), 1)
    salted_skew = max(salted_load.values()) / max(min(salted_load.values()), 1)
    selective_skew = max(selective_load.values()) / max(min(selective_load.values()), 1)
    print(f"  Unsalted skew ratio:    {unsalted_skew:.1f}x")
    print(f"  Universal salt skew:    {salted_skew:.1f}x")
    print(f"  Selective salt skew:    {selective_skew:.1f}x")
    print(f"  Selective salting gives near-uniform distribution")
    print(f"  without the read overhead of salting cold keys.\n")
