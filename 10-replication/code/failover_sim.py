"""
Failover Simulation
===================
Simulates leader failure detection, follower promotion, and the
split-brain problem. Demonstrates fencing tokens as a defense.
"""

import time

# ---------------------------------------------------------------------------
#   Cluster node
# ---------------------------------------------------------------------------

class Node:
    """A database node that can be leader or follower."""

    def __init__(self, name):
        self.name = name
        self.role = "follower"
        self.alive = True
        self.data = {}
        self.replication_position = 0
        self.fencing_token = 0

    def write(self, key, value, token=None):
        if not self.alive:
            print(f"  [{self.name}] WRITE REJECTED - node is down")
            return False
        if self.role != "leader":
            print(f"  [{self.name}] WRITE REJECTED - not the leader")
            return False
        if token is not None and token < self.fencing_token:
            print(f"  [{self.name}] WRITE REJECTED - stale token "
                  f"({token} < {self.fencing_token})")
            return False
        self.data[key] = value
        self.replication_position += 1
        print(f"  [{self.name}] WRITE {key}={value} "
              f"(pos={self.replication_position})")
        return True

    def replicate_from(self, leader):
        for k, v in leader.data.items():
            if k not in self.data:
                self.data[k] = v
                self.replication_position += 1

    def promote(self, token):
        self.role = "leader"
        self.fencing_token = token
        print(f"  [{self.name}] PROMOTED to leader (token={token})")

    def crash(self):
        self.alive = False
        print(f"  [{self.name}] *** CRASHED ***")


# ---------------------------------------------------------------------------
#   Health monitor
# ---------------------------------------------------------------------------

class HealthMonitor:
    """Detects leader failure via heartbeats and triggers election."""

    def __init__(self, heartbeat_interval=0.2, threshold=3):
        self.interval = heartbeat_interval
        self.threshold = threshold
        self.current_token = 0

    def check_leader(self, leader):
        missed = 0
        print(f"\n  [monitor] Watching {leader.name} "
              f"(threshold={self.threshold} misses)")
        for i in range(self.threshold + 1):
            time.sleep(self.interval)
            if leader.alive:
                print(f"  [monitor] heartbeat {i+1}: OK")
                missed = 0
            else:
                missed += 1
                print(f"  [monitor] heartbeat {i+1}: NO RESPONSE "
                      f"(missed={missed})")
            if missed >= self.threshold:
                print(f"  [monitor] FAILURE DETECTED")
                return False
        return True

    def elect(self, candidates):
        eligible = [n for n in candidates if n.alive]
        if not eligible:
            print("  [monitor] No candidates available!")
            return None
        best = max(eligible, key=lambda n: n.replication_position)
        self.current_token += 1
        best.promote(self.current_token)
        return best


# ---------------------------------------------------------------------------
#   Demo: basic failover
# ---------------------------------------------------------------------------

def demo_basic_failover():
    print("=" * 65)
    print("BASIC FAILOVER")
    print("=" * 65)

    leader = Node("node-A")
    leader.promote(token=1)
    f1, f2 = Node("node-B"), Node("node-C")

    leader.write("order:1", "placed")
    leader.write("order:2", "shipped")
    f1.replicate_from(leader)
    f2.replicate_from(leader)
    leader.write("order:3", "delivered")
    f1.replicate_from(leader)

    print(f"\n  Replication positions: A={leader.replication_position}, "
          f"B={f1.replication_position}, C={f2.replication_position}")

    leader.crash()
    monitor = HealthMonitor(heartbeat_interval=0.15, threshold=3)
    monitor.current_token = 1
    if not monitor.check_leader(leader):
        new = monitor.elect([f1, f2])
        print(f"  New leader: {new.name} (pos={new.replication_position})")
        new.write("order:4", "post-failover")
    print()


# ---------------------------------------------------------------------------
#   Demo: split-brain and fencing tokens
# ---------------------------------------------------------------------------

def demo_split_brain():
    print("=" * 65)
    print("SPLIT-BRAIN + FENCING TOKENS")
    print("=" * 65)
    print("  Old leader comes back after a new leader was elected.\n")

    old = Node("node-A")
    old.promote(token=1)
    old.write("balance", "1000")

    new = Node("node-B")
    new.promote(token=2)

    print(f"\n  Two leaders! A(token=1) and B(token=2)")
    print(f"\n  Without fencing - both accept writes:")
    old.write("balance", "900")
    new.write("balance", "1100")
    print(f"  DATA DIVERGED: A={old.data['balance']}, "
          f"B={new.data['balance']}")

    print(f"\n  With fencing - storage rejects stale tokens:")
    storage = Node("storage")
    storage.promote(token=1)
    storage.fencing_token = 2
    storage.write("balance", "900", token=1)
    storage.write("balance", "1100", token=2)
    print(f"  Final: {storage.data.get('balance')} (correct)\n")


# ---------------------------------------------------------------------------
#   Demo: failover timeline
# ---------------------------------------------------------------------------

def demo_timeline():
    print("=" * 65)
    print("FAILOVER TIMELINE")
    print("=" * 65)
    t0 = time.time()
    elapsed = lambda: f"{time.time() - t0:.2f}s"

    leader = Node("primary")
    leader.promote(token=1)
    f1, f2 = Node("secondary-1"), Node("secondary-2")

    print(f"\n  [{elapsed()}] Normal operation")
    leader.write("k1", "v1")
    f1.replicate_from(leader)
    f2.replicate_from(leader)

    print(f"  [{elapsed()}] Leader crashes")
    leader.crash()

    monitor = HealthMonitor(heartbeat_interval=0.15, threshold=3)
    monitor.current_token = 1
    if not monitor.check_leader(leader):
        print(f"  [{elapsed()}] Electing new leader")
        new = monitor.elect([f1, f2])
        new.write("k2", "v2")
        total = time.time() - t0
        print(f"\n  Total failover time: {total:.2f}s")
        print(f"  Detection: ~{monitor.threshold * monitor.interval:.2f}s")
    print()


# ---------------------------------------------------------------------------
#   Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    demo_basic_failover()
    demo_split_brain()
    demo_timeline()
    print("Done. Automatic failover is fast but risks split-brain.")
    print("Fencing tokens are the standard defense.")
