"""
CQRS Demo
=========
Command Query Responsibility Segregation with separate write model
(normalized, consistent) and read models (denormalized, fast).
Projections transform write-side events into read-optimized views.

Run: python cqrs_demo.py
"""

import uuid
import time
from dataclasses import dataclass, field
from typing import Dict, List, Any
from collections import defaultdict

# ---------------------------------------------------------------------------
# Write Model - normalized, enforces business rules
# ---------------------------------------------------------------------------

@dataclass
class WriteEvent:
    event_type: str
    data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])


class WriteModel:
    def __init__(self):
        self._products: Dict[str, dict] = {}
        self._orders: Dict[str, dict] = {}
        self._events: List[WriteEvent] = []

    def add_product(self, product_id: str, name: str, price: float, stock: int):
        if product_id in self._products:
            raise ValueError(f"Product {product_id} already exists")
        self._products[product_id] = {"name": name, "price": price, "stock": stock}
        event = WriteEvent("ProductAdded", {
            "product_id": product_id, "name": name, "price": price, "stock": stock
        })
        self._events.append(event)
        return event

    def place_order(self, customer: str, items: List[dict]):
        order_id = f"ORD-{str(uuid.uuid4())[:6]}"

        for item in items:
            product = self._products.get(item["product_id"])
            if not product:
                raise ValueError(f"Product {item['product_id']} not found")
            if product["stock"] < item["qty"]:
                raise ValueError(f"Not enough stock for {product['name']}")

        total = 0.0
        for item in items:
            product = self._products[item["product_id"]]
            product["stock"] -= item["qty"]
            total += product["price"] * item["qty"]

        self._orders[order_id] = {
            "customer": customer, "items": items,
            "total": total, "status": "confirmed"
        }

        event = WriteEvent("OrderPlaced", {
            "order_id": order_id, "customer": customer,
            "items": items, "total": total
        })
        self._events.append(event)
        return event

    def get_new_events(self, after_index: int) -> List[WriteEvent]:
        return self._events[after_index:]

    @property
    def event_count(self) -> int:
        return len(self._events)


# ---------------------------------------------------------------------------
# Read Models - denormalized views optimized for specific queries
# ---------------------------------------------------------------------------

class ProductCatalogView:
    """Read model: fast product lookups with availability info."""
    def __init__(self):
        self.products: Dict[str, dict] = {}

    def handle_event(self, event: WriteEvent):
        if event.event_type == "ProductAdded":
            d = event.data
            self.products[d["product_id"]] = {
                "name": d["name"], "price": d["price"],
                "stock": d["stock"], "available": d["stock"] > 0
            }
        elif event.event_type == "OrderPlaced":
            for item in event.data["items"]:
                pid = item["product_id"]
                if pid in self.products:
                    self.products[pid]["stock"] -= item["qty"]
                    self.products[pid]["available"] = self.products[pid]["stock"] > 0

    def query_all(self) -> List[dict]:
        return [{"id": k, **v} for k, v in self.products.items()]

    def query_available(self) -> List[dict]:
        return [{"id": k, **v} for k, v in self.products.items() if v["available"]]


class CustomerOrderView:
    """Read model: orders grouped by customer for account pages."""
    def __init__(self):
        self.orders_by_customer: Dict[str, List[dict]] = defaultdict(list)
        self.customer_totals: Dict[str, float] = defaultdict(float)

    def handle_event(self, event: WriteEvent):
        if event.event_type == "OrderPlaced":
            d = event.data
            self.orders_by_customer[d["customer"]].append({
                "order_id": d["order_id"], "total": d["total"],
                "item_count": sum(i["qty"] for i in d["items"])
            })
            self.customer_totals[d["customer"]] += d["total"]

    def query_customer(self, customer: str) -> dict:
        orders = self.orders_by_customer.get(customer, [])
        return {
            "customer": customer,
            "order_count": len(orders),
            "total_spent": self.customer_totals.get(customer, 0),
            "orders": orders
        }


class SalesDashboardView:
    """Read model: aggregate sales stats for dashboards."""
    def __init__(self):
        self.total_revenue = 0.0
        self.order_count = 0
        self.product_sales: Dict[str, int] = defaultdict(int)

    def handle_event(self, event: WriteEvent):
        if event.event_type == "OrderPlaced":
            self.total_revenue += event.data["total"]
            self.order_count += 1
            for item in event.data["items"]:
                self.product_sales[item["product_id"]] += item["qty"]

    def query_summary(self) -> dict:
        return {
            "total_revenue": self.total_revenue,
            "order_count": self.order_count,
            "avg_order_value": self.total_revenue / max(self.order_count, 1),
            "top_products": sorted(
                self.product_sales.items(), key=lambda x: x[1], reverse=True
            )
        }


# ---------------------------------------------------------------------------
# Projection Engine - feeds events from write model into read models
# ---------------------------------------------------------------------------

