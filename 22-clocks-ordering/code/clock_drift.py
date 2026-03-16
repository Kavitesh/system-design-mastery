"""
Clock Drift Simulation
======================
Demonstrates why physical clocks can't be trusted for event ordering
in distributed systems. Simulates multiple servers with independent
clock drift and shows how ordering breaks down.

Run: python clock_drift.py
"""

import time
import random

# ---------------------------------------------------------------------------
# Drifting clock - simulates a server with imperfect hardware
# ---------------------------------------------------------------------------

class DriftingClock:
    """A physical clock that drifts from true time at a configurable rate."""

    def __init__(self, name: str, drift_ppm: float):
        self.name = name
        self.drift_ppm = drift_ppm
        self.drift_per_sec = drift_ppm / 1_000_000
        self.offset = 0.0
        self.base_time = time.time()

    def now(self) -> float:
        elapsed = time.time() - self.base_time
        self.offset = elapsed * self.drift_per_sec
        return time.time() + self.offset

    def skew_from(self, other: "DriftingClock") -> float:
        return abs(self.now() - other.now())


# ---------------------------------------------------------------------------
# Show drift accumulation over simulated time
# ---------------------------------------------------------------------------

def demo_drift_accumulation():
    print("=" * 60)
    print("DEMO 1: Clock Drift Accumulation")
    print("=" * 60)
    print("Two servers with different drift rates over time.\n")

    fast_clock = DriftingClock("Server-A", drift_ppm=+15)
    slow_clock = DriftingClock("Server-B", drift_ppm=-20)

    durations = [
        (1, "1 second"),
        (60, "1 minute"),
        (3600, "1 hour"),
        (86400, "1 day"),
        (2592000, "30 days"),
    ]

    print(f"{'Duration':<15} {'Server-A drift':>18} {'Server-B drift':>18} {'Skew':>15}")
    print("-" * 70)

    for seconds, label in durations:
        drift_a = seconds * 15 / 1_000_000
        drift_b = seconds * (-20) / 1_000_000
        skew = abs(drift_a - drift_b)

        a_str = f"+{drift_a*1000:.3f}ms" if drift_a < 1 else f"+{drift_a:.4f}s"
        b_str = f"{drift_b*1000:.3f}ms" if abs(drift_b) < 1 else f"{drift_b:.4f}s"
        s_str = f"{skew*1000:.3f}ms" if skew < 1 else f"{skew:.4f}s"

        print(f"{label:<15} {a_str:>18} {b_str:>18} {s_str:>15}")

    print(f"\nAt 50k writes/sec, a 1.7s skew means ~85,000 writes could be misordered.")


# ---------------------------------------------------------------------------
# Show how drift breaks event ordering
# ---------------------------------------------------------------------------

def demo_ordering_broken():
    print(f"\n{'=' * 60}")
    print("DEMO 2: Drift Breaks Event Ordering")
    print("=" * 60)
    print("Events happen in a known real order, but clock drift")
    print("makes servers disagree about which came first.\n")

    random.seed(42)

    events = []
    server_offsets = {
        "Server-A": +0.003,
        "Server-B": -0.005,
        "Server-C": +0.008,
    }

    base = 1000000.0
    real_times = sorted([base + random.uniform(0, 0.020) for _ in range(8)])

    for i, real_t in enumerate(real_times):
        server = random.choice(list(server_offsets.keys()))
        observed_t = real_t + server_offsets[server]
        events.append({
            "id": f"E{i+1}",
            "real_time": real_t,
            "server": server,
            "observed_time": observed_t,
        })

    by_real = sorted(events, key=lambda e: e["real_time"])
    by_observed = sorted(events, key=lambda e: e["observed_time"])

    print("Real order (ground truth):")
    for e in by_real:
        offset_ms = (e["observed_time"] - e["real_time"]) * 1000
        print(f"  {e['id']}  real={e['real_time']:.6f}  server={e['server']}  offset={offset_ms:+.1f}ms")

    print(f"\nObserved order (what the system sees):")
    for e in by_observed:
        print(f"  {e['id']}  observed={e['observed_time']:.6f}  server={e['server']}")

    misorders = 0
    for i in range(len(by_real)):
        if by_real[i]["id"] != by_observed[i]["id"]:
            misorders += 1

    print(f"\nPositional mismatches: {misorders}/{len(events)}")
    if misorders > 0:
        print("Clock drift reordered events. Physical timestamps can't be trusted.")
    else:
        print("Got lucky this time - but drift will catch you eventually.")


# ---------------------------------------------------------------------------
# Show NTP correction side effects
# ---------------------------------------------------------------------------

def demo_ntp_jump():
    print(f"\n{'=' * 60}")
    print("DEMO 3: NTP Clock Jump")
    print("=" * 60)
    print("NTP corrects drift by stepping the clock. Watch what")
    print("happens to timestamp-based logic when time jumps backward.\n")

    class JumpingClock:
        def __init__(self):
            self.time = 1000.0
            self.jumped = False

        def tick(self, amount=0.001):
            self.time += amount

        def ntp_correction(self, offset: float):
            old = self.time
            self.time += offset
            self.jumped = True
            return old, self.time

    clock = JumpingClock()
    cache = {}
    log = []

    for i in range(5):
        clock.tick()
        ts = clock.time
        cache[f"key-{i}"] = {"value": f"v{i}", "expires_at": ts + 0.005}
        log.append(f"  SET key-{i} at t={ts:.4f}, expires at t={ts + 0.005:.4f}")

    print("Cache entries set with 5ms TTL:")
    for entry in log:
        print(entry)

    old_t, new_t = clock.ntp_correction(-0.010)
    print(f"\nNTP jumps clock BACKWARD: {old_t:.4f} -> {new_t:.4f} ({(new_t-old_t)*1000:.1f}ms)")
    print(f"\nChecking cache after jump (current time = {clock.time:.4f}):")

    expired = 0
    alive = 0
    for key, entry in cache.items():
        remaining = entry["expires_at"] - clock.time
        status = "ALIVE (should be expired)" if remaining > 0.005 else "looks normal"
        if remaining > 0.005:
            alive += 1
        else:
            expired += 1
        print(f"  {key}: remaining TTL = {remaining*1000:.1f}ms - {status}")

    print(f"\n{alive} entries got extra TTL from the clock jump.")
    print("Lesson: Use monotonic clocks for durations, wall clocks only for display.")


# ---------------------------------------------------------------------------
# Run all demos
# ---------------------------------------------------------------------------

def main():
    print("Clock Drift Simulation - Why Physical Clocks Lie")
    print()
    demo_drift_accumulation()
    demo_ordering_broken()
    demo_ntp_jump()


if __name__ == "__main__":
    main()
