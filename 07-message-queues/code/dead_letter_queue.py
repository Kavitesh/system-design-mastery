"""
dead_letter_queue.py - Retry Logic and Dead Letter Queues
==========================================================
Demonstrates what happens when messages can't be processed. Failed messages
are retried with exponential backoff. After exhausting retries, they move to
a dead letter queue for inspection and eventual replay.

Run:
    python dead_letter_queue.py
"""

import time
import uuid
from collections import deque
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
#   Message
# ---------------------------------------------------------------------------

@dataclass
class Message:
    body: dict
    msg_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    attempts: int = 0
    last_error: str = ""
    created_at: float = field(default_factory=time.time)

# ---------------------------------------------------------------------------
#   Reliable Queue with DLQ
# ---------------------------------------------------------------------------

class ReliableQueue:
    """Message queue with built-in retry logic and dead letter routing.

    When a consumer reports a processing failure, the queue checks the
    message's attempt count. If retries remain, the message goes back on
    the main queue after a backoff delay. If max retries are exhausted,
    the message moves to the dead letter queue.
    """

    def __init__(self, name: str, max_retries: int = 3, base_backoff: float = 0.1):
        self.name = name
        self.max_retries = max_retries
        self.base_backoff = base_backoff
        self._queue: deque[Message] = deque()
        self._dlq: list[Message] = []
        self._processed: list[Message] = []

    def enqueue(self, body: dict) -> str:
        msg = Message(body=body)
        self._queue.append(msg)
        return msg.msg_id

    def dequeue(self) -> Message | None:
        if not self._queue:
            return None
        return self._queue.popleft()

    def ack(self, msg: Message):
        self._processed.append(msg)

    def nack(self, msg: Message, error: str):
        msg.attempts += 1
        msg.last_error = error

        if msg.attempts >= self.max_retries:
            self._dlq.append(msg)
            print(f"    -> moved to DLQ after {msg.attempts} attempts: {error}")
            return

        backoff = self.base_backoff * (2 ** (msg.attempts - 1))
        print(f"    -> retry {msg.attempts}/{self.max_retries} (backoff {backoff:.2f}s): {error}")
        time.sleep(backoff)
        self._queue.appendleft(msg)

    @property
    def dlq_messages(self) -> list[Message]:
        return list(self._dlq)

    @property
    def dlq_depth(self) -> int:
        return len(self._dlq)

    @property
    def processed_count(self) -> int:
        return len(self._processed)

    def replay_dlq(self):
        count = len(self._dlq)
        for msg in self._dlq:
            msg.attempts = 0
            msg.last_error = ""
            self._queue.append(msg)
        self._dlq.clear()
        return count

# ---------------------------------------------------------------------------
#   Message Processor
# ---------------------------------------------------------------------------

class OrderProcessor:
    """Simulates a consumer that fails on specific message types. Orders
    with negative quantities or missing fields trigger processing errors.
    """

    def process(self, msg: Message) -> tuple[bool, str]:
        body = msg.body

        if "order_id" not in body:
            return False, "missing order_id field"

        if body.get("quantity", 0) < 0:
            return False, f"invalid quantity: {body['quantity']}"

        if body.get("total", 0) > 10000:
            return False, f"amount {body['total']} exceeds fraud threshold"

        return True, "ok"

# ---------------------------------------------------------------------------
#   Demo
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("DEMO 1: Mixed messages - some succeed, some fail")
    print("=" * 60)
    print()

    q = ReliableQueue("orders", max_retries=3, base_backoff=0.05)
    processor = OrderProcessor()

    orders = [
        {"order_id": "ord-1001", "item": "laptop", "quantity": 1, "total": 999},
        {"order_id": "ord-1002", "item": "phone", "quantity": -1, "total": 599},
        {"order_id": "ord-1003", "item": "tablet", "quantity": 2, "total": 450},
        {"item": "mystery", "quantity": 1, "total": 100},
        {"order_id": "ord-1005", "item": "watch", "quantity": 1, "total": 15000},
        {"order_id": "ord-1006", "item": "mouse", "quantity": 3, "total": 75},
    ]

    for order in orders:
        q.enqueue(order)
    print(f"  enqueued {len(orders)} messages\n")

    round_num = 0
    while True:
        msg = q.dequeue()
        if msg is None:
            break
        round_num += 1
        label = msg.body.get("order_id", "unknown")
        print(f"  [{round_num}] processing {label} (attempt {msg.attempts + 1})...")
        success, error = processor.process(msg)
        if success:
            q.ack(msg)
            print(f"    -> success")
        else:
            q.nack(msg, error)

    print()
    print(f"  results: {q.processed_count} processed, {q.dlq_depth} in DLQ")

    print()
    print("=" * 60)
    print("DEMO 2: Inspecting the dead letter queue")
    print("=" * 60)
    print()

    for msg in q.dlq_messages:
        print(f"  msg={msg.msg_id}  attempts={msg.attempts}  error={msg.last_error!r}")
        print(f"    body={msg.body}")
    print()

    print("=" * 60)
    print("DEMO 3: Replaying DLQ after fixing the processor")
    print("=" * 60)
    print()

    class LenientProcessor:
        def process(self, msg: Message) -> tuple[bool, str]:
            body = msg.body
            if "order_id" not in body:
                body["order_id"] = f"auto-{msg.msg_id}"
            if body.get("quantity", 0) < 0:
                body["quantity"] = abs(body["quantity"])
            return True, "ok (fixed)"

    count = q.replay_dlq()
    print(f"  replayed {count} messages from DLQ back to main queue")
    print()

    fixed_processor = LenientProcessor()
    while True:
        msg = q.dequeue()
        if msg is None:
            break
        label = msg.body.get("order_id", "unknown")
        print(f"  processing {label}...")
        success, error = fixed_processor.process(msg)
        if success:
            q.ack(msg)
            print(f"    -> {error}")
        else:
            q.nack(msg, error)

    print()
    print(f"  final: {q.processed_count} processed, {q.dlq_depth} in DLQ")


if __name__ == "__main__":
    main()
