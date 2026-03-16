"""
message_queue.py - In-Memory Message Queue
===========================================
Point-to-point message queue with producer/consumer pattern, competing
consumers, and explicit acknowledgment. Messages that aren't acknowledged
within the visibility timeout get redelivered to another consumer.

Run:
    python message_queue.py
"""

import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
#   Message and Queue
# ---------------------------------------------------------------------------

@dataclass
class Message:
    body: str
    msg_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    attempts: int = 0


class MessageQueue:
    """Thread-safe FIFO queue with visibility-timeout-based acknowledgment.

    When a consumer reads a message, the message becomes invisible to other
    consumers for `visibility_timeout` seconds. If the consumer doesn't
    acknowledge within that window, the message reappears on the queue and
    gets delivered to the next available consumer.
    """

    def __init__(self, name: str, visibility_timeout: float = 2.0):
        self.name = name
        self._queue: deque[Message] = deque()
        self._in_flight: dict[str, tuple[Message, float]] = {}
        self._visibility_timeout = visibility_timeout
        self._lock = threading.Lock()

    def put(self, body: str) -> str:
        msg = Message(body=body)
        with self._lock:
            self._queue.append(msg)
        return msg.msg_id

    def get(self) -> Message | None:
        with self._lock:
            self._requeue_expired()
            if not self._queue:
                return None
            msg = self._queue.popleft()
            msg.attempts += 1
            self._in_flight[msg.msg_id] = (msg, time.time())
            return msg

    def ack(self, msg_id: str) -> bool:
        with self._lock:
            if msg_id in self._in_flight:
                del self._in_flight[msg_id]
                return True
            return False

    def _requeue_expired(self):
        now = time.time()
        expired = [
            mid for mid, (_, ts) in self._in_flight.items()
            if now - ts > self._visibility_timeout
        ]
        for mid in expired:
            msg, _ = self._in_flight.pop(mid)
            self._queue.appendleft(msg)

    @property
    def depth(self) -> int:
        with self._lock:
            return len(self._queue)

# ---------------------------------------------------------------------------
#   Producer
# ---------------------------------------------------------------------------

def producer(queue: MessageQueue, messages: list[str]):
    for body in messages:
        msg_id = queue.put(body)
        print(f"  [producer] sent msg={msg_id}  body={body!r}")
        time.sleep(0.05)

# ---------------------------------------------------------------------------
#   Consumer
# ---------------------------------------------------------------------------

def consumer(queue: MessageQueue, consumer_id: str, count: int):
    processed = 0
    while processed < count:
        msg = queue.get()
        if msg is None:
            time.sleep(0.1)
            continue
        time.sleep(0.1)
        queue.ack(msg.msg_id)
        print(f"  [consumer-{consumer_id}] processed msg={msg.msg_id}  body={msg.body!r}  attempt={msg.attempts}")
        processed += 1

# ---------------------------------------------------------------------------
#   Demo
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("DEMO 1: Single producer, single consumer")
    print("=" * 60)

    q = MessageQueue("orders")
    tasks = ["order-1001", "order-1002", "order-1003", "order-1004"]
    producer(q, tasks)
    print()
    consumer(q, "A", len(tasks))

    print()
    print("=" * 60)
    print("DEMO 2: Competing consumers (work distribution)")
    print("=" * 60)
    print()

    q2 = MessageQueue("jobs")
    tasks2 = [f"job-{i}" for i in range(1, 7)]
    producer(q2, tasks2)
    print()

    t1 = threading.Thread(target=consumer, args=(q2, "X", 3))
    t2 = threading.Thread(target=consumer, args=(q2, "Y", 3))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    print()
    print("=" * 60)
    print("DEMO 3: Visibility timeout and redelivery")
    print("=" * 60)
    print()

    q3 = MessageQueue("retry-demo", visibility_timeout=0.3)
    q3.put("fragile-task")

    msg = q3.get()
    print(f"  [consumer-Z] received msg={msg.msg_id}  body={msg.body!r}")
    print(f"  [consumer-Z] simulating crash (no ack)...")
    time.sleep(0.5)

    msg2 = q3.get()
    if msg2:
        print(f"  [consumer-W] redelivered msg={msg2.msg_id}  body={msg2.body!r}  attempt={msg2.attempts}")
        q3.ack(msg2.msg_id)
        print(f"  [consumer-W] acknowledged successfully")


if __name__ == "__main__":
    main()
