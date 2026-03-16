"""
pub_sub.py - Publish/Subscribe Messaging
==========================================
Topic-based pub/sub broker with fan-out delivery. Publishers send messages
to named topics. Every subscriber on a topic receives its own copy of every
message - subscribers are independent and don't compete.

Run:
    python pub_sub.py
"""

import time
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable

# ---------------------------------------------------------------------------
#   Message and Broker
# ---------------------------------------------------------------------------

@dataclass
class PubSubMessage:
    topic: str
    body: dict
    timestamp: float = field(default_factory=time.time)


class PubSubBroker:
    """In-memory pub/sub broker with topic-based routing.

    Subscribers register a callback function for a topic. When a message
    is published, the broker invokes every subscriber's callback with a
    copy of the message. Delivery is synchronous within the publish call
    for simplicity, but each subscriber runs in its own thread.
    """

    def __init__(self):
        self._subscribers: dict[str, dict[str, Callable]] = defaultdict(dict)
        self._lock = threading.Lock()
        self._stats: dict[str, int] = defaultdict(int)

    def subscribe(self, topic: str, subscriber_id: str, callback: Callable):
        with self._lock:
            self._subscribers[topic][subscriber_id] = callback
        print(f"  [{subscriber_id}] subscribed to '{topic}'")

    def unsubscribe(self, topic: str, subscriber_id: str):
        with self._lock:
            self._subscribers[topic].pop(subscriber_id, None)
        print(f"  [{subscriber_id}] unsubscribed from '{topic}'")

    def publish(self, topic: str, body: dict):
        msg = PubSubMessage(topic=topic, body=body)
        with self._lock:
            subs = dict(self._subscribers.get(topic, {}))
        self._stats[topic] += 1

        if not subs:
            print(f"  [broker] no subscribers for '{topic}' - message dropped")
            return

        threads = []
        for sub_id, callback in subs.items():
            t = threading.Thread(target=callback, args=(sub_id, msg))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()

    def topic_stats(self) -> dict[str, int]:
        return dict(self._stats)

# ---------------------------------------------------------------------------
#   Subscriber Handlers
# ---------------------------------------------------------------------------

def email_handler(sub_id: str, msg: PubSubMessage):
    time.sleep(0.05)
    print(f"  [{sub_id}] sending email for: {msg.body}")


def analytics_handler(sub_id: str, msg: PubSubMessage):
    time.sleep(0.03)
    print(f"  [{sub_id}] recording analytics: {msg.body}")


def audit_handler(sub_id: str, msg: PubSubMessage):
    time.sleep(0.02)
    print(f"  [{sub_id}] audit log entry: {msg.body}")


def inventory_handler(sub_id: str, msg: PubSubMessage):
    time.sleep(0.04)
    print(f"  [{sub_id}] updating inventory: {msg.body}")

# ---------------------------------------------------------------------------
#   Demo
# ---------------------------------------------------------------------------

def main():
    broker = PubSubBroker()

    print("=" * 60)
    print("DEMO 1: Fan-out - one event, multiple subscribers")
    print("=" * 60)
    print()

    broker.subscribe("user.signup", "email-service", email_handler)
    broker.subscribe("user.signup", "analytics", analytics_handler)
    broker.subscribe("user.signup", "audit-log", audit_handler)
    print()

    print("  [publisher] publishing user.signup event...")
    broker.publish("user.signup", {"user_id": "u-42", "email": "alice@example.com"})
    print()

    print("=" * 60)
    print("DEMO 2: Multiple topics, selective subscription")
    print("=" * 60)
    print()

    broker.subscribe("order.created", "email-service", email_handler)
    broker.subscribe("order.created", "inventory", inventory_handler)
    broker.subscribe("order.created", "analytics", analytics_handler)
    print()

    print("  [publisher] publishing order.created event...")
    broker.publish("order.created", {"order_id": "ord-1001", "item": "keyboard", "qty": 2})
    print()

    print("=" * 60)
    print("DEMO 3: Unsubscribe and dynamic routing")
    print("=" * 60)
    print()

    broker.unsubscribe("user.signup", "analytics")
    print()

    print("  [publisher] publishing user.signup (analytics unsubscribed)...")
    broker.publish("user.signup", {"user_id": "u-43", "email": "bob@example.com"})
    print()

    print("=" * 60)
    print("DEMO 4: No subscribers - message dropped")
    print("=" * 60)
    print()

    print("  [publisher] publishing payment.failed (no subscribers)...")
    broker.publish("payment.failed", {"payment_id": "pay-999"})
    print()

    print("=" * 60)
    print("DEMO 5: Burst publishing")
    print("=" * 60)
    print()

    for i in range(1, 4):
        broker.publish("order.created", {"order_id": f"ord-200{i}", "item": f"item-{i}", "qty": i})
    print()

    stats = broker.topic_stats()
    print("  [broker] message counts by topic:")
    for topic, count in sorted(stats.items()):
        print(f"    {topic}: {count} messages published")


if __name__ == "__main__":
    main()
