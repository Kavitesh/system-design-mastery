"""
Choreography vs Orchestration
==============================
Same order processing workflow implemented both ways.
Choreography: services react to events independently.
Orchestration: a central coordinator drives the workflow.

Run: python choreography_vs_orchestration.py
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Callable, Any

# ---------------------------------------------------------------------------
# Shared event infrastructure
# ---------------------------------------------------------------------------

@dataclass
class Event:
    event_type: str
    data: Dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:6])


class SimpleBus:
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
        self._log: List[str] = []

    def on(self, event_type: str, handler: Callable):
        self._handlers.setdefault(event_type, []).append(handler)

    def emit(self, event: Event):
        self._log.append(f"  -> {event.event_type}: {event.data}")
        for handler in self._handlers.get(event.event_type, []):
            handler(event)

    def print_log(self):
        for entry in self._log:
            print(entry)


# ---------------------------------------------------------------------------
# PART 1: Choreography - decentralized, services react to events
# ---------------------------------------------------------------------------

def run_choreography():
    print("\n" + "=" * 65)
    print("CHOREOGRAPHY - Services react independently to events")
    print("=" * 65)
    print("No central coordinator. Each service listens and emits.\n")

    bus = SimpleBus()
    workflow_trace = []

    def payment_service(event: Event):
        if event.event_type == "OrderPlaced":
            order_id = event.data["order_id"]
            total = event.data["total"]
            workflow_trace.append(f"PaymentService: charged ${total:.2f}")
            print(f"  [PaymentService] Charging ${total:.2f} for {order_id}")
            time.sleep(0.05)
            bus.emit(Event("PaymentCompleted", {
                "order_id": order_id, "amount": total
            }))

    def inventory_service(event: Event):
        if event.event_type == "PaymentCompleted":
            order_id = event.data["order_id"]
            workflow_trace.append("InventoryService: reserved stock")
            print(f"  [InventoryService] Reserving stock for {order_id}")
            time.sleep(0.05)
            bus.emit(Event("StockReserved", {"order_id": order_id}))

    def shipping_service(event: Event):
        if event.event_type == "StockReserved":
            order_id = event.data["order_id"]
            tracking = f"TRK-{uuid.uuid4().hex[:6].upper()}"
            workflow_trace.append(f"ShippingService: shipping {tracking}")
            print(f"  [ShippingService] Creating shipment {tracking} for {order_id}")
            time.sleep(0.05)
            bus.emit(Event("OrderShipped", {
                "order_id": order_id, "tracking": tracking
            }))

    def notification_service(event: Event):
        if event.event_type == "OrderShipped":
            tracking = event.data["tracking"]
            workflow_trace.append("NotificationService: email sent")
            print(f"  [NotificationService] Emailing customer: tracking {tracking}")

    bus.on("OrderPlaced", payment_service)
    bus.on("PaymentCompleted", inventory_service)
    bus.on("StockReserved", shipping_service)
    bus.on("OrderShipped", notification_service)

    print("  Triggering: OrderPlaced\n")
    start = time.time()
    bus.emit(Event("OrderPlaced", {
        "order_id": "ORD-C100", "customer": "alice", "total": 99.99
    }))
    elapsed = time.time() - start

    print(f"\n  Workflow completed in {elapsed*1000:.0f}ms")
    print(f"  Steps executed: {len(workflow_trace)}")
    for i, step in enumerate(workflow_trace, 1):
        print(f"    {i}. {step}")

    print("\n  Event flow (event log):")
    bus.print_log()

    print("\n  Key trait: No service knows about the full workflow.")
    print("  Each service only knows what events it cares about.")


# ---------------------------------------------------------------------------
# PART 2: Orchestration - centralized coordinator drives the workflow
# ---------------------------------------------------------------------------

class PaymentClient:
    def charge(self, order_id: str, amount: float) -> dict:
        print(f"  [PaymentClient] Charging ${amount:.2f} for {order_id}")
        time.sleep(0.05)
        return {"status": "charged", "transaction_id": f"txn-{uuid.uuid4().hex[:6]}"}


class InventoryClient:
    def reserve(self, order_id: str) -> dict:
        print(f"  [InventoryClient] Reserving stock for {order_id}")
        time.sleep(0.05)
        return {"status": "reserved"}


class ShippingClient:
    def create_shipment(self, order_id: str) -> dict:
        tracking = f"TRK-{uuid.uuid4().hex[:6].upper()}"
        print(f"  [ShippingClient] Creating shipment {tracking}")
        time.sleep(0.05)
        return {"status": "shipped", "tracking": tracking}


class NotificationClient:
    def send_email(self, customer: str, tracking: str):
        print(f"  [NotificationClient] Emailing {customer}: tracking {tracking}")


class OrderOrchestrator:
    def __init__(self):
        self.payment = PaymentClient()
        self.inventory = InventoryClient()
        self.shipping = ShippingClient()
        self.notification = NotificationClient()

    def process_order(self, order_id: str, customer: str, total: float) -> dict:
        result = {"order_id": order_id, "steps": []}

        print(f"  [Orchestrator] Starting workflow for {order_id}\n")

        pay_result = self.payment.charge(order_id, total)
        result["steps"].append(f"Payment: {pay_result['status']}")
        if pay_result["status"] != "charged":
            result["status"] = "payment_failed"
            return result

        inv_result = self.inventory.reserve(order_id)
        result["steps"].append(f"Inventory: {inv_result['status']}")
        if inv_result["status"] != "reserved":
            result["status"] = "inventory_failed"
            return result

        ship_result = self.shipping.create_shipment(order_id)
        result["steps"].append(f"Shipping: {ship_result['status']}")
        result["tracking"] = ship_result["tracking"]

        self.notification.send_email(customer, ship_result["tracking"])
        result["steps"].append("Notification: sent")

        result["status"] = "completed"
        return result


def run_orchestration():
    print("\n" + "=" * 65)
    print("ORCHESTRATION - Central coordinator drives the workflow")
    print("=" * 65)
    print("One service owns the process and calls each step.\n")

    orchestrator = OrderOrchestrator()

    start = time.time()
    result = orchestrator.process_order("ORD-O200", "bob", 149.99)
    elapsed = time.time() - start

    print(f"\n  Workflow result: {result['status']}")
    print(f"  Completed in {elapsed*1000:.0f}ms")
    print(f"  Tracking: {result.get('tracking', 'N/A')}")
    print(f"  Steps executed: {len(result['steps'])}")
    for i, step in enumerate(result["steps"], 1):
        print(f"    {i}. {step}")

    print("\n  Key trait: The orchestrator sees and controls the full workflow.")
    print("  Error handling is centralized. Easy to add rollback logic.")


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

def print_comparison():
    print("\n" + "=" * 65)
    print("COMPARISON")
    print("=" * 65)

    rows = [
        ("Coupling",        "Loose - services don't know each other",   "Tighter - orchestrator knows all services"),
        ("Visibility",      "Hard to see full flow",                    "Full flow visible in one place"),
        ("Error handling",  "Each service handles its own failures",    "Centralized rollback and retry"),
        ("Adding steps",    "Add a subscriber, no existing code changes","Modify the orchestrator"),
        ("Debugging",       "Trace events across service logs",         "Read the orchestrator logic"),
        ("Single point",    "No single coordinator to fail",            "Orchestrator is a critical path"),
        ("Best for",        "Simple, independent side effects",         "Complex, ordered, multi-step flows"),
    ]

    print(f"\n  {'Dimension':<18} {'Choreography':<42} {'Orchestration'}")
    print(f"  {'─'*18} {'─'*42} {'─'*42}")
    for dim, choreo, orch in rows:
        print(f"  {dim:<18} {choreo:<42} {orch}")

    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 65)
    print("CHOREOGRAPHY vs ORCHESTRATION")
    print("Same order workflow, two architectural approaches")
    print("=" * 65)

    run_choreography()
    run_orchestration()
    print_comparison()

    print("=" * 65)
    print("DONE - Neither is universally better. Use choreography for")
    print("independent reactions, orchestration for complex workflows.")
    print("=" * 65)


if __name__ == "__main__":
    main()
