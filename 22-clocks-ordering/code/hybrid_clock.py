"""
Hybrid Logical Clock (HLC)
==========================
Implements Hybrid Logical Clocks as described by Kulkarni et al.
Combines physical wall-clock time with logical counters to get
the best of both worlds: real-time proximity and causal ordering.

Run: python hybrid_clock.py
"""

import time

# ---------------------------------------------------------------------------
# HLC timestamp
# ---------------------------------------------------------------------------

class HLCTimestamp:
    """A hybrid logical clock timestamp: (wall_time_ms, counter)."""

    def __init__(self, wall_ms: int, counter: int):
        self.wall_ms = wall_ms
        self.counter = counter

    def __lt__(self, other):
        if self.wall_ms != other.wall_ms:
            return self.wall_ms < other.wall_ms
        return self.counter < other.counter

    def __le__(self, other):
        return self == other or self < other

    def __eq__(self, other):
        return self.wall_ms == other.wall_ms and self.counter == other.counter

    def __repr__(self):
        return f"({self.wall_ms}, c={self.counter})"

    def to_packed(self) -> int:
        return (self.wall_ms << 16) | (self.counter & 0xFFFF)


# ---------------------------------------------------------------------------
# HLC implementation
# ---------------------------------------------------------------------------

class HybridLogicalClock:
    """
    Hybrid Logical Clock per node.
    Uses a simulated physical clock to make demos reproducible.
    """

    def __init__(self, node_id: str, start_time_ms: int = 1000):
        self.node_id = node_id
        self.l = start_time_ms
        self.c = 0
        self._sim_time = start_time_ms
        self._auto_advance = 1

    def _physical_time(self) -> int:
        self._sim_time += self._auto_advance
        return self._sim_time

    def set_physical_time(self, ms: int):
        self._sim_time = ms
        self._auto_advance = 0

    def resume_auto_advance(self):
        self._auto_advance = 1

    def now(self) -> HLCTimestamp:
        pt = self._physical_time()
        old_l = self.l

        self.l = max(old_l, pt)

        if self.l == old_l:
            self.c += 1
        else:
            self.c = 0

        return HLCTimestamp(self.l, self.c)

    def receive(self, msg_ts: HLCTimestamp) -> HLCTimestamp:
        pt = self._physical_time()
        old_l = self.l

        self.l = max(old_l, msg_ts.wall_ms, pt)

        if self.l == old_l == msg_ts.wall_ms:
            self.c = max(self.c, msg_ts.counter) + 1
        elif self.l == old_l:
            self.c = self.c + 1
        elif self.l == msg_ts.wall_ms:
            self.c = msg_ts.counter + 1
        else:
            self.c = 0

        return HLCTimestamp(self.l, self.c)


# ---------------------------------------------------------------------------
# Demo 1: Basic HLC operation
# ---------------------------------------------------------------------------

def demo_basic_hlc():
    print("=" * 65)
    print("DEMO 1: Basic HLC Operation")
    print("=" * 65)
    print("Two nodes exchange messages. HLC stays close to wall time")
    print("while preserving causal order.\n")

    node_a = HybridLogicalClock("A", start_time_ms=1000)
    node_b = HybridLogicalClock("B", start_time_ms=1000)

    events = []

    ts1 = node_a.now()
    events.append(("A", "local: accept request", ts1))

    ts2 = node_a.now()
    events.append(("A", "send: forward to B", ts2))

    ts3 = node_b.receive(ts2)
    events.append(("B", "recv: request from A", ts3))

    ts4 = node_b.now()
    events.append(("B", "local: process query", ts4))

    ts5 = node_b.now()
    events.append(("B", "send: response to A", ts5))

    ts6 = node_a.receive(ts5)
    events.append(("A", "recv: response from B", ts6))

    ts7 = node_a.now()
    events.append(("A", "local: return to client", ts7))

    print(f"{'Node':<6} {'HLC Timestamp':<18} {'Event'}")
    print("-" * 65)
    for node, desc, ts in events:
        print(f"{node:<6} {str(ts):<18} {desc}")

    print(f"\nAll timestamps strictly increasing along causal chain.")
    print(f"Wall-time component stays close to physical time (within a few ms).")


# ---------------------------------------------------------------------------
# Demo 2: HLC handles clock skew gracefully
# ---------------------------------------------------------------------------

