"""
Distributed Rate Limiting
===========================
Simulates the challenge of rate limiting across multiple servers.

Compares three approaches:
  1. No coordination - each server limits independently (broken)
  2. Centralized store - all servers share a counter (accurate)
  3. Local counters with periodic sync (approximate)

Run: python distributed_rate_limiter.py
"""

import time
import threading
from collections import defaultdict


# ---------------------------------------------------------------------------
# Shared counter store (simulates Redis)
# ---------------------------------------------------------------------------

class CentralStore:
    """Thread-safe counter store simulating Redis INCR + EXPIRE."""

    def __init__(self):
        self._counters = defaultdict(int)
        self._expiry = {}
        self._lock = threading.Lock()
        self.total_ops = 0

    def increment(self, key: str, window_seconds: float) -> int:
        with self._lock:
            now = time.time()
            self.total_ops += 1
            if key in self._expiry and now > self._expiry[key]:
                self._counters[key] = 0
            self._counters[key] += 1
            if key not in self._expiry or now > self._expiry[key]:
                self._expiry[key] = now + window_seconds
            return self._counters[key]

    def get(self, key: str) -> int:
        with self._lock:
            now = time.time()
            if key in self._expiry and now > self._expiry[key]:
                return 0
            return self._counters[key]


# ---------------------------------------------------------------------------
# Server Node
# ---------------------------------------------------------------------------

class ServerNode:
    """Simulates a single API server with rate limiting."""

    def __init__(self, node_id: str, limit: int, window: float,
                 central_store: CentralStore = None, mode: str = "local"):
        self.node_id = node_id
        self.limit = limit
        self.window = window
        self.mode = mode
        self.central_store = central_store
        self.local_counter = defaultdict(int)
        self.local_window_start = {}
        self.allowed = 0
        self.denied = 0

    def handle_request(self, client_id: str) -> bool:
        if self.mode == "local":
            return self._check_local(client_id)
        elif self.mode == "centralized":
            return self._check_centralized(client_id)
        elif self.mode == "sync":
            return self._check_sync(client_id)
        return False

    def _check_local(self, client_id: str) -> bool:
        now = time.time()
        key = f"{client_id}"
        if key not in self.local_window_start or now - self.local_window_start[key] >= self.window:
            self.local_counter[key] = 0
            self.local_window_start[key] = now
        self.local_counter[key] += 1
        if self.local_counter[key] <= self.limit:
            self.allowed += 1
            return True
        self.denied += 1
        return False

    def _check_centralized(self, client_id: str) -> bool:
        key = f"rate:{client_id}"
        count = self.central_store.increment(key, self.window)
        if count <= self.limit:
            self.allowed += 1
            return True
        self.denied += 1
        return False

    def _check_sync(self, client_id: str) -> bool:
        per_node_limit = self.limit // 3
        now = time.time()
        key = f"{client_id}"
        if key not in self.local_window_start or now - self.local_window_start[key] >= self.window:
            self.local_counter[key] = 0
            self.local_window_start[key] = now
        self.local_counter[key] += 1
        if self.local_counter[key] <= per_node_limit:
            self.allowed += 1
            return True
        self.denied += 1
        return False


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

def simulate_traffic(nodes: list, total_requests: int, client_id: str = "user-42"):
    """Distributes requests round-robin across nodes."""
    results = []
    for i in range(total_requests):
        node = nodes[i % len(nodes)]
        allowed = node.handle_request(client_id)
        results.append((node.node_id, allowed))
    return results


def run_scenario(name: str, mode: str, limit: int, total_requests: int):
    print(f"\n{'=' * 60}")
    print(f"  {name}")
    print(f"  Mode: {mode} | Limit: {limit}/window | Requests: {total_requests}")
    print(f"{'=' * 60}")

    central = CentralStore()
    nodes = [
        ServerNode(f"node-{i+1}", limit, window=1.0,
                   central_store=central, mode=mode)
        for i in range(3)
    ]

    results = simulate_traffic(nodes, total_requests)
    total_allowed = sum(1 for _, a in results if a)
    total_denied = total_requests - total_allowed

    print(f"\n  Total allowed: {total_allowed}  |  Total denied: {total_denied}")
    if mode != "centralized":
        overflow = max(0, total_allowed - limit)
        if overflow > 0:
            print(f"  OVERFLOW: {overflow} requests beyond the limit!")
        else:
            print(f"  Within limit: OK")
    else:
        print(f"  Central store ops: {central.total_ops}")

    print(f"\n  Per-node breakdown:")
    for node in nodes:
        print(f"    {node.node_id}: allowed={node.allowed}, denied={node.denied}")

    return total_allowed


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Distributed Rate Limiting Simulation")
    print("=" * 60)
    print("  3 server nodes, 1 client, round-robin load balancing")
    print("  Goal: enforce a global limit of 30 requests per window")

    allowed_local = run_scenario(
        "Scenario 1: Independent Local Counters (BROKEN)",
        mode="local", limit=30, total_requests=60,
    )

    allowed_central = run_scenario(
        "Scenario 2: Centralized Store (CORRECT)",
        mode="centralized", limit=30, total_requests=60,
    )

    allowed_sync = run_scenario(
        "Scenario 3: Split Limit Across Nodes (APPROXIMATE)",
        mode="sync", limit=30, total_requests=60,
    )

    # Summary
    print(f"\n{'=' * 60}")
    print("COMPARISON")
    print(f"{'=' * 60}")
    print(f"""
  Global limit: 30 requests per window
  Total requests sent: 60

  {'Approach':<35} {'Allowed':<12} {'Accurate?'}
  {'-'*60}
  {'Local (no coordination)':<35} {allowed_local:<12} {'NO - each node allows up to 30'}
  {'Centralized (shared Redis)':<35} {allowed_central:<12} {'YES - single source of truth'}
  {'Split limit (limit/N per node)':<35} {allowed_sync:<12} {'APPROXIMATE - uneven traffic skews it'}

  The centralized approach is the production standard. Redis INCR is
  atomic, fast (~1ms), and gives you exact counts. The split-limit
  approach works at extreme scale where Redis becomes the bottleneck,
  but you trade accuracy for throughput.
    """)


if __name__ == "__main__":
    main()
