"""
Leader-Follower Replication Simulator
=====================================
Simulates a leader node replicating writes to followers in both synchronous
and asynchronous modes. Demonstrates replication lag and stale reads.
"""

import time
import threading
import random

# ---------------------------------------------------------------------------
#   Node classes
# ---------------------------------------------------------------------------

class LeaderNode:
    """Accepts writes and replicates them to follower nodes."""

    def __init__(self, name, followers, mode="async"):
        self.name = name
        self.data = {}
        self.followers = followers
        self.mode = mode
        self.log = []

    def write(self, key, value):
        timestamp = time.time()
        entry = {"key": key, "value": value, "ts": timestamp}
        self.data[key] = value
        self.log.append(entry)
        print(f"  [{self.name}] WRITE {key}={value}")

        if self.mode == "sync":
            self._replicate_sync(entry)
        else:
            self._replicate_async(entry)

        return entry

    def _replicate_sync(self, entry):
        for follower in self.followers:
            follower.apply(entry)
            print(f"  [{self.name}] sync ACK from {follower.name}")

    def _replicate_async(self, entry):
        for follower in self.followers:
            delay = random.uniform(0.1, 0.5)
            t = threading.Thread(target=follower.apply, args=(entry, delay))
            t.daemon = True
            t.start()


class FollowerNode:
    """Receives replicated writes and serves reads."""

    def __init__(self, name):
        self.name = name
        self.data = {}
        self.applied_count = 0

    def apply(self, entry, delay=0):
        if delay > 0:
            time.sleep(delay)
        self.data[entry["key"]] = entry["value"]
        self.applied_count += 1
        print(f"  [{self.name}] APPLIED {entry['key']}={entry['value']}"
              f" (delay={delay:.2f}s)")

    def read(self, key):
        value = self.data.get(key, None)
        status = "FOUND" if value is not None else "NOT FOUND (stale!)"
        print(f"  [{self.name}] READ {key} -> {value} [{status}]")
        return value


# ---------------------------------------------------------------------------
#   Demo: synchronous replication
# ---------------------------------------------------------------------------

def demo_sync():
    print("=" * 65)
    print("SYNCHRONOUS REPLICATION")
    print("=" * 65)
    print("Leader waits for all followers before confirming the write.\n")

    f1 = FollowerNode("follower-1")
    f2 = FollowerNode("follower-2")
    leader = LeaderNode("leader", [f1, f2], mode="sync")

    start = time.time()
    leader.write("user:1", "Alice")
    leader.write("user:2", "Bob")
    elapsed = time.time() - start

    print(f"\n  Write latency: {elapsed:.3f}s (blocked on all replicas)")
    print(f"  Follower-1 read: {f1.read('user:2')}")
    print(f"  Follower-2 read: {f2.read('user:2')}")
    print("  Result: both followers are guaranteed up-to-date.\n")


# ---------------------------------------------------------------------------
#   Demo: asynchronous replication
# ---------------------------------------------------------------------------

def demo_async():
    print("=" * 65)
    print("ASYNCHRONOUS REPLICATION")
    print("=" * 65)
    print("Leader returns immediately. Followers catch up later.\n")

    f1 = FollowerNode("follower-1")
    f2 = FollowerNode("follower-2")
    leader = LeaderNode("leader", [f1, f2], mode="async")

    start = time.time()
    leader.write("user:1", "Alice")
    leader.write("user:2", "Bob")
    elapsed = time.time() - start

    print(f"\n  Write latency: {elapsed:.3f}s (didn't wait for replicas)")
    print("\n  Reading from follower IMMEDIATELY after write:")
    f1.read("user:2")

    print("\n  Waiting 1 second for replication to catch up...")
    time.sleep(1.0)

    print("\n  Reading from follower AFTER replication lag:")
    f1.read("user:2")
    f2.read("user:2")
    print("  Result: followers eventually catch up, but reads can be stale.\n")


# ---------------------------------------------------------------------------
#   Demo: read-after-write consistency
# ---------------------------------------------------------------------------

def demo_read_after_write():
    print("=" * 65)
    print("READ-AFTER-WRITE CONSISTENCY")
    print("=" * 65)
    print("Route the writing user's reads to the leader.\n")

    f1 = FollowerNode("follower-1")
    leader = LeaderNode("leader", [f1], mode="async")

    leader.write("comment:99", "Great post!")

    print("\n  Strategy: read from leader for the user who just wrote")
    value = leader.data.get("comment:99")
    print(f"  [leader] READ comment:99 -> {value} [CONSISTENT]")

    print("  Other users can still read from followers (may be stale).")
    f1.read("comment:99")
    time.sleep(0.6)
    print("\n  After replication catches up:")
    f1.read("comment:99")
    print()


# ---------------------------------------------------------------------------
#   Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    demo_sync()
    demo_async()
    demo_read_after_write()
    print("Done. Compare write latencies and read consistency across modes.")
