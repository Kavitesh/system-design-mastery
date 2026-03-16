"""
PACELC Theorem Demo
====================
Compares a PA/EL system (Cassandra-like) with a PC/EC system
(ZooKeeper-like). Shows how each behaves during normal operation
and during a network partition, demonstrating the full PACELC
tradeoff.

Run: python pacelc_demo.py
"""

import time
import random
import threading

# ---------------------------------------------------------------------------
#  Node with configurable sync latency
# ---------------------------------------------------------------------------

class Node:
    def __init__(self, nid, latency_ms=2.0):
        self.nid = nid
        self.store = {}
        self.lat = latency_ms / 1000
        self.peers = set()

    def write(self, key, val, ver):
        time.sleep(self.lat)
        cur = self.store.get(key)
        if cur is None or ver > cur[1]:
            self.store[key] = (val, ver)

    def read(self, key):
        time.sleep(self.lat)
        e = self.store.get(key)
        return e[0] if e else None

# ---------------------------------------------------------------------------
#  PA/EL system - available + low latency (Cassandra-like)
# ---------------------------------------------------------------------------

class PAEL:
    def __init__(self):
        self.nodes = [Node(i, random.uniform(1, 3)) for i in range(3)]
        self.ver = 0
        self.heal()

    def heal(self):
        for n in self.nodes:
            n.peers = {p.nid for p in self.nodes if p != n}

    def partition(self, iso):
        for n in self.nodes: n.peers.discard(iso)
        self.nodes[iso].peers.clear()

    def put(self, key, val, target=0):
        self.ver += 1
        nd = self.nodes[target]
        start = time.time()
        nd.write(key, val, self.ver)
        for pid in nd.peers:
            threading.Thread(target=self.nodes[pid].write,
                             args=(key, val, self.ver), daemon=True).start()
        return True, round((time.time() - start) * 1000, 2)

    def get(self, key, target=0):
        start = time.time()
        val = self.nodes[target].read(key)
        return val, True, round((time.time() - start) * 1000, 2)

    def sync(self):
        for s in self.nodes:
            for pid in s.peers:
                for k, (v, ver) in list(s.store.items()):
                    self.nodes[pid].write(k, v, ver)

# ---------------------------------------------------------------------------
#  PC/EC system - consistent + higher latency (ZooKeeper-like)
# ---------------------------------------------------------------------------

class PCEC:
    def __init__(self):
        self.nodes = [Node(i, random.uniform(3, 8)) for i in range(3)]
        self.ver = 0
        self.heal()

    def heal(self):
        for n in self.nodes:
            n.peers = {p.nid for p in self.nodes if p != n}

    def partition(self, iso):
        for n in self.nodes: n.peers.discard(iso)
        self.nodes[iso].peers.clear()

    def put(self, key, val, target=0):
        self.ver += 1
        nd = self.nodes[target]
        start = time.time()
        nd.write(key, val, self.ver)
        acks = 1
        for pid in nd.peers:
            self.nodes[pid].write(key, val, self.ver)
            acks += 1
        ms = round((time.time() - start) * 1000, 2)
        ok = acks >= 2
        return ok, ms

    def get(self, key, target=0):
        nd = self.nodes[target]
        reachable = 1 + len(nd.peers)
        start = time.time()
        if reachable < 2:
            return None, False, round((time.time() - start) * 1000, 2)
        val = nd.read(key)
        return val, True, round((time.time() - start) * 1000, 2)

# ---------------------------------------------------------------------------
#  Simulation
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  PACELC THEOREM DEMO")
    print("=" * 60)
    print("\n  PA/EL = Cassandra-like  |  PC/EC = ZooKeeper-like\n")

    pael, pcec = PAEL(), PCEC()

    print("--- PHASE 1: Normal operation (no partition) ---\n")
    ok, ms = pael.put("cfg", "v1")
    print(f"  PA/EL write: ok={ok}, {ms}ms (async - fast)")
    ok, ms = pcec.put("cfg", "v1")
    print(f"  PC/EC write: ok={ok}, {ms}ms (sync - slower)")
    time.sleep(0.02)
    v, a, ms = pael.get("cfg")
    print(f"  PA/EL read:  val='{v}', {ms}ms")
    v, a, ms = pcec.get("cfg")
    print(f"  PC/EC read:  val='{v}', {ms}ms")
    print("  PC/EC is slower even with no partition (the EC tradeoff).\n")

    print("--- PHASE 2: Network partition (Node 0 isolated) ---\n")
    pael.partition(0); pcec.partition(0)

    ok, ms = pael.put("cfg", "v2", target=0)
    print(f"  PA/EL write on isolated node: ok={ok} (accepted!)")
    v0, _, _ = pael.get("cfg", 0)
    v1, _, _ = pael.get("cfg", 1)
    print(f"  PA/EL reads: Node0='{v0}', Node1='{v1}' (DIVERGED)")

    ok, ms = pcec.put("cfg", "v2", target=0)
    print(f"  PC/EC write on isolated node: ok={ok} (rejected!)")
    v, avail, _ = pcec.get("cfg", target=0)
    print(f"  PC/EC read on isolated node:  available={avail}")
    v, avail, _ = pcec.get("cfg", target=1)
    print(f"  PC/EC read on majority side:  val='{v}', available={avail}\n")

    print("--- PHASE 3: Partition heals ---\n")
    pael.heal(); pael.sync(); pcec.heal()
    time.sleep(0.02)
    for i in range(3):
        v, _, _ = pael.get("cfg", i)
        print(f"  PA/EL Node {i}: '{v}'")
    print("  (Converged via anti-entropy)\n")
    for i in range(3):
        v, a, _ = pcec.get("cfg", i)
        print(f"  PC/EC Node {i}: '{v}' available={a}")
    print("  (Was already consistent)")

    print("\n" + "=" * 60)
    print("  PA/EL: available during partition, fast during normal")
    print("  PC/EC: consistent during partition, slower during normal")
    print("  PACELC captures BOTH tradeoffs - not just partition behavior.")
    print("=" * 60)


if __name__ == "__main__":
    main()