def demo_clock_skew():
    print(f"\n{'=' * 65}")
    print("DEMO 2: HLC Handles Clock Skew")
    print("=" * 65)
    print("Node B's physical clock is 50ms behind Node A's.")
    print("HLC ensures correct ordering despite the skew.\n")

    node_a = HybridLogicalClock("A", start_time_ms=1000)
    node_b = HybridLogicalClock("B", start_time_ms=950)

    ts1 = node_a.now()
    print(f"  A local event:    {ts1}  (A's physical clock at ~1001ms)")

    ts2 = node_a.now()
    print(f"  A sends to B:     {ts2}  (message carries this timestamp)")

    ts3 = node_b.receive(ts2)
    print(f"  B receives:       {ts3}  (B's clock was at ~952ms, adopts A's time)")

    ts4 = node_b.now()
    print(f"  B local event:    {ts4}  (B continues from A's time, not its own)")

    ts5 = node_b.now()
    print(f"  B sends to A:     {ts5}")

    ts6 = node_a.receive(ts5)
    print(f"  A receives:       {ts6}")

    print(f"\n  B's physical clock was 50ms behind, but HLC kept timestamps")
    print(f"  monotonically increasing. No causal violations.")
    print(f"  The logical component (c) increments when physical time hasn't advanced.")


# ---------------------------------------------------------------------------
# Demo 3: Compare HLC vs Lamport vs wall clock
# ---------------------------------------------------------------------------

def demo_comparison():
    print(f"\n{'=' * 65}")
    print("DEMO 3: HLC vs Lamport Clock vs Wall Clock")
    print("=" * 65)
    print()

    print(f"{'Property':<30} {'Wall Clock':<16} {'Lamport':<16} {'HLC'}")
    print("-" * 78)
    rows = [
        ("Tracks real time", "Yes", "No", "Yes"),
        ("Monotonic across nodes", "No (drift)", "Yes", "Yes"),
        ("Detects causality", "No", "One direction", "One direction"),
        ("Detects concurrency", "No", "No", "No"),
        ("Size per timestamp", "8 bytes", "8 bytes", "12 bytes"),
        ("Needs clock sync (NTP)", "Yes", "No", "Tolerates skew"),
        ("Human-readable", "Yes", "No", "Mostly yes"),
        ("Special hardware needed", "No", "No", "No"),
    ]
    for prop, wall, lamport, hlc in rows:
        print(f"  {prop:<30} {wall:<16} {lamport:<16} {hlc}")

    print(f"\nHLC sits in the sweet spot: close to real time, causally correct,")
    print(f"no special hardware, compact. That's why CockroachDB picked it.")


# ---------------------------------------------------------------------------
# Demo 4: Rapid events - counter saves the day
# ---------------------------------------------------------------------------

def demo_rapid_events():
    print(f"\n{'=' * 65}")
    print("DEMO 4: Rapid Events Within Same Millisecond")
    print("=" * 65)
    print("Multiple events happen faster than clock resolution.")
    print("The counter component distinguishes them.\n")

    node = HybridLogicalClock("X", start_time_ms=5000)
    node.set_physical_time(5001)

    timestamps = []
    for i in range(8):
        ts = node.now()
        timestamps.append(ts)

    print(f"{'Event':<10} {'wall_ms':<12} {'counter':<10} {'Packed (sortable)'}")
    print("-" * 50)
    for i, ts in enumerate(timestamps):
        print(f"E{i+1:<9} {ts.wall_ms:<12} {ts.counter:<10} {ts.to_packed()}")

    all_unique = len(set(ts.to_packed() for ts in timestamps)) == len(timestamps)
    all_ordered = all(timestamps[i] < timestamps[i+1] for i in range(len(timestamps)-1))

    print(f"\n  All timestamps unique: {all_unique}")
    print(f"  All timestamps ordered: {all_ordered}")
    print(f"  Physical clock didn't advance, but counter kept them distinct.")
    print(f"  Packed into a single 64-bit int for efficient storage and comparison.")

    node.resume_auto_advance()
    ts_later = node.now()
    print(f"\n  After physical clock advances: {ts_later}")
    print(f"  Counter resets to 0 - physical time takes over again.")


# ---------------------------------------------------------------------------
# Run all demos
# ---------------------------------------------------------------------------

def main():
    print("Hybrid Logical Clocks - The Practical Middle Ground\n")
    demo_basic_hlc()
    demo_clock_skew()
    demo_comparison()
    demo_rapid_events()


if __name__ == "__main__":
    main()
