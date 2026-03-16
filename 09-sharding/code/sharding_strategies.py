"""
Sharding Strategies - Range, Hash, and Directory
=================================================
Distributes 10,000 simulated user records across shards using three
different strategies and compares the evenness of each distribution.
Run this to see why hash-based sharding is the safest default.

    python sharding_strategies.py
"""

import hashlib
import random

NUM_USERS = 10_000
NUM_SHARDS = 4

# ---------------------------------------------------------------------------
#   Range-Based Sharding
# ---------------------------------------------------------------------------

def range_shard(user_id, boundaries):
    """
    Assigns a user to a shard based on which ID range they fall into.
    Boundaries is a sorted list of (upper_bound, shard_id) tuples.
    """
    for upper_bound, shard_id in boundaries:
        if user_id <= upper_bound:
            return shard_id
    return boundaries[-1][1]


def demo_range_sharding(user_ids):
    chunk = max(user_ids) // NUM_SHARDS
    boundaries = []
    for i in range(NUM_SHARDS):
        upper = chunk * (i + 1) if i < NUM_SHARDS - 1 else max(user_ids) + 1
        boundaries.append((upper, f"shard_{i}"))

    distribution = {f"shard_{i}": 0 for i in range(NUM_SHARDS)}
    for uid in user_ids:
        shard = range_shard(uid, boundaries)
        distribution[shard] += 1

    return distribution, boundaries


# ---------------------------------------------------------------------------
#   Hash-Based Sharding
# ---------------------------------------------------------------------------

def hash_shard(user_id, num_shards):
    """
    Hashes the user ID with MD5 and takes modulo to pick a shard.
    MD5 isn't cryptographically secure, but it distributes well.
    """
    h = hashlib.md5(str(user_id).encode()).hexdigest()
    return f"shard_{int(h, 16) % num_shards}"


def demo_hash_sharding(user_ids):
    distribution = {f"shard_{i}": 0 for i in range(NUM_SHARDS)}
    for uid in user_ids:
        shard = hash_shard(uid, NUM_SHARDS)
        distribution[shard] += 1

    return distribution


# ---------------------------------------------------------------------------
#   Directory-Based Sharding
# ---------------------------------------------------------------------------

class ShardDirectory:
    """
    Maintains an explicit mapping from tenant IDs to shards. Tenants
    can be moved between shards without rehashing.
    """

    def __init__(self, num_shards):
        self.num_shards = num_shards
        self.mapping = {}
        self._next_shard = 0

    def assign(self, tenant_id):
        if tenant_id not in self.mapping:
            self.mapping[tenant_id] = f"shard_{self._next_shard % self.num_shards}"
            self._next_shard += 1
        return self.mapping[tenant_id]

    def move(self, tenant_id, target_shard):
        self.mapping[tenant_id] = target_shard

    def lookup(self, tenant_id):
        return self.mapping.get(tenant_id)


def demo_directory_sharding(user_ids, num_tenants=20):
    directory = ShardDirectory(NUM_SHARDS)
    tenants = [f"tenant_{i}" for i in range(num_tenants)]
    for t in tenants:
        directory.assign(t)

    tenant_sizes = {}
    for t in tenants:
        tenant_sizes[t] = random.randint(100, 2000)

    distribution = {f"shard_{i}": 0 for i in range(NUM_SHARDS)}
    for tenant, size in tenant_sizes.items():
        shard = directory.lookup(tenant)
        distribution[shard] += size

    return distribution, directory, tenant_sizes


# ---------------------------------------------------------------------------
#   Output Helpers
# ---------------------------------------------------------------------------

def print_distribution(name, dist):
    total = sum(dist.values())
    ideal = total / len(dist)

    print(f"\n  {name}")
    print(f"  {'Shard':<12} {'Count':>7} {'Percent':>8} {'Deviation':>10}")
    print(f"  {'-'*40}")
    for shard in sorted(dist):
        count = dist[shard]
        pct = count / total * 100
        dev = (count - ideal) / ideal * 100
        bar = "#" * int(pct / 2)
        print(f"  {shard:<12} {count:>7} {pct:>7.1f}% {dev:>+9.1f}%  {bar}")


def skewed_user_ids(n):
    """
    Generates user IDs with gaps and clusters to simulate real-world
    unevenness. Most IDs cluster in the lower range.
    """
    ids = set()
    while len(ids) < n:
        if random.random() < 0.7:
            ids.add(random.randint(1, n // 2))
        else:
            ids.add(random.randint(n // 2, n * 10))
    return sorted(ids)


# ---------------------------------------------------------------------------
#   Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Sharding Strategies Comparison")
    print("=" * 50)
    print(f"Users: {NUM_USERS:,}  |  Shards: {NUM_SHARDS}")

    user_ids = skewed_user_ids(NUM_USERS)

    print("\n--- Strategy 1: Range-Based ---")
    range_dist, boundaries = demo_range_sharding(user_ids)
    for ub, sid in boundaries:
        print(f"  {sid}: IDs up to {ub:,}")
    print_distribution("Range Distribution", range_dist)

    print("\n--- Strategy 2: Hash-Based ---")
    hash_dist = demo_hash_sharding(user_ids)
    print_distribution("Hash Distribution", hash_dist)

    print("\n--- Strategy 3: Directory-Based ---")
    dir_dist, directory, tenant_sizes = demo_directory_sharding(user_ids)
    print("  Tenant assignments (first 8):")
    for t in sorted(directory.mapping)[:8]:
        print(f"    {t} -> {directory.mapping[t]}")
    print_distribution("Directory Distribution", dir_dist)

    print("\n--- Verdict ---")
    range_max_dev = max(abs(v - NUM_USERS / NUM_SHARDS) for v in range_dist.values())
    hash_max_dev = max(abs(v - NUM_USERS / NUM_SHARDS) for v in hash_dist.values())
    print(f"  Range max deviation from ideal:  {range_max_dev:,.0f} records")
    print(f"  Hash max deviation from ideal:   {hash_max_dev:,.0f} records")
    print(f"  Hash-based sharding wins for uniform distribution.\n")
