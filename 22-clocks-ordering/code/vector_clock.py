"""
Vector Clock Simulation
=======================
Implements vector clocks for a distributed system. Demonstrates
concurrent event detection - something Lamport clocks can't do.

Run: python vector_clock.py
"""

from copy import deepcopy

# ---------------------------------------------------------------------------
# Vector clock implementation
# ---------------------------------------------------------------------------

class VectorClock:
    def __init__(self, process_ids: list, owner: str):
        self.clock = {pid: 0 for pid in process_ids}
        self.owner = owner

    def tick(self):
        self.clock[self.owner] += 1

    def send(self) -> dict:
        self.tick()
        return deepcopy(self.clock)

    def receive(self, incoming: dict):
        for pid in self.clock:
            self.clock[pid] = max(self.clock[pid], incoming.get(pid, 0))
        self.tick()

    def snapshot(self) -> dict:
        return deepcopy(self.clock)

    @staticmethod
    def compare(vc_a: dict, vc_b: dict) -> str:
        a_leq_b = all(vc_a[k] <= vc_b[k] for k in vc_a)
        b_leq_a = all(vc_b[k] <= vc_a[k] for k in vc_a)
        equal = all(vc_a[k] == vc_b[k] for k in vc_a)

        if equal:
            return "EQUAL"
        elif a_leq_b:
            return "A -> B (A happened before B)"
        elif b_leq_a:
            return "B -> A (B happened before A)"
        else:
            return "CONCURRENT (no causal relationship)"

    def __repr__(self):
        entries = ", ".join(f"{k}:{v}" for k, v in self.clock.items())
        return f"[{entries}]"


# ---------------------------------------------------------------------------
# Process node with vector clock
# ---------------------------------------------------------------------------

class Node:
    def __init__(self, pid: str, all_pids: list):
        self.pid = pid
        self.vc = VectorClock(all_pids, pid)
        self.history = []

    def local_event(self, desc: str) -> dict:
        self.vc.tick()
        snap = self.vc.snapshot()
        self.history.append({"desc": desc, "vc": snap})
        return snap

    def send_to(self, target: "Node", msg: str) -> tuple[dict, dict]:
        outgoing = self.vc.send()
        self.history.append({"desc": f"send '{msg}' -> {target.pid}", "vc": deepcopy(self.vc.clock)})

        target.vc.receive(outgoing)
        recv_snap = target.vc.snapshot()
        target.history.append({"desc": f"recv '{msg}' <- {self.pid}", "vc": recv_snap})

        return deepcopy(self.vc.clock), recv_snap


# ---------------------------------------------------------------------------
# Demo 1: Causal ordering with messages
# ---------------------------------------------------------------------------

def demo_causal_ordering():
    print("=" * 65)
    print("DEMO 1: Vector Clocks Track Causality")
    print("=" * 65)

    pids = ["A", "B", "C"]
    a, b, c = Node("A", pids), Node("B", pids), Node("C", pids)

    e1 = a.local_event("client request arrives")
    e2 = a.local_event("validate input")
    a.send_to(b, "process-order")
    e3 = b.local_event("check inventory")
    b.send_to(c, "reserve-stock")
    e4 = c.local_event("stock reserved")
    c.send_to(a, "confirmation")
    e5 = a.local_event("respond to client")

    for node in [a, b, c]:
        print(f"\n  {node.pid}'s event log:")
        for entry in node.history:
            vc_str = ", ".join(f"{k}:{v}" for k, v in entry["vc"].items())
            print(f"    [{vc_str}]  {entry['desc']}")

    print(f"\n  Comparing events:")
    print(f"    'validate input' vs 'stock reserved':")
    print(f"      {VectorClock.compare(e2, e4)}")
    print(f"    'validate input' vs 'respond to client':")
    print(f"      {VectorClock.compare(e2, e5)}")


# ---------------------------------------------------------------------------
# Demo 2: Detecting concurrent writes (the main event)
# ---------------------------------------------------------------------------

def demo_concurrent_detection():
    print(f"\n{'=' * 65}")
    print("DEMO 2: Detecting Concurrent Writes")
    print("=" * 65)
    print("Two clients write to the same key on different replicas")
    print("without communicating. Vector clocks catch the conflict.\n")

    pids = ["R1", "R2", "R3"]
    r1, r2, r3 = Node("R1", pids), Node("R2", pids), Node("R3", pids)

    print("Step 1: Initial write goes through R1, propagated to all")
    r1.local_event("write user.email = 'old@test.com'")
    r1.send_to(r2, "sync user.email")
    r1.send_to(r3, "sync user.email")

    state_after_sync = {
        "R1": deepcopy(r1.vc.clock),
        "R2": deepcopy(r2.vc.clock),
        "R3": deepcopy(r3.vc.clock),
    }

    print(f"  After sync: R1={r1.vc}, R2={r2.vc}, R3={r3.vc}")

    print("\nStep 2: Two clients write CONCURRENTLY to different replicas")
    write_a = r1.local_event("Client-A writes user.email = 'alice@new.com'")
    write_b = r2.local_event("Client-B writes user.email = 'bob@new.com'")

    print(f"  Client-A on R1: {write_a}")
    print(f"  Client-B on R2: {write_b}")

    result = VectorClock.compare(write_a, write_b)
    print(f"\n  Comparison: {result}")

    print("\nStep 3: When replicas sync, they detect the conflict")
    print(f"  R1 has user.email = 'alice@new.com' at {write_a}")
    print(f"  R2 has user.email = 'bob@new.com'   at {write_b}")
    print(f"  Neither dominates - system must resolve the conflict.")
    print(f"\n  Resolution strategies:")
    print(f"    1. Last-writer-wins (pick one, lose the other)")
    print(f"    2. Return both to client (Amazon's shopping cart approach)")
    print(f"    3. Application-level merge (CRDTs, custom logic)")


# ---------------------------------------------------------------------------
# Demo 3: Vector clock size problem
# ---------------------------------------------------------------------------

def demo_scalability():
    print(f"\n{'=' * 65}")
    print("DEMO 3: Vector Clock Scalability Problem")
    print("=" * 65)
    print()

    sizes = [3, 10, 50, 100, 500, 1000]

    print(f"{'Nodes':<10} {'VC Size (ints)':<18} {'Bytes (32-bit)':<18} {'Per-message overhead'}")
    print("-" * 70)

    for n in sizes:
        bytes_32 = n * 4
        if bytes_32 < 1024:
            overhead = f"{bytes_32} B"
        else:
            overhead = f"{bytes_32/1024:.1f} KB"
        print(f"{n:<10} {n:<18} {bytes_32:<18} {overhead}")

    print(f"\nAt 1000 nodes with 10,000 messages/sec:")
    print(f"  Overhead: ~4 KB per message = ~40 MB/sec just for clocks.")
    print(f"  This is why large systems use HLCs instead of vector clocks.")


# ---------------------------------------------------------------------------
# Run all demos
# ---------------------------------------------------------------------------

def main():
    print("Vector Clocks - Detecting Concurrency in Distributed Systems\n")
    demo_causal_ordering()
    demo_concurrent_detection()
    demo_scalability()


if __name__ == "__main__":
    main()
