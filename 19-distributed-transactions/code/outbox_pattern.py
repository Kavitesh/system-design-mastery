"""
Transactional Outbox Pattern
==============================
Demonstrates the dual-write problem and how the outbox pattern
solves it. Business data and event records are written in the
same database transaction, then a relay publishes from the outbox.

Run: python outbox_pattern.py
"""

import json
import sqlite3
import time
import uuid

# ---------------------------------------------------------------------------
# Database setup - orders table + outbox table in the same DB
# ---------------------------------------------------------------------------

def init_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("""CREATE TABLE orders (
        id TEXT PRIMARY KEY, customer TEXT, item TEXT,
        amount REAL, status TEXT DEFAULT 'CREATED')""")
    conn.execute("""CREATE TABLE outbox (
        id TEXT PRIMARY KEY, event_type TEXT, aggregate_id TEXT,
        payload TEXT, published INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    conn.commit()
    return conn

# ---------------------------------------------------------------------------
# Order service - atomic write of business data + outbox event
# ---------------------------------------------------------------------------

class OrderService:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create_order(self, customer: str, item: str, amount: float) -> str:
        order_id = str(uuid.uuid4())
        payload = json.dumps({"order_id": order_id, "customer": customer,
                              "item": item, "amount": amount})
        cur = self.conn.cursor()
        cur.execute("INSERT INTO orders VALUES (?,?,?,?,?)",
                    (order_id, customer, item, amount, "CREATED"))
        cur.execute("INSERT INTO outbox (id, event_type, aggregate_id, payload) VALUES (?,?,?,?)",
                    (str(uuid.uuid4()), "OrderCreated", order_id, payload))
        self.conn.commit()
        print(f"  [DB] Order {order_id[:8]} + outbox event written atomically")
        return order_id

    def update_status(self, order_id: str, new_status: str):
        payload = json.dumps({"order_id": order_id, "status": new_status})
        cur = self.conn.cursor()
        cur.execute("UPDATE orders SET status=? WHERE id=?", (new_status, order_id))
        cur.execute("INSERT INTO outbox (id, event_type, aggregate_id, payload) VALUES (?,?,?,?)",
                    (str(uuid.uuid4()), f"Order{new_status.title()}", order_id, payload))
        self.conn.commit()
        print(f"  [DB] Order {order_id[:8]} -> {new_status} + outbox event written")

# ---------------------------------------------------------------------------
# Outbox relay - polls outbox and publishes to broker
# ---------------------------------------------------------------------------

class OutboxRelay:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def poll_and_publish(self) -> int:
        cur = self.conn.cursor()
        cur.execute("SELECT id, event_type, payload FROM outbox WHERE published=0 ORDER BY created_at")
        rows = cur.fetchall()
        for eid, etype, payload in rows:
            data = json.loads(payload)
            print(f"  [Relay] Publishing {etype} -> {json.dumps(data)[:80]}")
            cur.execute("UPDATE outbox SET published=1 WHERE id=?", (eid,))
        self.conn.commit()
        return len(rows)

# ---------------------------------------------------------------------------
# Demonstrate the problem and solution
# ---------------------------------------------------------------------------

def show_dual_write_problem():
    print(f"\n{'='*60}")
    print("PROBLEM: The Dual-Write Issue")
    print(f"{'='*60}\n")
    print("  Without the outbox pattern:\n")
    print("    1. Write order to database     -> SUCCESS")
    print("    2. Publish event to Kafka       -> NETWORK ERROR\n")
    print("  Result: Order exists but downstream services never")
    print("  hear about it. Payment never charged.\n")
    print("  Or reversed:\n")
    print("    1. Publish event to Kafka       -> SUCCESS")
    print("    2. Write order to database      -> DB CRASH\n")
    print("  Result: Downstream processes a non-existent order.")

def show_outbox_solution():
    print(f"\n{'='*60}")
    print("SOLUTION: Transactional Outbox Pattern")
    print(f"{'='*60}\n")

    conn = init_db()
    svc = OrderService(conn)
    relay = OutboxRelay(conn)

    print("--- Step 1: Create orders (atomic data + event writes) ---\n")
    id1 = svc.create_order("Alice", "Laptop", 1299.99)
    id2 = svc.create_order("Bob", "Monitor", 449.99)
    svc.update_status(id1, "CONFIRMED")

    print(f"\n--- Step 2: Outbox table contents ---\n")
    cur = conn.cursor()
    cur.execute("SELECT id, event_type, aggregate_id, published FROM outbox")
    print(f"  {'Event ID':<12} {'Type':<20} {'Order':<12} {'Sent'}")
    print(f"  {'-'*50}")
    for eid, etype, aid, pub in cur.fetchall():
        print(f"  {eid[:10]:<12} {etype:<20} {aid[:10]:<12} {'Yes' if pub else 'No'}")

    print(f"\n--- Step 3: Relay publishes events from outbox ---\n")
    count = relay.poll_and_publish()
    print(f"\n  Published {count} events")

    print(f"\n--- Step 4: Verify outbox is drained ---\n")
    cur.execute("SELECT SUM(published), COUNT(*) FROM outbox")
    published, total = cur.fetchone()
    print(f"  Published: {published}/{total}, Remaining: {total - published}")
    conn.close()


def main():
    print("Transactional Outbox Pattern Simulation")
    show_dual_write_problem()
    show_outbox_solution()

    print(f"\n{'='*60}")
    print("KEY TAKEAWAY: The outbox table lives in the same database")
    print("as your business data. One atomic transaction writes both.")
    print("A separate relay publishes events. You trade exactly-once")
    print("for at-least-once - fine if consumers are idempotent.")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
