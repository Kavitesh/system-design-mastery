"""
Cache Cluster with Replication and Failover
============================================
Simulates a cache cluster where each shard has a primary and one replica.
Writes go to the primary and replicate asynchronously to the replica.
When a primary dies, the replica gets promoted and serves reads without
data loss (for keys that had time to replicate).

Run: python cache_cluster.py
"""

import hashlib
import bisect
import time
import random
from collections import defaultdict


# ---------------------------------------------------------------------------
# Shard - a primary/replica pair
# ---------------------------------------------------------------------------

class CacheShard:
    """A single shard with a primary node and one replica."""

    def __init__(self, shard_id: str):
        self.shard_id = shard_id
        self._primary = {}
        self._replica = {}
        self._primary_alive = True
        self._replica_alive = True
        self._pending_replication = []
        self.stats = {"reads": 0, "writes": 0, "failovers": 0,
                      "replica_reads": 0}

    def set(self, key: str, value):
        if not self._primary_alive:
            raise RuntimeError(f"Shard {self.shard_id}: primary is down")
        self._primary[key] = value
        self._pending_replication.append((key, value))
        self.stats["writes"] += 1

    def get(self, key: str):
        self.stats["reads"] += 1
        if self._primary_alive:
            return self._primary.get(key)
        if self._replica_alive:
            self.stats["replica_reads"] += 1
            return self._replica.get(key)
        return None

    def delete(self, key: str):
        if self._primary_alive:
            self._primary.pop(key, None)
            self._pending_replication.append((key, None))

    def replicate(self):
        """Flush pending writes to the replica (async replication sim)."""
        replicated = 0
        for key, value in self._pending_replication:
            if value is None:
                self._replica.pop(key, None)
            else:
                self._replica[key] = value
            replicated += 1
        self._pending_replication.clear()
        return replicated

    def kill_primary(self):
        self._primary_alive = False
        self._primary.clear()

    def promote_replica(self):
        if not self._replica_alive:
            raise RuntimeError(f"Shard {self.shard_id}: replica also down")
        self._primary = dict(self._replica)
        self._primary_alive = True
        self.stats["failovers"] += 1

    @property
    def primary_alive(self):
        return self._primary_alive

    @property
    def key_count(self):
        if self._primary_alive:
            return len(self._primary)
        return len(self._replica)


# ---------------------------------------------------------------------------
# Cluster - consistent hashing over shards
# ---------------------------------------------------------------------------

class CacheCluster:
    """Distributed cache cluster with consistent hashing and replication."""

    def __init__(self, num_shards: int = 4, vnodes: int = 150):
        self._shards = {}
        self._ring_positions = []
        self._position_to_shard = {}

        for i in range(num_shards):
            shard_id = f"shard-{i:02d}"
            self._shards[shard_id] = CacheShard(shard_id)
            for v in range(vnodes):
                h = self._hash(f"{shard_id}#vn{v}")
                self._position_to_shard[h] = shard_id
                bisect.insort(self._ring_positions, h)

    def _hash(self, key: str) -> int:
        return int(hashlib.md5(key.encode()).hexdigest(), 16)

    def _get_shard(self, key: str) -> CacheShard:
        h = self._hash(key)
        idx = bisect.bisect_right(self._ring_positions, h)
        if idx == len(self._ring_positions):
            idx = 0
        shard_id = self._position_to_shard[self._ring_positions[idx]]
        return self._shards[shard_id]

    def set(self, key: str, value):
        shard = self._get_shard(key)
        shard.set(key, value)

    def get(self, key: str):
        shard = self._get_shard(key)
        return shard.get(key)

    def delete(self, key: str):
        shard = self._get_shard(key)
        shard.delete(key)

    def replicate_all(self):
        total = 0
        for shard in self._shards.values():
            total += shard.replicate()
        return total

    def kill_shard_primary(self, shard_id: str):
        self._shards[shard_id].kill_primary()

    def failover_shard(self, shard_id: str):
        self._shards[shard_id].promote_replica()

    def print_status(self):
        print(f"\n  {'Shard':<12} {'Status':<12} {'Keys':>6} {'Reads':>6} "
              f"{'Writes':>6} {'Failovers':>10}")
        print(f"  {'-'*56}")
        for sid in sorted(self._shards):
            s = self._shards[sid]
            status = "PRIMARY" if s.primary_alive else "REPLICA"
            st = s.stats
            print(f"  {sid:<12} {status:<12} {s.key_count:>6} {st['reads']:>6} "
                  f"{st['writes']:>6} {st['failovers']:>10}")


