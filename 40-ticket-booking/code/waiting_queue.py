"""
Waiting Queue
=============
Fair FIFO queue for high-demand events. Instead of letting 2 million
users slam the seat selection page, users join a queue and are admitted
in controlled batches.

Simulates what Redis sorted sets (ZADD/ZPOPMIN) do in production.

Usage:
  python waiting_queue.py
"""

import time
import threading
import heapq
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Queue engine (simulates Redis sorted set with timestamps as scores)
# ---------------------------------------------------------------------------

@dataclass(order=True)
class QueueEntry:
    join_time: float
    user_id: str = field(compare=False)

class WaitingQueue:
    def __init__(self, event_id: str, batch_size: int = 5, batch_interval: float = 2.0,
                 access_ttl: float = 30.0):
        self.event_id = event_id
        self.batch_size = batch_size
        self.batch_interval = batch_interval
        self.access_ttl = access_ttl

        self._heap: list[QueueEntry] = []
        self._positions: dict[str, int] = {}
        self._access_tokens: dict[str, float] = {}
        self._admitted_count = 0
        self._lock = threading.Lock()
        self._running = False

    def join(self, user_id: str) -> dict:
        with self._lock:
            if user_id in self._positions:
                pos = self._positions[user_id]
                return {"status": "already_queued", "position": pos,
                        "estimated_wait": self._estimate_wait(pos)}

            if user_id in self._access_tokens:
                return {"status": "already_admitted", "expires_in":
                        round(self._access_tokens[user_id] - time.time(), 1)}

            entry = QueueEntry(join_time=time.time(), user_id=user_id)
            heapq.heappush(self._heap, entry)
            position = len(self._heap)
            self._positions[user_id] = position

            return {"status": "queued", "position": position,
                    "estimated_wait": self._estimate_wait(position)}

    def get_position(self, user_id: str) -> dict:
        with self._lock:
            if user_id in self._access_tokens:
                ttl = self._access_tokens[user_id] - time.time()
                if ttl > 0:
                    return {"status": "admitted", "expires_in": round(ttl, 1)}
                del self._access_tokens[user_id]
                return {"status": "token_expired"}

            if user_id in self._positions:
                pos = self._positions[user_id]
                return {"status": "waiting", "position": pos,
                        "estimated_wait": self._estimate_wait(pos)}

            return {"status": "not_in_queue"}

    def validate_access(self, user_id: str) -> bool:
        with self._lock:
            if user_id in self._access_tokens:
                if self._access_tokens[user_id] > time.time():
                    return True
                del self._access_tokens[user_id]
            return False

    def admit_batch(self) -> list[str]:
        admitted = []
        with self._lock:
            for _ in range(self.batch_size):
                if not self._heap:
                    break
                entry = heapq.heappop(self._heap)
                self._access_tokens[entry.user_id] = time.time() + self.access_ttl
                self._positions.pop(entry.user_id, None)
                self._admitted_count += 1
                admitted.append(entry.user_id)

            # Recalculate positions after batch removal
            for i, entry in enumerate(self._heap):
                self._positions[entry.user_id] = i + 1

        return admitted

    def stats(self) -> dict:
        with self._lock:
            return {
                "queue_length": len(self._heap),
                "active_tokens": sum(1 for t in self._access_tokens.values() if t > time.time()),
                "total_admitted": self._admitted_count,
            }

    def _estimate_wait(self, position: int) -> str:
        batches_ahead = position / self.batch_size
        seconds = batches_ahead * self.batch_interval
        if seconds < 60:
            return f"{int(seconds)}s"
        return f"{int(seconds // 60)}m {int(seconds % 60)}s"

    def start_admission_loop(self):
        self._running = True
        t = threading.Thread(target=self._admission_loop, daemon=True)
        t.start()

    def stop(self):
        self._running = False

    def _admission_loop(self):
        while self._running:
            admitted = self.admit_batch()
            if admitted:
                print(f"  [Batch] Admitted {len(admitted)} users: {', '.join(admitted)}")
            time.sleep(self.batch_interval)


# ---------------------------------------------------------------------------
# Demo simulation
# ---------------------------------------------------------------------------

def simulate_demand():
    print("=" * 60)
    print("WAITING QUEUE - High-Demand Event Simulation")
    print("=" * 60)

    queue = WaitingQueue(
        event_id="coldplay-2026",
        batch_size=3,
        batch_interval=1.5,
        access_ttl=10.0,
    )

    # Phase 1: Users join the queue
    print("\n--- Phase 1: Users Join Queue ---")
    users = [f"user-{i}" for i in range(1, 16)]

    for user in users:
        result = queue.join(user)
        if result["position"] <= 5 or result["position"] == len(users):
            print(f"  {user} joined -> position #{result['position']} "
                  f"(wait: {result['estimated_wait']})")
    print(f"  ... ({len(users)} total users in queue)")

    # Duplicate join attempt
    dup = queue.join("user-1")
    print(f"\n  user-1 tries again -> {dup['status']} (position #{dup['position']})")

    # Phase 2: Start controlled admission
    print("\n--- Phase 2: Batch Admission (3 users every 1.5s) ---")
    queue.start_admission_loop()

    # Check positions while queue processes
    time.sleep(2)
    for check_user in ["user-1", "user-8", "user-15"]:
        pos = queue.get_position(check_user)
        print(f"  {check_user} status: {pos}")

    # Let more batches through
    time.sleep(5)

    # Phase 3: Validate access tokens
    print("\n--- Phase 3: Access Token Validation ---")
    for check_user in ["user-1", "user-5", "user-14"]:
        valid = queue.validate_access(check_user)
        print(f"  {check_user} has valid access token: {valid}")

    # Phase 4: Wait for tokens to expire and check again
    print("\n--- Phase 4: After Token Expiry ---")
    time.sleep(6)
    for check_user in ["user-1", "user-2"]:
        pos = queue.get_position(check_user)
        print(f"  {check_user} status: {pos}")

    queue.stop()

    # Final stats
    print("\n--- Queue Stats ---")
    stats = queue.stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")

    print("\n--- Key Takeaways ---")
    print("  1. Users get a position and estimated wait - better than HTTP 429")
    print("  2. Batch admission controls load on the seat service")
    print("  3. Access tokens expire - abandoned slots get recycled")
    print("  4. FIFO ordering is fair - first come, first served")


if __name__ == "__main__":
    simulate_demand()
