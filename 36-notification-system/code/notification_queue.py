"""
Notification Priority Queue
============================
Demonstrates a multi-priority notification queue with exponential backoff
retry logic. Notifications are sorted by priority, then by timestamp.
Failed deliveries are re-enqueued with increasing delay.

Run the simulation:
    python notification_queue.py
"""

import heapq
import time
import random
from dataclasses import dataclass, field
from enum import IntEnum


# ---------------------------------------------------------------------------
# Priority levels
# ---------------------------------------------------------------------------

class Priority(IntEnum):
    CRITICAL = 0   # OTP codes, security alerts
    HIGH = 1       # Payment confirmation, chat messages
    NORMAL = 2     # Social updates, order status
    LOW = 3        # Marketing, weekly digest


PRIORITY_LABELS = {
    Priority.CRITICAL: "CRITICAL",
    Priority.HIGH: "HIGH",
    Priority.NORMAL: "NORMAL",
    Priority.LOW: "LOW",
}

PRIORITY_SLA = {
    Priority.CRITICAL: "< 1 second",
    Priority.HIGH: "< 10 seconds",
    Priority.NORMAL: "< 5 minutes",
    Priority.LOW: "< 1 hour",
}


# ---------------------------------------------------------------------------
# Notification item
# ---------------------------------------------------------------------------

@dataclass(order=True)
class QueueItem:
    priority: int
    scheduled_at: float
    notif_id: str = field(compare=False)
    user_id: str = field(compare=False)
    channel: str = field(compare=False)
    message: str = field(compare=False)
    retry_count: int = field(default=0, compare=False)
    max_retries: int = field(default=4, compare=False)
    created_at: float = field(default_factory=time.time, compare=False)


# ---------------------------------------------------------------------------
# Priority queue
# ---------------------------------------------------------------------------

class NotificationQueue:
    def __init__(self, failure_rate=0.3):
        self._heap = []
        self._processed = 0
        self._delivered = 0
        self._failed_permanent = 0
        self._retried = 0
        self._failure_rate = failure_rate

    def enqueue(self, item):
        heapq.heappush(self._heap, item)

    def size(self):
        return len(self._heap)

    def process_next(self):
        if not self._heap:
            return None

        item = heapq.heappop(self._heap)
        now = time.time()

        if item.scheduled_at > now:
            heapq.heappush(self._heap, item)
            return None

        self._processed += 1
        label = PRIORITY_LABELS[item.priority]
        success = random.random() > self._failure_rate

        if success:
            self._delivered += 1
            latency = now - item.created_at
            print(f"  [DELIVERED] {label:8s} | {item.channel:5s} | {item.notif_id} | "
                  f"user={item.user_id} | latency={latency:.3f}s | \"{item.message}\"")
            return {"status": "delivered", "item": item}

        if item.retry_count >= item.max_retries:
            self._failed_permanent += 1
            print(f"  [FAILED]    {label:8s} | {item.channel:5s} | {item.notif_id} | "
                  f"user={item.user_id} | exhausted {item.max_retries} retries")
            return {"status": "failed", "item": item}

        delay = (2 ** item.retry_count) + random.uniform(0, 2 ** item.retry_count * 0.5)
        item.retry_count += 1
        item.scheduled_at = now + delay
        self._retried += 1
        print(f"  [RETRY {item.retry_count}/{item.max_retries}]  {label:8s} | {item.channel:5s} | "
              f"{item.notif_id} | next attempt in {delay:.1f}s")
        heapq.heappush(self._heap, item)
        return {"status": "retrying", "item": item}

    def drain(self, max_iterations=200):
        """Process all items until the queue is empty or max iterations reached."""
        iterations = 0
        while self._heap and iterations < max_iterations:
            result = self.process_next()
            if result is None:
                min_wait = self._heap[0].scheduled_at - time.time() if self._heap else 0
                if min_wait > 0.01:
                    time.sleep(min(min_wait, 0.05))
            iterations += 1

    def stats(self):
        return {
            "processed": self._processed,
            "delivered": self._delivered,
            "failed": self._failed_permanent,
            "retried": self._retried,
            "remaining": len(self._heap),
            "delivery_rate": f"{self._delivered / max(self._processed, 1) * 100:.1f}%",
        }


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

def run_simulation():
    print("=" * 72)
    print("NOTIFICATION PRIORITY QUEUE - SIMULATION")
    print("=" * 72)

    print("\nPriority Levels:")
    for p in Priority:
        print(f"  P{p.value} {PRIORITY_LABELS[p]:10s} - SLA: {PRIORITY_SLA[p]}")

    queue = NotificationQueue(failure_rate=0.3)
    now = time.time()

    test_notifications = [
        (Priority.LOW,      "email", "u_010", "Weekly digest ready"),
        (Priority.LOW,      "email", "u_011", "New items on sale"),
        (Priority.NORMAL,   "push",  "u_005", "Alice liked your post"),
        (Priority.NORMAL,   "push",  "u_006", "Order #1234 shipped"),
        (Priority.NORMAL,   "email", "u_007", "Bob commented on your photo"),
        (Priority.HIGH,     "push",  "u_003", "Payment of $49.99 received"),
        (Priority.HIGH,     "sms",   "u_004", "Your ride is arriving"),
        (Priority.CRITICAL, "sms",   "u_001", "Your OTP code is 847293"),
        (Priority.CRITICAL, "email", "u_002", "Suspicious login detected"),
    ]

    print(f"\nEnqueueing {len(test_notifications)} notifications (out of priority order)...\n")
    for priority, channel, user_id, message in test_notifications:
        item = QueueItem(
            priority=priority,
            scheduled_at=now,
            notif_id=f"n_{random.randint(1000, 9999)}",
            user_id=user_id,
            channel=channel,
            message=message,
        )
        queue.enqueue(item)

    print("Processing queue (highest priority first):\n")
    queue.drain(max_iterations=100)

    print("\n" + "-" * 72)
    print("RESULTS")
    print("-" * 72)
    s = queue.stats()
    for key, val in s.items():
        print(f"  {key:15s}: {val}")

    print("\nKey observations:")
    print("  - CRITICAL notifications processed before LOW, regardless of enqueue order")
    print("  - Failed deliveries retried with exponential backoff + jitter")
    print(f"  - {s['retried']} retries needed to achieve {s['delivery_rate']} delivery rate")
    print("  - In production, separate physical queues per priority prevent starvation")


if __name__ == "__main__":
    run_simulation()
