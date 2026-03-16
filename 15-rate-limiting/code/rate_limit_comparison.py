"""
Rate Limiting Algorithm Comparison
====================================
Visual side-by-side comparison of how four algorithms handle identical
burst traffic patterns. Shows allow/deny decisions over time with
ASCII timeline charts.

Run: python rate_limit_comparison.py
"""

import time
from collections import deque


# ---------------------------------------------------------------------------
# Algorithms (minimal implementations for comparison)
# ---------------------------------------------------------------------------

class TokenBucket:
    def __init__(self, capacity, refill_rate):
        self.capacity = capacity
        self.tokens = float(capacity)
        self.refill_rate = refill_rate
        self.last_time = 0.0

    def allow(self, timestamp: float) -> bool:
        elapsed = timestamp - self.last_time
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_time = timestamp
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False


class LeakyBucket:
    def __init__(self, capacity, drain_rate):
        self.capacity = capacity
        self.drain_rate = drain_rate
        self.water = 0.0
        self.last_time = 0.0

    def allow(self, timestamp: float) -> bool:
        elapsed = timestamp - self.last_time
        self.water = max(0, self.water - elapsed * self.drain_rate)
        self.last_time = timestamp
        if self.water < self.capacity:
            self.water += 1
            return True
        return False


class FixedWindow:
    def __init__(self, limit, window_size):
        self.limit = limit
        self.window_size = window_size
        self.counter = 0
        self.window_start = 0.0

    def allow(self, timestamp: float) -> bool:
        if timestamp - self.window_start >= self.window_size:
            self.counter = 0
            self.window_start = timestamp
        if self.counter < self.limit:
            self.counter += 1
            return True
        return False


class SlidingWindowCounter:
    def __init__(self, limit, window_size):
        self.limit = limit
        self.window_size = window_size
        self.prev_count = 0
        self.curr_count = 0
        self.window_start = 0.0

    def allow(self, timestamp: float) -> bool:
        if timestamp - self.window_start >= self.window_size:
            self.prev_count = self.curr_count
            self.curr_count = 0
            self.window_start = timestamp
        elapsed = timestamp - self.window_start
        weight = 1.0 - (elapsed / self.window_size) if self.window_size > 0 else 0
        estimated = self.prev_count * weight + self.curr_count
        if estimated < self.limit:
            self.curr_count += 1
            return True
        return False


# ---------------------------------------------------------------------------
# Traffic Patterns
# ---------------------------------------------------------------------------

def generate_steady_traffic(duration: float, rate: float) -> list:
    """Evenly spaced requests."""
    timestamps = []
    interval = 1.0 / rate
    t = 0.0
    while t < duration:
        timestamps.append(round(t, 4))
        t += interval
    return timestamps


def generate_burst_traffic(duration: float, burst_size: int,
                           burst_interval: float) -> list:
    """Periodic bursts of requests."""
    timestamps = []
    t = 0.0
    while t < duration:
        for i in range(burst_size):
            timestamps.append(round(t + i * 0.01, 4))
        t += burst_interval
    return timestamps


def generate_spike_traffic() -> list:
    """Steady traffic with a sudden spike in the middle."""
    timestamps = []
    for i in range(5):
        timestamps.append(i * 0.2)
    for i in range(20):
        timestamps.append(1.0 + i * 0.02)
    for i in range(5):
        timestamps.append(2.0 + i * 0.2)
    return [round(t, 4) for t in timestamps]


# ---------------------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------------------

def run_comparison(name: str, timestamps: list, limit: int, window: float):
    print(f"\n{'=' * 65}")
    print(f"  {name}")
    print(f"  {len(timestamps)} requests | limit: {limit}/window | window: {window}s")
    print(f"{'=' * 65}\n")

    algorithms = {
        "Token Bucket":     TokenBucket(capacity=limit, refill_rate=limit / window),
        "Leaky Bucket":     LeakyBucket(capacity=limit, drain_rate=limit / window),
        "Fixed Window":     FixedWindow(limit=limit, window_size=window),
        "Sliding Window":   SlidingWindowCounter(limit=limit, window_size=window),
    }

    results = {}
    for algo_name, algo in algorithms.items():
        decisions = []
        for ts in timestamps:
            decisions.append(algo.allow(ts))
        results[algo_name] = decisions

    bar_width = min(len(timestamps), 50)
    scale = max(1, len(timestamps) // bar_width)

    for algo_name, decisions in results.items():
        allowed = sum(decisions)
        denied = len(decisions) - allowed

        chunks = []
        for i in range(0, len(decisions), scale):
            chunk = decisions[i:i + scale]
            allow_pct = sum(chunk) / len(chunk)
            if allow_pct > 0.7:
                chunks.append("█")
            elif allow_pct > 0.3:
                chunks.append("▓")
            elif allow_pct > 0:
                chunks.append("░")
            else:
                chunks.append(" ")

        bar = "".join(chunks)
        print(f"  {algo_name:<20} [{bar:<{bar_width}}] {allowed:>3}/{len(decisions)} allowed")

    print(f"\n  Legend: █ = mostly allowed  ▓ = mixed  ░ = mostly denied  (space) = all denied")

    print(f"\n  {'Algorithm':<20} {'Allowed':<10} {'Denied':<10} {'Allow Rate'}")
    print(f"  {'-'*55}")
    for algo_name, decisions in results.items():
        allowed = sum(decisions)
        denied = len(decisions) - allowed
        rate = allowed / len(decisions) * 100
        print(f"  {algo_name:<20} {allowed:<10} {denied:<10} {rate:.1f}%")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Rate Limiting Algorithm Comparison")
    print("=" * 65)
    print("  Same traffic pattern, same limits, different algorithms.")
    print("  Watch how each one decides what gets through.")

    # Pattern 1: Steady 15 req/s for 3 seconds, limit 10/s
    run_comparison(
        "Pattern 1: Steady Overload (15 req/s, limit 10/s)",
        generate_steady_traffic(duration=3.0, rate=15),
        limit=10, window=1.0,
    )

    # Pattern 2: Bursts of 8 every 0.5s, limit 10/s
    run_comparison(
        "Pattern 2: Periodic Bursts (8 requests every 500ms)",
        generate_burst_traffic(duration=3.0, burst_size=8, burst_interval=0.5),
        limit=10, window=1.0,
    )

    # Pattern 3: Spike
    run_comparison(
        "Pattern 3: Sudden Spike (5 slow, 20 fast, 5 slow)",
        generate_spike_traffic(),
        limit=10, window=1.0,
    )

    # Pattern 4: Rapid burst then nothing
    single_burst = [i * 0.005 for i in range(25)]
    run_comparison(
        "Pattern 4: Single Burst (25 requests in 125ms)",
        single_burst,
        limit=10, window=1.0,
    )

    print(f"\n{'=' * 65}")
    print("KEY INSIGHTS")
    print(f"{'=' * 65}")
    print("""
  1. Token Bucket allows the initial burst (up to capacity), then
     throttles to the refill rate. Best for APIs that want to
     tolerate short spikes.

  2. Leaky Bucket smooths everything to a constant rate. Bursts
     get queued or dropped. Best when you need predictable load
     on downstream services.

  3. Fixed Window allows the full limit per window but can let
     2x through at boundaries. Don't use in production.

  4. Sliding Window Counter gives near-perfect accuracy with
     minimal memory. The best general-purpose choice for
     strict per-window enforcement.

  Pick token bucket for burst-tolerant APIs.
  Pick sliding window counter for strict quotas.
  Avoid fixed window - the boundary exploit is real.
    """)


if __name__ == "__main__":
    main()
