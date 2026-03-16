"""
Saga Choreography Pattern
===========================
Event-driven saga where services react to events published
by other services. No central coordinator - each service
decides what to do based on events it receives.

Run: python saga_choreography.py
"""

import time
import uuid
from collections import defaultdict

# ---------------------------------------------------------------------------
# Simple in-process event bus
# ---------------------------------------------------------------------------

class EventBus:
    def __init__(self):
        self._handlers = defaultdict(list)
        self._log = []

    def subscribe(self, event_type: str, handler):
        self._handlers[event_type].append(handler)

    def publish(self, event_type: str, data: dict):
        self._log.append(event_type)
        print(f"  >> EVENT: {event_type}")
        time.sleep(0.03)
        for handler in self._handlers.get(event_type, []):
            handler(data)

    def print_log(self):
        print(f"\n  Event Log ({len(self._log)} events):")
        for i, e in enumerate(self._log, 1):
            print(f"    {i}. {e}")

# ---------------------------------------------------------------------------
# Services - subscribe to events, publish outcomes
# ---------------------------------------------------------------------------

class OrderService:
    def __init__(self, bus: EventBus):
        self.bus = bus
        self.orders = {}
        bus.subscribe("PaymentCompleted", self._on_paid)
        bus.subscribe("PaymentFailed", self._on_fail)
        bus.subscribe("ShipmentScheduled", self._on_shipped)
        bus.subscribe("InventoryFailed", self._on_fail)

    def create_order(self, order_id: str, item: str, amount: float):
        self.orders[order_id] = {"item": item, "amount": amount, "status": "CREATED"}
        print(f"  [Order] Created {order_id[:8]}: {item} ${amount}")
        self.bus.publish("OrderCreated", {"order_id": order_id, "item": item, "amount": amount})

    def _on_paid(self, data):
        self.orders[data["order_id"]]["status"] = "PAID"
        print(f"  [Order] {data['order_id'][:8]} marked PAID")

    def _on_shipped(self, data):
        self.orders[data["order_id"]]["status"] = "SHIPPING"
        print(f"  [Order] {data['order_id'][:8]} marked SHIPPING")

    def _on_fail(self, data):
        self.orders[data["order_id"]]["status"] = "CANCELLED"
        print(f"  [Order] {data['order_id'][:8]} CANCELLED")

class PaymentService:
    def __init__(self, bus: EventBus, should_fail=False):
        self.bus, self.should_fail, self.payments = bus, should_fail, {}
        bus.subscribe("OrderCreated", self._on_order)
        bus.subscribe("InventoryFailed", self._on_inventory_fail)

    def _on_order(self, data):
        oid = data["order_id"]
        print(f"  [Payment] Charging ${data['amount']} for {oid[:8]}...")
        if self.should_fail:
            print(f"  [Payment] Declined for {oid[:8]}")
            self.bus.publish("PaymentFailed", {"order_id": oid})
        else:
            self.payments[oid] = data["amount"]
            print(f"  [Payment] ${data['amount']} charged successfully")
            self.bus.publish("PaymentCompleted", data)

    def _on_inventory_fail(self, data):
        oid = data["order_id"]
        if oid in self.payments:
            print(f"  [Payment] Refunding ${self.payments[oid]} for {oid[:8]}")
            self.bus.publish("PaymentRefunded", {"order_id": oid})

class InventoryService:
    def __init__(self, bus: EventBus, stock: int = 10):
        self.bus, self.stock = bus, stock
        bus.subscribe("PaymentCompleted", self._on_paid)

    def _on_paid(self, data):
        oid = data["order_id"]
        print(f"  [Inventory] Checking stock for '{data['item']}' ({self.stock} left)")
        if self.stock <= 0:
            print(f"  [Inventory] Out of stock for {oid[:8]}")
            self.bus.publish("InventoryFailed", {"order_id": oid})
        else:
            self.stock -= 1
            print(f"  [Inventory] Reserved '{data['item']}' ({self.stock} left)")
            self.bus.publish("InventoryReserved", data)

class ShippingService:
    def __init__(self, bus: EventBus):
        self.bus = bus
        bus.subscribe("InventoryReserved", self._on_reserved)

    def _on_reserved(self, data):
        oid = data["order_id"]
        tracking = f"TRACK-{oid[:6].upper()}"
        print(f"  [Shipping] Scheduled shipment - tracking {tracking}")
        self.bus.publish("ShipmentScheduled", {"order_id": oid, "tracking": tracking})

# ---------------------------------------------------------------------------
# Run scenarios
# ---------------------------------------------------------------------------

def run_scenario(title: str, payment_fail=False, stock=10):
    print(f"\n{'='*60}")
    print(f"SCENARIO: {title}")
    print(f"{'='*60}\n")

    bus = EventBus()
    order_svc = OrderService(bus)
    PaymentService(bus, should_fail=payment_fail)
    InventoryService(bus, stock=stock)
    ShippingService(bus)

    order_id = str(uuid.uuid4())
    order_svc.create_order(order_id, "Mechanical Keyboard", 149.99)
    bus.print_log()
    print(f"\n  Final order status: {order_svc.orders[order_id]['status']}")


def main():
    print("Saga Choreography - Event-Driven Order Processing")
    run_scenario("Successful order flow")
    run_scenario("Payment fails - order cancelled", payment_fail=True)
    run_scenario("Out of stock - payment refunded", stock=0)

    print(f"\n{'='*60}")
    print("KEY TAKEAWAY: No central coordinator. Each service reacts")
    print("to events and publishes its own. The flow is implicit in")
    print("the event subscriptions. Simple to extend, but harder to")
    print("trace when things go wrong.")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
