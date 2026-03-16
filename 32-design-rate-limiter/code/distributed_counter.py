"""
Distributed Counter
===================
Simulates multiple API servers sharing a rate limit counter.
Demonstrates three approaches: naive (racy), atomic increment,
and Lua-script-style atomic check-and-set. No Redis needed -
uses threads and shared memory to show the same problems.

Run: python distributed_counter.py
"""

import time
import threading
from concurrent.futures import ThreadPoolExecutor

# ---------------------------------------------------------------------------
# Simulated Redis store (shared state between "servers")
# ---------------------------------------------------------------------------

class SimulatedRedis:
    def __init__(self):
        self.data = {}
        self.lock = threading.Lock()

    def get(self, key: str) -> int:
        return self.data.get(key, 0)

    def set(self, key: str, value: int):
        self.data[key] = value

    def incr(self, key: str) -> int:
        with self.lock:
            val = self.data.get(key, 0) + 1
            self.data[key] = val
            return val

    def eval_lua(self, key: str, limit: int) -> dict:
        """Simulates a Lua script that atomically checks and increments."""
        with self.lock:
            count = self.data.get(key, 0)
            if count < limit:
                self.data[key] = count + 1
                return {"allowed": True, "count": count + 1, "remaining": limit - count - 1}
            return {"allowed": False, "count": count, "remaining": 0}

    def reset(self):
        self.data.clear()


# ---------------------------------------------------------------------------
# Scenario 1: Naive read-then-write (race condition)
# ---------------------------------------------------------------------------

def naive_rate_check(store: SimulatedRedis, key: str, limit: int) -> bool:
    count = store.get(key)
    time.sleep(0.001)  # simulate network latency - opens the race window
    if count < limit:
        store.set(key, count + 1)  # NOT atomic - another thread may have changed it
        return True
    return False


def run_naive(store: SimulatedRedis, num_servers: int, requests_per_server: int, limit: int):
    key = "rate:user42:naive"
    allowed = {"count": 0}
    lock = threading.Lock()

    def server_work(server_id: int):
        for _ in range(requests_per_server):
            if naive_rate_check(store, key, limit):
                with lock:
                    allowed["count"] += 1

    with ThreadPoolExecutor(max_workers=num_servers) as pool:
        futures = [pool.submit(server_work, i) for i in range(num_servers)]
        for f in futures:
            f.result()

    final_count = store.get(key)
    return allowed["count"], final_count


# ---------------------------------------------------------------------------
# Scenario 2: Atomic INCR (correct)
# ---------------------------------------------------------------------------

def atomic_rate_check(store: SimulatedRedis, key: str, limit: int) -> bool:
    count = store.incr(key)
    return count <= limit


def run_atomic(store: SimulatedRedis, num_servers: int, requests_per_server: int, limit: int):
    key = "rate:user42:atomic"
    allowed = {"count": 0}
    lock = threading.Lock()

    def server_work(server_id: int):
        for _ in range(requests_per_server):
            if atomic_rate_check(store, key, limit):
                with lock:
                    allowed["count"] += 1

    with ThreadPoolExecutor(max_workers=num_servers) as pool:
        futures = [pool.submit(server_work, i) for i in range(num_servers)]
        for f in futures:
            f.result()

    final_count = store.get(key)
    return allowed["count"], final_count


# ---------------------------------------------------------------------------
# Scenario 3: Lua-script-style atomic check-and-set
# ---------------------------------------------------------------------------

def lua_rate_check(store: SimulatedRedis, key: str, limit: int) -> bool:
    result = store.eval_lua(key, limit)
    return result["allowed"]


def run_lua(store: SimulatedRedis, num_servers: int, requests_per_server: int, limit: int):
    key = "rate:user42:lua"
    allowed = {"count": 0}
    lock = threading.Lock()

    def server_work(server_id: int):
        for _ in range(requests_per_server):
            if lua_rate_check(store, key, limit):
                with lock:
                    allowed["count"] += 1

    with ThreadPoolExecutor(max_workers=num_servers) as pool:
        futures = [pool.submit(server_work, i) for i in range(num_servers)]
        for f in futures:
            f.result()

    final_count = store.get(key)
    return allowed["count"], final_count


# ---------------------------------------------------------------------------
# Run all scenarios
# ---------------------------------------------------------------------------

def main():
    NUM_SERVERS = 5
    REQUESTS_PER_SERVER = 20
    LIMIT = 50
    TOTAL_REQUESTS = NUM_SERVERS * REQUESTS_PER_SERVER

    print("=" * 70)
    print("DISTRIBUTED RATE LIMITER - RACE CONDITION DEMO")
    print("=" * 70)
    print(f"\nSetup: {NUM_SERVERS} servers, {REQUESTS_PER_SERVER} requests each, limit={LIMIT}")
    print(f"Total requests attempted: {TOTAL_REQUESTS}")
    print(f"Expected: exactly {LIMIT} allowed, {TOTAL_REQUESTS - LIMIT} rejected")

    store = SimulatedRedis()

    # Scenario 1: Naive
    print(f"\n{'-' * 70}")
    print("SCENARIO 1: Naive read-then-write (has race condition)")
    print(f"{'-' * 70}")
    allowed, final = run_naive(store, NUM_SERVERS, REQUESTS_PER_SERVER, LIMIT)
    over = allowed - LIMIT if allowed > LIMIT else 0
    print(f"  Requests allowed:  {allowed}")
    print(f"  Counter in store:  {final}")
    print(f"  Over limit by:     {over}")
    if over > 0:
        print(f"  BUG: {over} extra requests slipped through the race window!")
    else:
        print("  Got lucky this run - but the race exists. Run again to see it.")

    store.reset()

    # Scenario 2: Atomic INCR
    print(f"\n{'-' * 70}")
    print("SCENARIO 2: Atomic INCR (correct)")
    print(f"{'-' * 70}")
    allowed, final = run_atomic(store, NUM_SERVERS, REQUESTS_PER_SERVER, LIMIT)
    print(f"  Requests allowed:  {allowed}")
    print(f"  Counter in store:  {final}")
    print(f"  Over limit by:     {allowed - LIMIT if allowed > LIMIT else 0}")
    print(f"  Exactly {LIMIT} allowed - atomic INCR prevents the race.")

    store.reset()

    # Scenario 3: Lua script
    print(f"\n{'-' * 70}")
    print("SCENARIO 3: Lua-script atomic check-and-increment")
    print(f"{'-' * 70}")
    allowed, final = run_lua(store, NUM_SERVERS, REQUESTS_PER_SERVER, LIMIT)
    print(f"  Requests allowed:  {allowed}")
    print(f"  Counter in store:  {final}")
    print(f"  Over limit by:     {allowed - LIMIT if allowed > LIMIT else 0}")
    print(f"  Also correct - Lua script runs atomically inside Redis.")

    # Summary
    print(f"\n{'=' * 70}")
    print("COMPARISON")
    print(f"{'=' * 70}")
    print(f"  {'Method':<35} {'Correct?':<12} {'Trade-off'}")
    print(f"  {'-'*35} {'-'*12} {'-'*20}")
    print(f"  {'Naive read-then-write':<35} {'NO':<12} Race condition under load")
    print(f"  {'Atomic INCR':<35} {'YES':<12} Simple, one command")
    print(f"  {'Lua script':<35} {'YES':<12} Flexible, handles complex logic")
    print(f"\n  TAKEAWAY: Never separate the read and write. Use INCR for simple")
    print(f"  counters, Lua scripts for token bucket or sliding window logic.")
    print(f"{'=' * 70}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()
