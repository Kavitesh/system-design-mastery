"""
Consistency Models Demo
=======================
Side-by-side comparison of strong, eventual, causal, and
read-your-writes consistency. Runs the same writes through
each model and shows how reads behave differently.

Run: python consistency_models.py
"""

import time

# ---------------------------------------------------------------------------
#  Replica node
# ---------------------------------------------------------------------------

class Replica:
    def __init__(self, name):
        self.name = name
        self.store = {}

    def write(self, key, val, ts):
        cur = self.store.get(key)
        if cur is None or ts > cur[1]:
            self.store[key] = (val, ts)

    def read(self, key):
        e = self.store.get(key)
        return e[0] if e else None

# ---------------------------------------------------------------------------
#  Strong consistency - sync replication to all before returning
# ---------------------------------------------------------------------------

def demo_strong():
    nodes = [Replica("A"), Replica("B"), Replica("C")]
    print("--- STRONG CONSISTENCY ---")
    print("  Writes block until ALL replicas confirm.\n")
    ts = time.time()
    for n in nodes:
        n.write("status", "confirmed", ts)
    print("  SET status='confirmed' -> replicated to all 3 nodes")
    for n in nodes:
        print(f"  {n.name} reads: '{n.read('status')}'")
    print("  Every node returns the latest write.\n")

# ---------------------------------------------------------------------------
#  Eventual consistency - async replication with visible lag
# ---------------------------------------------------------------------------

def demo_eventual():
    nodes = [Replica("A"), Replica("B"), Replica("C")]
    print("--- EVENTUAL CONSISTENCY ---")
    print("  Write returns after local commit. Replication is async.\n")
    ts = time.time()
    nodes[0].write("status", "shipped", ts)
    print("  SET status='shipped' on Node A only")
    print("  Before replication:")
    for n in nodes:
        print(f"    {n.name}: '{n.read('status')}'")
    for n in nodes[1:]:
        n.write("status", "shipped", ts)
    print("  After replication:")
    for n in nodes:
        print(f"    {n.name}: '{n.read('status')}'")
    print("  Stale reads occurred, then all nodes converged.\n")

# ---------------------------------------------------------------------------
#  Causal consistency - causally related ops seen in order
# ---------------------------------------------------------------------------

def demo_causal():
    nodes = [Replica("A"), Replica("B"), Replica("C")]
    print("--- CAUSAL CONSISTENCY ---")
    print("  Causally related ops appear in order everywhere.")
    print("  Concurrent ops may appear in any order.\n")
    ts = time.time()
    nodes[0].write("photo", "beach.jpg", ts)
    nodes[0].write("comment", "Great day!", ts + 0.001)
    nodes[2].write("like", "post_99", ts + 0.002)
    print("  Alice@A: POST photo, then COMMENT (causal chain)")
    print("  Bob@C:   LIKE post_99 (independent)\n")
    print("  Replicating with causal order enforced...")
    for n in nodes[1:]:
        n.write("photo", "beach.jpg", ts)
        n.write("comment", "Great day!", ts + 0.001)
    for n in [nodes[0], nodes[1]]:
        n.write("like", "post_99", ts + 0.002)
    for n in nodes:
        print(f"  {n.name}: photo={n.read('photo')}, "
              f"comment={n.read('comment')}, like={n.read('like')}")
    print("  No node sees comment without photo (causal guarantee).\n")

# ---------------------------------------------------------------------------
#  Read-your-writes consistency
# ---------------------------------------------------------------------------

def demo_read_your_writes():
    nodes = [Replica("A"), Replica("B"), Replica("C")]
    print("--- READ-YOUR-WRITES ---")
    print("  You always see your own writes immediately.\n")
    ts = time.time()
    nodes[0].write("profile", "alice_2024", ts)
    print(f"  Alice writes profile='alice_2024' on Node A")
    print(f"  Alice reads A: '{nodes[0].read('profile')}' (sees own write)")
    print(f"  Bob   reads B: '{nodes[1].read('profile')}' (not replicated)")
    print("  Alice always gets her data; Bob may see stale.\n")

# ---------------------------------------------------------------------------
#  Monotonic reads consistency
# ---------------------------------------------------------------------------

def demo_monotonic():
    nodes = [Replica("A"), Replica("B"), Replica("C")]
    print("--- MONOTONIC READS ---")
    print("  Once you see version N, you never see version < N.\n")
    ts = time.time()
    for n in nodes:
        n.write("counter", "10", ts)
    nodes[0].write("counter", "15", ts + 0.01)
    nodes[1].write("counter", "15", ts + 0.01)
    print("  All nodes at 10. Nodes A,B updated to 15.")
    print(f"  Read A: {nodes[0].read('counter')}")
    print(f"  Read C: {nodes[2].read('counter')} (STALE - went backwards!)")
    print(f"  Read B: {nodes[1].read('counter')} (monotonic read routes here)")
    print("  System prevents time-travel by tracking read versions.\n")

# ---------------------------------------------------------------------------
#  Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  CONSISTENCY MODELS DEMO")
    print("=" * 60 + "\n")

    for demo in [demo_strong, demo_eventual, demo_causal,
                 demo_read_your_writes, demo_monotonic]:
        demo()
        print("-" * 60)

    print("\n  Model               Guarantee                     Cost")
    print("  -----               ---------                     ----")
    print("  Strong              Latest write, always          Sync replication latency")
    print("  Eventual            Converges over time           Stale reads possible")
    print("  Causal              Respects happens-before       Track causal deps")
    print("  Read-Your-Writes    See your own writes           Session affinity")
    print("  Monotonic Reads     Never go backwards            Track read versions\n")


if __name__ == "__main__":
    main()