class ProjectionEngine:
    def __init__(self, write_model: WriteModel):
        self._write_model = write_model
        self._views: List = []
        self._last_index = 0

    def register(self, view):
        self._views.append(view)

    def sync(self):
        new_events = self._write_model.get_new_events(self._last_index)
        for event in new_events:
            for view in self._views:
                view.handle_event(event)
        count = len(new_events)
        self._last_index = self._write_model.event_count
        return count


# ---------------------------------------------------------------------------
# Main demo
# ---------------------------------------------------------------------------

def main():
    print("=" * 65)
    print("CQRS DEMO - Separate Write and Read Models")
    print("=" * 65)

    write = WriteModel()
    catalog_view = ProductCatalogView()
    customer_view = CustomerOrderView()
    sales_view = SalesDashboardView()

    projector = ProjectionEngine(write)
    projector.register(catalog_view)
    projector.register(customer_view)
    projector.register(sales_view)

    # --- Commands: write side ---
    print("\n1. COMMANDS (Write Side)")
    print("-" * 50)

    write.add_product("SKU-KB", "Mechanical Keyboard", 129.99, 50)
    write.add_product("SKU-MS", "Wireless Mouse", 49.99, 100)
    write.add_product("SKU-HD", "USB-C Hub", 34.99, 30)
    write.add_product("SKU-MN", "4K Monitor", 399.99, 10)
    print(f"  Added 4 products to write model")

    write.place_order("alice", [
        {"product_id": "SKU-KB", "qty": 1},
        {"product_id": "SKU-MS", "qty": 2}
    ])
    write.place_order("bob", [
        {"product_id": "SKU-MN", "qty": 1},
        {"product_id": "SKU-HD", "qty": 1}
    ])
    write.place_order("alice", [
        {"product_id": "SKU-HD", "qty": 3},
        {"product_id": "SKU-MS", "qty": 1}
    ])
    print(f"  Placed 3 orders")
    print(f"  Write model has {write.event_count} events pending projection")

    # --- Sync projections ---
    print("\n2. PROJECTING EVENTS INTO READ MODELS")
    print("-" * 50)
    synced = projector.sync()
    print(f"  Projected {synced} events into 3 read models")

    # --- Query: Product Catalog View ---
    print("\n3. QUERY: Product Catalog (Read Model 1)")
    print("-" * 50)
    print(f"  {'Product':<25} {'Price':>8} {'Stock':>6} {'Available'}")
    print(f"  {'─'*25} {'─'*8} {'─'*6} {'─'*9}")
    for p in catalog_view.query_all():
        avail = "Yes" if p["available"] else "SOLD OUT"
        print(f"  {p['name']:<25} ${p['price']:>7.2f} {p['stock']:>5}  {avail}")

    print(f"\n  Available products: {len(catalog_view.query_available())} of {len(catalog_view.query_all())}")

    # --- Query: Customer Order View ---
    print("\n4. QUERY: Customer Orders (Read Model 2)")
    print("-" * 50)
    for customer in ["alice", "bob"]:
        data = customer_view.query_customer(customer)
        print(f"  {customer.upper()}: {data['order_count']} orders, ${data['total_spent']:.2f} total")
        for o in data["orders"]:
            print(f"    - {o['order_id']}: ${o['total']:.2f} ({o['item_count']} items)")

    # --- Query: Sales Dashboard View ---
    print("\n5. QUERY: Sales Dashboard (Read Model 3)")
    print("-" * 50)
    summary = sales_view.query_summary()
    print(f"  Total Revenue:     ${summary['total_revenue']:.2f}")
    print(f"  Total Orders:      {summary['order_count']}")
    print(f"  Avg Order Value:   ${summary['avg_order_value']:.2f}")
    print(f"  Units Sold by SKU:")
    for sku, qty in summary["top_products"]:
        print(f"    {sku}: {qty} units")

    # --- Demonstrate write/read independence ---
    print("\n6. WRITE AND READ ARE INDEPENDENT")
    print("-" * 50)
    write.place_order("carol", [{"product_id": "SKU-MN", "qty": 2}])
    print(f"  New order placed. Write model event count: {write.event_count}")

    stale_summary = sales_view.query_summary()
    print(f"  Read model (before sync): {stale_summary['order_count']} orders, ${stale_summary['total_revenue']:.2f}")

    synced = projector.sync()
    print(f"  Synced {synced} new event(s)")

    fresh_summary = sales_view.query_summary()
    print(f"  Read model (after sync):  {fresh_summary['order_count']} orders, ${fresh_summary['total_revenue']:.2f}")
    print(f"  Read model lags until projections run. This is eventual consistency.")

    print("\n" + "=" * 65)
    print("DONE - Write model handles commands. Read models serve queries.")
    print("Each read model is shaped for its consumer. No compromises.")
    print("=" * 65)


if __name__ == "__main__":
    main()
