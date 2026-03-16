"""
Retry Patterns Comparison
=========================
Side-by-side comparison of simple retry, exponential backoff,
and exponential backoff with jitter.
"""

import time
import random

# ---------------------------------------------------------------------------
#  Retry Strategies
# ---------------------------------------------------------------------------

def simple_retry(func, max_attempts=5):
    """Retries immediately on failure. Don't use this in production."""
    attempts = []
    for attempt in range(1, max_attempts + 1):
        start = time.time()
        try:
            result = func(attempt)
            attempts.append({"attempt": attempt, "delay": 0, "result": "success"})
            return result, attempts
        except Exception:
            delay = 0
            attempts.append({"attempt": attempt, "delay": delay, "result": "fail"})
    return None, attempts


def exponential_backoff(func, max_attempts=5, base_delay=0.5, max_delay=8.0):
    """Doubles the wait between each retry."""
    attempts = []
    for attempt in range(1, max_attempts + 1):
        try:
            result = func(attempt)
            attempts.append({"attempt": attempt, "delay": 0, "result": "success"})
            return result, attempts
        except Exception:
            if attempt < max_attempts:
                delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                attempts.append({"attempt": attempt, "delay": delay, "result": "fail"})
                time.sleep(delay)
            else:
                attempts.append({"attempt": attempt, "delay": 0, "result": "fail"})
    return None, attempts


def exponential_backoff_jitter(func, max_attempts=5, base_delay=0.5, max_delay=8.0):
    """Exponential backoff with full jitter to prevent thundering herd."""
    attempts = []
    for attempt in range(1, max_attempts + 1):
        try:
            result = func(attempt)
            attempts.append({"attempt": attempt, "delay": 0, "result": "success"})
            return result, attempts
        except Exception:
            if attempt < max_attempts:
                exp_delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                delay = random.uniform(0, exp_delay)
                attempts.append({"attempt": attempt, "delay": delay, "result": "fail"})
                time.sleep(delay)
            else:
                attempts.append({"attempt": attempt, "delay": 0, "result": "fail"})
    return None, attempts


# ---------------------------------------------------------------------------
#  Simulated Flaky Service
# ---------------------------------------------------------------------------

class FlakyEndpoint:
    """Fails for the first N calls, then succeeds."""

    def __init__(self, fail_count=3):
        self.calls = 0
        self.fail_count = fail_count

    def call(self, attempt_num):
        self.calls += 1
        if self.calls <= self.fail_count:
            raise ConnectionError(f"Service down (call {self.calls})")
        return f"Success on attempt {attempt_num}"

    def reset(self):
        self.calls = 0


# ---------------------------------------------------------------------------
#  Demo
# ---------------------------------------------------------------------------

def print_attempts(strategy_name, attempts, elapsed):
    print(f"\n{strategy_name}")
    print("-" * 50)
    total_delay = 0
    for a in attempts:
        status = "OK" if a["result"] == "success" else "FAIL"
        delay_str = f"  (waited {a['delay']:.2f}s)" if a["delay"] > 0 else ""
        print(f"  Attempt {a['attempt']}: {status}{delay_str}")
        total_delay += a["delay"]
    print(f"  Total attempts: {len(attempts)} | Total delay: {total_delay:.2f}s | Wall time: {elapsed:.2f}s")


def run_strategy(name, strategy_func, endpoint, **kwargs):
    endpoint.reset()
    start = time.time()
    result, attempts = strategy_func(endpoint.call, **kwargs)
    elapsed = time.time() - start
    print_attempts(name, attempts, elapsed)
    return result


def main():
    print("Retry Patterns Comparison")
    print("=" * 50)
    print("Simulated service fails 3 times, then succeeds.\n")

    endpoint = FlakyEndpoint(fail_count=3)

    run_strategy("1. Simple Retry (no delay)", simple_retry, endpoint)
    run_strategy("2. Exponential Backoff", exponential_backoff, endpoint)
    run_strategy("3. Exponential Backoff + Jitter", exponential_backoff_jitter, endpoint)

    print("\n" + "=" * 50)
    print("Thundering Herd: 10 clients, 3 retries each\n")

    print("Without jitter - all clients retry at identical times:")
    for attempt in range(3):
        delay = 0.5 * (2 ** attempt)
        print(f"  Retry {attempt + 1}: all 10 clients hit at exactly {delay:.1f}s")

    print("\nWith jitter - clients spread across the window:")
    for attempt in range(3):
        exp_delay = 0.5 * (2 ** attempt)
        times = sorted([random.uniform(0, exp_delay) for _ in range(10)])
        print(f"  Retry {attempt + 1}: spread {times[0]:.2f}s to {times[-1]:.2f}s")

    print("\nTakeaway: Jitter prevents synchronized retry bursts.")


if __name__ == "__main__":
    main()
