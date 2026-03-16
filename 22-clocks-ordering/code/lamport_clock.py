"""
Lamport Clock Simulation
========================
Simulates multiple processes exchanging messages using Lamport
logical clocks. Demonstrates total ordering and the happens-before
relationship.

Run: python lamport_clock.py
"""

import random

# ---------------------------------------------------------------------------
# Lamport clock implementation
# ---------------------------------------------------------------------------

class LamportClock:
    def __init__(self):
        self.time = 0

    def tick(self) -> int:
        self.time += 1
        return self.time

    def send(self) -> int:
        self.time += 1
        return self.time

    def receive(self, msg_time: int) -> int:
        self.time = max(self.time, msg_time) + 1
        return self.time


# ---------------------------------------------------------------------------
# Process with Lamport clock
# ---------------------------------------------------------------------------

class Process:
    def __init__(self, pid: str):
        self.pid = pid
        self.clock = LamportClock()
        self.log = []

    def local_event(self, description: str):
        ts = self.clock.tick()
        event = {"ts": ts, "pid": self.pid, "type": "local", "desc": description}
        self.log.append(event)
        return event

    def send_message(self, target: "Process", content: str):
        ts = self.clock.send()
        event = {"ts": ts, "pid": self.pid, "type": "send", "desc": f"send '{content}' to {target.pid}"}
        self.log.append(event)

        recv_event = target.receive_message(self, ts, content)
        return event, recv_event

    def receive_message(self, sender: "Process", msg_ts: int, content: str):
        ts = self.clock.receive(msg_ts)
        event = {"ts": ts, "pid": self.pid, "type": "recv", "desc": f"recv '{content}' from {sender.pid}"}
        self.log.append(event)
        return event


# ---------------------------------------------------------------------------
# Simulation - three processes exchanging messages
# ---------------------------------------------------------------------------

def run_simulation():
    print("=" * 65)
    print("LAMPORT CLOCK SIMULATION")
    print("=" * 65)
    print("Three processes performing local events and exchanging messages.\n")

    p1 = Process("P1")
    p2 = Process("P2")
    p3 = Process("P3")

    p1.local_event("read from disk")
    p2.local_event("initialize cache")
    p1.local_event("process request")
    p1.send_message(p2, "update-key-X")
    p2.local_event("write to cache")
    p2.send_message(p3, "invalidate-key-X")
    p3.local_event("clear local cache")
    p3.send_message(p1, "ack-invalidation")
    p1.local_event("confirm sync")
    p2.local_event("log completion")
    p3.local_event("resume serving")

    all_events = p1.log + p2.log + p3.log

    print("Event Timeline:")
    print(f"{'Process':<6} {'Clock':>5}  {'Type':<6}  {'Description'}")
    print("-" * 65)

    for proc in [p1, p2, p3]:
        for e in proc.log:
            marker = "->" if e["type"] == "send" else ("<-" if e["type"] == "recv" else "  ")
            print(f"{e['pid']:<6} {e['ts']:>5}  {marker} {e['type']:<4}  {e['desc']}")
        print()

    return all_events


# ---------------------------------------------------------------------------
# Demonstrate total ordering
# ---------------------------------------------------------------------------

def demo_total_ordering(events: list):
    print("=" * 65)
    print("TOTAL ORDER (sorted by Lamport timestamp, then process ID)")
    print("=" * 65)
    print()

    sorted_events = sorted(events, key=lambda e: (e["ts"], e["pid"]))

    print(f"{'Rank':<6} {'(ts, pid)':<12} {'Description'}")
    print("-" * 65)
    for i, e in enumerate(sorted_events, 1):
        print(f"{i:<6} ({e['ts']}, {e['pid']})     {e['desc']}")

    print(f"\nTotal order established: {len(sorted_events)} events, fully sorted.")
    print("Every node using this algorithm produces the SAME total order.")


# ---------------------------------------------------------------------------
# Show the limitation - can't detect concurrency
# ---------------------------------------------------------------------------

def demo_concurrency_limitation():
    print(f"\n{'=' * 65}")
    print("LIMITATION: Lamport Clocks Can't Detect Concurrency")
    print("=" * 65)
    print()

    a = Process("A")
    b = Process("B")

    e1 = a.local_event("write X=1")
    e2 = a.local_event("write X=2")
    e3 = b.local_event("write X=10")
    e4 = b.local_event("write X=20")

    print("Two processes writing independently (no messages exchanged):")
    print(f"  A: write X=1 at ts={e1['ts']}, write X=2 at ts={e2['ts']}")
    print(f"  B: write X=10 at ts={e3['ts']}, write X=20 at ts={e4['ts']}")
    print()

    print(f"Lamport timestamps: A.write(X=1)={e1['ts']}, B.write(X=10)={e3['ts']}")
    print(f"Both have ts=1. After tiebreaking by PID: A < B")
    print(f"System concludes: A's write 'happened before' B's write.")
    print(f"Reality: They're CONCURRENT - neither caused the other.")
    print(f"\nLamport clocks guarantee: if A->B then ts(A)<ts(B)")
    print(f"They do NOT guarantee: if ts(A)<ts(B) then A->B")
    print(f"For concurrency detection, you need vector clocks.")


# ---------------------------------------------------------------------------
# Run everything
# ---------------------------------------------------------------------------

def main():
    print("Lamport Clock - Logical Time in Distributed Systems\n")
    events = run_simulation()
    demo_total_ordering(events)
    demo_concurrency_limitation()


if __name__ == "__main__":
    main()
