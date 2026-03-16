"""
Event Bus
=========
In-memory publish/subscribe event bus with event history and replay.
Demonstrates decoupled communication between producers and consumers.

Run: python event_bus.py
"""

import uuid
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Any
from datetime import datetime

# ---------------------------------------------------------------------------
# Event definition
# ---------------------------------------------------------------------------

@dataclass
class Event:
    event_type: str
    data: Dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: float = field(default_factory=time.time)
    source: str = "unknown"

    def __str__(self):
        ts = datetime.fromtimestamp(self.timestamp).strftime("%H:%M:%S.%f")[:-3]
        return f"[{ts}] {self.event_type} (id={self.event_id}) from {self.source}"


# ---------------------------------------------------------------------------
# Event Bus - publish, subscribe, history, replay
# ---------------------------------------------------------------------------

class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._history: List[Event] = []
        self._processed_ids: set = set()

    def subscribe(self, event_type: str, handler: Callable):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        print(f"  Subscribed {handler.__name__} to '{event_type}'")

    def publish(self, event: Event):
        self._history.append(event)
        handlers = self._subscribers.get(event.event_type, [])
        print(f"\n  Published: {event}")
        print(f"  Delivering to {len(handlers)} handler(s)...")
        for handler in handlers:
            handler(event)

    def history(self, event_type: str = None) -> List[Event]:
        if event_type:
            return [e for e in self._history if e.event_type == event_type]
        return list(self._history)

    def replay(self, event_type: str = None, since: float = 0):
        events = [
            e for e in self._history
            if (event_type is None or e.event_type == event_type)
            and e.timestamp >= since
        ]
        print(f"\n  Replaying {len(events)} event(s)...")
        for event in events:
            handlers = self._subscribers.get(event.event_type, [])
            for handler in handlers:
                handler(event)


# ---------------------------------------------------------------------------
# Idempotent handler wrapper
# ---------------------------------------------------------------------------

class IdempotentHandler:
    def __init__(self, name: str, handler: Callable):
        self.__name__ = name
        self._handler = handler
        self._seen: set = set()

    def __call__(self, event: Event):
        if event.event_id in self._seen:
            print(f"    [{self.__name__}] SKIPPED duplicate event {event.event_id}")
            return
        self._seen.add(event.event_id)
        self._handler(event)


# ---------------------------------------------------------------------------
# Demo handlers
# ---------------------------------------------------------------------------

def payment_handler(event: Event):
    order_id = event.data.get("order_id", "?")
    total = event.data.get("total", 0)
    print(f"    [PaymentService] Charging ${total:.2f} for order {order_id}")


def inventory_handler(event: Event):
    items = event.data.get("items", [])
    print(f"    [InventoryService] Reserving stock for {len(items)} item(s): {items}")


def email_handler(event: Event):
    customer = event.data.get("customer", "?")
    print(f"    [EmailService] Sending confirmation to {customer}")


def analytics_handler(event: Event):
    print(f"    [Analytics] Recorded event: {event.event_type}")


# ---------------------------------------------------------------------------
# Main demo
# ---------------------------------------------------------------------------

def main():
    print("=" * 65)
    print("EVENT BUS DEMO - Publish/Subscribe with History and Replay")
    print("=" * 65)

    bus = EventBus()

    # --- Subscribe handlers ---
    print("\n1. SUBSCRIBING HANDLERS")
    print("-" * 40)
    bus.subscribe("OrderPlaced", payment_handler)
    bus.subscribe("OrderPlaced", inventory_handler)
    bus.subscribe("OrderPlaced", email_handler)
    bus.subscribe("PaymentReceived", analytics_handler)

    # --- Publish events ---
    print("\n2. PUBLISHING EVENTS")
    print("-" * 40)

    bus.publish(Event(
        event_type="OrderPlaced",
        data={"order_id": "ORD-001", "customer": "alice@test.com",
              "total": 149.99, "items": ["Keyboard", "Mouse"]},
        source="order-service"
    ))

    time.sleep(0.01)

    bus.publish(Event(
        event_type="PaymentReceived",
        data={"order_id": "ORD-001", "amount": 149.99, "method": "credit_card"},
        source="payment-service"
    ))

    time.sleep(0.01)

    bus.publish(Event(
        event_type="OrderPlaced",
        data={"order_id": "ORD-002", "customer": "bob@test.com",
              "total": 49.99, "items": ["USB Cable"]},
        source="order-service"
    ))

    # --- Event history ---
    print("\n3. EVENT HISTORY")
    print("-" * 40)
    all_events = bus.history()
    print(f"  Total events recorded: {len(all_events)}")
    for e in all_events:
        print(f"    {e}")

    order_events = bus.history("OrderPlaced")
    print(f"\n  OrderPlaced events only: {len(order_events)}")

    # --- Adding a late subscriber and replaying ---
    print("\n4. LATE SUBSCRIBER + REPLAY")
    print("-" * 40)
    print("  A new analytics service comes online and needs to catch up...")
    bus.subscribe("OrderPlaced", analytics_handler)
    bus.replay("OrderPlaced")

    # --- Idempotent handler demo ---
    print("\n5. IDEMPOTENT HANDLER DEMO")
    print("-" * 40)
    safe_payment = IdempotentHandler("SafePayment", payment_handler)
    bus2 = EventBus()
    bus2.subscribe("OrderPlaced", safe_payment)

    duplicate_event = Event(
        event_type="OrderPlaced",
        data={"order_id": "ORD-003", "customer": "carol@test.com",
              "total": 299.99, "items": ["Monitor"]},
        source="order-service"
    )

    print("  Publishing same event 3 times (simulating redelivery)...")
    bus2.publish(duplicate_event)
    bus2.publish(duplicate_event)
    bus2.publish(duplicate_event)
    print("  Result: Processed once, skipped twice. Idempotency works.")

    print("\n" + "=" * 65)
    print("DONE - The event bus decouples producers from consumers.")
    print("Add new subscribers anytime. Replay history to catch up.")
    print("=" * 65)


if __name__ == "__main__":
    main()
