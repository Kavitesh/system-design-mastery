"""
Rate Limiting Algorithms
=========================
Implements the four major rate limiting algorithms from scratch so you
can see exactly how each one decides to allow or reject a request.

Token bucket, leaky bucket, fixed window, and sliding window counter -
all tested against the same request pattern.

Run: python rate_limiters.py
"""

import time
from collections import deque


# ---------------------------------------------------------------------------
# Token Bucket
# ---------------------------------------------------------------------------

class TokenBucket:
    """Allows bursts up to capacity, refills at a constant rate."""

    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()

    def _refill(self):
        now = time.time()
        elapsed = now - self.last_refill
        new_tokens = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_refill = now

    def allow(self) -> bool:
        self._refill()
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False


# ---------------------------------------------------------------------------
# Leaky Bucket
# ---------------------------------------------------------------------------

class LeakyBucket:
    """Queues requests and processes them at a fixed rate."""

    def __init__(self, capacity: int, drain_rate: float):
        self.capacity = capacity
        self.drain_rate = drain_rate
        self.queue = deque()
        self.last_drain = time.time()

    def _drain(self):
        now = time.time()
        elapsed = now - self.last_drain
        to_drain = int(elapsed * self.drain_rate)
        for _ in range(min(to_drain, len(self.queue))):
            self.queue.popleft()
        if to_drain > 0:
            self.last_drain = now

    def allow(self) -> bool:
        self._drain()
        if len(self.queue) < self.capacity:
            self.queue.append(time.time())
            return True
        return False


# ---------------------------------------------------------------------------
# Fixed Window Counter
# ---------------------------------------------------------------------------

class FixedWindow:
    """Counts requests in fixed time windows. Simple but has the boundary problem."""

    def __init__(self, limit: int, window_seconds: float):
        self.limit = limit
        self.window_seconds = window_seconds
        self.counter = 0
        self.window_start = time.time()

    def _reset_if_needed(self):
        now = time.time()
        if now - self.window_start >= self.window_seconds:
            self.counter = 0
            self.window_start = now

    def allow(self) -> bool:
        self._reset_if_needed()
        if self.counter < self.limit:
            self.counter += 1
            return True
        return False


# ---------------------------------------------------------------------------
# Sliding Window Counter
# ---------------------------------------------------------------------------

class SlidingWindowCounter:
    """Weighted average of current and previous window. Near-perfect accuracy."""

    def __init__(self, limit: int, window_seconds: float):
        self.limit = limit
        self.window_seconds = window_seconds
        self.current_count = 0
        self.previous_count = 0
        self.window_start = time.time()

    def _slide_if_needed(self):
        now = time.time()
        elapsed = now - self.window_start
        if elapsed >= self.window_seconds:
            self.previous_count = self.current_count
            self.current_count = 0
            self.window_start = now

    def allow(self) -> bool:
        self._slide_if_needed()
        now = time.time()
        elapsed = now - self.window_start
        window_fraction = elapsed / self.window_seconds
        overlap = 1.0 - window_fraction
        weighted = self.previous_count * overlap + self.current_count
        if weighted < self.limit:
            self.current_count += 1
            return True
        return False


# ---------------------------------------------------------------------------
# Demo helpers
# ---------------------------------------------------------------------------

def test_algorithm(name: str, limiter, request_count: int, delay: float):
    """Send request_count requests with a delay between each."""
    allowed = 0
    denied = 0
    results = []

    for i in range(request_count):
        if limiter.allow():
            allowed += 1
            results.append(".")
        else:
            denied += 1
            results.append("x")
        if delay > 0:
            time.sleep(delay)

    timeline = "".join(results)
    print(f"  {name:<24} allowed={allowed:<3} denied={denied:<3} [{timeline}]")
    return allowed, denied


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Rate Limiting Algorithms Demo")
    print("=" * 60)

    # Scenario 1: Steady traffic
    print("\n--- Scenario 1: Steady Traffic (20 requests, 50ms apart) ---")
    print("  Limit: 10 per second\n")

    test_algorithm("Token Bucket",
                   TokenBucket(capacity=10, refill_rate=10), 20, 0.05)
    test_algorithm("Leaky Bucket",
                   LeakyBucket(capacity=10, drain_rate=10), 20, 0.05)
    test_algorithm("Fixed Window",
                   FixedWindow(limit=10, window_seconds=1.0), 20, 0.05)
    test_algorithm("Sliding Window Counter",
                   SlidingWindowCounter(limit=10, window_seconds=1.0), 20, 0.05)

    # Scenario 2: Burst traffic
    print("\n--- Scenario 2: Burst Traffic (15 requests, no delay) ---")
    print("  Limit: 10 per second\n")

    test_algorithm("Token Bucket",
                   TokenBucket(capacity=10, refill_rate=10), 15, 0)
    test_algorithm("Leaky Bucket",
                   LeakyBucket(capacity=10, drain_rate=10), 15, 0)
    test_algorithm("Fixed Window",
                   FixedWindow(limit=10, window_seconds=1.0), 15, 0)
    test_algorithm("Sliding Window Counter",
                   SlidingWindowCounter(limit=10, window_seconds=1.0), 15, 0)

    # Scenario 3: Burst then pause then burst
    print("\n--- Scenario 3: Burst, Pause, Burst ---")
    print("  5 rapid requests, 1s pause, 5 more rapid requests")
    print("  Limit: 5 per second\n")

    algorithms = [
        ("Token Bucket", TokenBucket(capacity=5, refill_rate=5)),
        ("Leaky Bucket", LeakyBucket(capacity=5, drain_rate=5)),
        ("Fixed Window", FixedWindow(limit=5, window_seconds=1.0)),
        ("Sliding Window Counter", SlidingWindowCounter(limit=5, window_seconds=1.0)),
    ]

    for name, limiter in algorithms:
        allowed = 0
        denied = 0
        results = []

        for i in range(5):
            r = limiter.allow()
            results.append("." if r else "x")
            allowed += r
            denied += (not r)

        results.append("|")
        time.sleep(1.0)

        for i in range(5):
            r = limiter.allow()
            results.append("." if r else "x")
            allowed += r
            denied += (not r)

        timeline = "".join(results)
        print(f"  {name:<24} allowed={allowed:<3} denied={denied:<3} [{timeline}]")

    # Summary
    print("\n" + "=" * 60)
    print("ALGORITHM SUMMARY")
    print("=" * 60)
    print(f"""
  {'Algorithm':<24} {'Memory':<20} {'Burst Friendly':<18} {'Accuracy'}
  {'-'*75}
  {'Token Bucket':<24} {'2 values/key':<20} {'Yes (up to cap)':<18} {'N/A'}
  {'Leaky Bucket':<24} {'Queue (cap items)':<20} {'No (smoothed)':<18} {'N/A'}
  {'Fixed Window':<24} {'2 values/key':<20} {'2x at boundary':<18} {'Poor'}
  {'Sliding Window Counter':<24} {'3 values/key':<20} {'Weighted smooth':<18} {'Near-perfect'}

  Legend: . = allowed, x = denied, | = 1 second pause
    """)


if __name__ == "__main__":
    main()