# ---------------------------------------------------------------------------
# Demo: normal operations with replication
# ---------------------------------------------------------------------------

def demo_normal_operations():
    print("=" * 60)
    print("CACHE CLUSTER - Normal Operations with Replication")
    print("=" * 60)

    cluster = CacheCluster(num_shards=4)

    print("\n  Writing 1,000 keys to the cluster...")
    for i in range(1000):
        cluster.set(f"user:{i}", {"id": i, "name": f"User {i}", "active": True})

    print("  Replicating to replicas...")
    replicated = cluster.replicate_all()
    print(f"  Replicated {replicated} key-value pairs")

    hits = 0
    for i in range(1000):
        if cluster.get(f"user:{i}") is not None:
            hits += 1
    print(f"\n  Read verification: {hits}/1,000 keys retrieved successfully")

    cluster.print_status()


# ---------------------------------------------------------------------------
# Demo: primary failure and failover
# ---------------------------------------------------------------------------

def demo_failover():
    print("\n" + "=" * 60)
    print("FAILOVER - Primary Dies, Replica Takes Over")
    print("=" * 60)

    cluster = CacheCluster(num_shards=4)

    print("\n  Phase 1: Write 500 keys and replicate")
    for i in range(500):
        cluster.set(f"item:{i}", {"product_id": i, "price": round(random.uniform(1, 100), 2)})
    cluster.replicate_all()

    # Read all keys to verify
    readable_before = sum(1 for i in range(500) if cluster.get(f"item:{i}") is not None)
    print(f"  All keys readable: {readable_before}/500")

    print("\n  Phase 2: Write 100 MORE keys (not yet replicated)")
    for i in range(500, 600):
        cluster.set(f"item:{i}", {"product_id": i, "price": round(random.uniform(1, 100), 2)})
    print("  (replication not triggered - these exist only on primaries)")

    print("\n  Phase 3: Kill shard-01 primary")
    cluster.kill_shard_primary("shard-01")
    print("  shard-01 primary is DOWN")

    # Check what's readable now (shard-01 serves from replica)
    readable_after_kill = sum(1 for i in range(600) if cluster.get(f"item:{i}") is not None)
    lost = readable_before + 100 - readable_after_kill
    print(f"  Keys readable after failure: {readable_after_kill}/600")
    print(f"  Keys lost (unreplicated on shard-01): {lost}")

    print("\n  Phase 4: Promote shard-01 replica to primary")
    cluster.failover_shard("shard-01")

    readable_after_failover = sum(1 for i in range(600) if cluster.get(f"item:{i}") is not None)
    print(f"  Keys readable after failover: {readable_after_failover}/600")

    cluster.print_status()

    print(f"""
  Takeaway: Async replication means a small data loss window.
  The {lost} keys written after the last replication cycle were
  lost when the primary died. For a cache this is acceptable -
  clients just get misses and refetch from the database.
    """)


# ---------------------------------------------------------------------------
# Demo: replication lag
# ---------------------------------------------------------------------------

def demo_replication_lag():
    print("=" * 60)
    print("REPLICATION LAG - Writes Between Sync Cycles")
    print("=" * 60)

    cluster = CacheCluster(num_shards=3)
    batch_size = 200
    sync_interval_keys = 50

    print(f"\n  Writing {batch_size} keys, syncing every {sync_interval_keys} writes...")
    print(f"\n  {'Writes Done':>12} {'Pending':>10} {'Replicated':>12} {'Lag':>8}")
    print(f"  {'-'*44}")

    total_replicated = 0
    for i in range(batch_size):
        cluster.set(f"data:{i}", {"seq": i, "ts": time.time()})
        if (i + 1) % sync_interval_keys == 0:
            batch_rep = cluster.replicate_all()
            total_replicated += batch_rep
            pending = (i + 1) - total_replicated
            print(f"  {i+1:>12} {pending:>10} {total_replicated:>12} "
                  f"{pending:>7} keys")

    final_rep = cluster.replicate_all()
    total_replicated += final_rep
    print(f"\n  Final sync: replicated remaining {final_rep} keys")
    print(f"  Total replicated: {total_replicated}")
    print(f"\n  In production, replication lag is measured in milliseconds,")
    print(f"  not key counts. Redis replication lag is typically < 1ms")
    print(f"  within the same datacenter.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    demo_normal_operations()
    demo_failover()
    demo_replication_lag()


if __name__ == "__main__":
    main()
