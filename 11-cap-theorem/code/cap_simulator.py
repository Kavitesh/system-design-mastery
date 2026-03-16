"""
CAP Theorem Simulator
=====================
Simulates a 3-node cluster under CP and AP modes. Triggers a
network partition and shows how each approach handles reads and
writes when nodes can't communicate.

Run: python cap_simulator.py
"""

import time

# ---------------------------------------------------------------------------
#  Node and Cluster
# ---------------------------------------------------------------------------

class Node:
    def __init__(self, nid):
        self.nid = nid
        self.data = {}
        self.peers = set()

    def write(self, key, val, ts):
        cur = self.data.get(key)
        if cur is None or ts > cur[1]:
            self.data[key] = (val, ts)
            return True
        return False

    def read(self, key):
        e = self.data.get(key)
        return e[0] if e else None


class Cluster:
    def __init__(self, n=3):
        self.nodes = [Node(i) for i in range(n)]
        self.heal()

    def partition(self, a_ids, b_ids):
        for a in a_ids:
            self.nodes[a].peers -= set(b_ids)
        for b in b_ids:
            self.nodes[b].peers -= set(a_ids)

    def heal(self):
        for n in self.nodes:
            n.peers = {p.nid for p in self.nodes if p != n}

    def sync(self):
        for src in self.nodes:
            for pid in list(src.peers):
                for k, (v, t) in list(src.data.items()):
                    self.nodes[pid].write(k, v, t)

# ---------------------------------------------------------------------------
#  CP operations - require majority quorum
# ---------------------------------------------------------------------------

def cp_write(c, key, val):
    ts, coord = time.time(), c.nodes[0]
    acks = int(coord.write(key, val, ts))
    for pid in coord.peers:
        acks += int(c.nodes[pid].write(key, val, ts))
    majority = len(c.nodes) // 2 + 1
    if acks < majority:
        coord.data.pop(key, None)
    return acks >= majority, acks

def cp_read(c, key):
    coord = c.nodes[0]
    reachable = 1 + len(coord.peers)
    if reachable < len(c.nodes) // 2 + 1:
        return None, False
    return coord.read(key), True

# ---------------------------------------------------------------------------
#  AP operations - always accept, replicate where possible
# ---------------------------------------------------------------------------

def ap_write(c, nid, key, val):
    ts, node = time.time(), c.nodes[nid]
    node.write(key, val, ts)
    for pid in node.peers:
        c.nodes[pid].write(key, val, ts)

def ap_read(c, nid, key):
    return c.nodes[nid].read(key)

# ---------------------------------------------------------------------------
#  Simulation
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  CAP THEOREM SIMULATOR")
    print("=" * 60)

    print("\n--- CP SYSTEM (like ZooKeeper / etcd) ---\n")
    cl = Cluster(3)
    ok, n = cp_write(cl, "balance", "100")
    print(f"  Write balance=100  -> success={ok}, acks={n}/3")
    v, a = cp_read(cl, "balance")
    print(f"  Read  balance      -> value={v}, available={a}")

    print(f"\n  >>> Partition: Node 0 isolated from Nodes 1,2")
    cl.partition([0], [1, 2])
    ok, n = cp_write(cl, "balance", "200")
    print(f"  Write balance=200  -> success={ok}, acks={n}/3  (NO QUORUM)")
    v, a = cp_read(cl, "balance")
    print(f"  Read  balance      -> value={v}, available={a}")

    print(f"\n  >>> Heal partition")
    cl.heal(); cl.sync()
    ok, n = cp_write(cl, "balance", "200")
    print(f"  Write balance=200  -> success={ok}, acks={n}/3")

    print("\n" + "-" * 60)
    print("\n--- AP SYSTEM (like Cassandra / DynamoDB) ---\n")
    cl = Cluster(3)
    ap_write(cl, 0, "cart", "item_A")
    vals = [cl.nodes[i].read("cart") for i in range(3)]
    print(f"  Write cart=item_A  -> all nodes: {vals}")

    print(f"\n  >>> Partition: Node 0 isolated from Nodes 1,2")
    cl.partition([0], [1, 2])
    ap_write(cl, 0, "cart", "item_B")
    ap_write(cl, 1, "cart", "item_C")
    vals = [cl.nodes[i].read("cart") for i in range(3)]
    print(f"  Concurrent writes  -> all nodes: {vals}")
    print(f"  Nodes disagree, but every read succeeded (AVAILABLE)")

    print(f"\n  >>> Heal partition + anti-entropy sync")
    cl.heal(); cl.sync()
    vals = [cl.nodes[i].read("cart") for i in range(3)]
    print(f"  After healing      -> all nodes: {vals}  (LWW resolved)")

    print("\n" + "=" * 60)
    print("  CP: rejects ops during partition (no stale data)")
    print("  AP: accepts ops during partition (may serve stale data)")
    print("  Both converge after partition heals.")
    print("=" * 60)


if __name__ == "__main__":
    main()
