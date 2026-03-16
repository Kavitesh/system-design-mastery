"""
SQL Demo - Relational Databases in Action
==========================================
Builds an e-commerce schema in SQLite, populates it with data,
runs JOIN queries, and demonstrates ACID transaction guarantees
with commit and rollback.

Run: python sql_demo.py
"""

import sqlite3
import os

DB_FILE = "ecommerce_demo.db"


# ---------------------------------------------------------------------------
# Schema and seed data
# ---------------------------------------------------------------------------

def init_db(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE users (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            name  TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE
        );
        CREATE TABLE products (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            name  TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE orders (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL REFERENCES users(id),
            total      REAL NOT NULL,
            status     TEXT NOT NULL DEFAULT 'pending',
            ordered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE order_items (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id   INTEGER NOT NULL REFERENCES orders(id),
            product_id INTEGER NOT NULL REFERENCES products(id),
            quantity   INTEGER NOT NULL,
            price      REAL NOT NULL
        );
    """)

    conn.executemany("INSERT INTO users (name, email) VALUES (?, ?)", [
        ("Alice", "alice@example.com"),
        ("Bob", "bob@example.com"),
        ("Charlie", "charlie@example.com"),
    ])
    conn.executemany("INSERT INTO products (name, price, stock) VALUES (?, ?, ?)", [
        ("Laptop", 999.99, 50),
        ("Mechanical Keyboard", 149.99, 200),
        ("Monitor", 399.99, 75),
        ("USB-C Hub", 49.99, 500),
    ])

    cur = conn.cursor()
    cur.execute("INSERT INTO orders (user_id, total, status) VALUES (1, 1149.98, 'completed')")
    oid = cur.lastrowid
    cur.executemany("INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (?,?,?,?)", [
        (oid, 1, 1, 999.99), (oid, 2, 1, 149.99),
    ])
    cur.execute("INSERT INTO orders (user_id, total, status) VALUES (2, 99.98, 'completed')")
    oid = cur.lastrowid
    cur.execute("INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (?,?,?,?)",
                (oid, 4, 2, 49.99))
    conn.commit()


# ---------------------------------------------------------------------------
# JOIN queries - the real power of relational databases
# ---------------------------------------------------------------------------

def demo_joins(conn: sqlite3.Connection):
    print("=" * 60)
    print("JOIN QUERIES")
    print("=" * 60)
    cur = conn.cursor()

    print("\nOrder details (3-table JOIN):")
    for row in cur.execute("""
        SELECT u.name, p.name, oi.quantity, oi.price
        FROM order_items oi
        JOIN orders o   ON oi.order_id   = o.id
        JOIN users u    ON o.user_id     = u.id
        JOIN products p ON oi.product_id = p.id
        ORDER BY u.name
    """):
        print(f"  {row[0]} bought {row[2]}x {row[1]} @ ${row[3]:.2f}")

    print("\nRevenue per product (JOIN + GROUP BY):")
    for row in cur.execute("""
        SELECT p.name, SUM(oi.quantity * oi.price) as revenue
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        GROUP BY p.name ORDER BY revenue DESC
    """):
        print(f"  {row[0]:.<30} ${row[1]:.2f}")

    print("\nCustomers with no orders (LEFT JOIN):")
    for row in cur.execute("""
        SELECT u.name FROM users u
        LEFT JOIN orders o ON u.id = o.user_id
        WHERE o.id IS NULL
    """):
        print(f"  {row[0]} - has never ordered")


# ---------------------------------------------------------------------------
# ACID transaction demo
# ---------------------------------------------------------------------------

def demo_acid(conn: sqlite3.Connection):
    print("\n" + "=" * 60)
    print("ACID TRANSACTION DEMO")
    print("=" * 60)
    cur = conn.cursor()

    cur.execute("SELECT stock FROM products WHERE id = 1")
    stock_before = cur.fetchone()[0]
    print(f"\nLaptop stock before purchase: {stock_before}")

    print("Purchasing 1 laptop for Charlie (atomic: debit stock + create order)...")
    try:
        cur.execute("UPDATE products SET stock = stock - 1 WHERE id = 1")
        cur.execute("INSERT INTO orders (user_id, total, status) VALUES (3, 999.99, 'completed')")
        oid = cur.lastrowid
        cur.execute("INSERT INTO order_items (order_id,product_id,quantity,price) VALUES (?,?,?,?)",
                    (oid, 1, 1, 999.99))
        conn.commit()
        print("COMMITTED - all three writes succeeded together.")
    except Exception as e:
        conn.rollback()
        print(f"ROLLED BACK - nothing changed. Error: {e}")

    cur.execute("SELECT stock FROM products WHERE id = 1")
    print(f"Laptop stock after purchase: {cur.fetchone()[0]}")

    print(f"\nAttempting to buy 9999 laptops (more than stock)...")
    try:
        cur.execute("UPDATE products SET stock = stock - 9999 WHERE id = 1")
        new_stock = cur.execute("SELECT stock FROM products WHERE id = 1").fetchone()[0]
        if new_stock < 0:
            raise ValueError(f"Insufficient stock (would go to {new_stock})")
        conn.commit()
    except (ValueError, Exception) as e:
        conn.rollback()
        print(f"ROLLED BACK: {e}")

    final = cur.execute("SELECT stock FROM products WHERE id = 1").fetchone()[0]
    print(f"Stock unchanged after rollback: {final}")
    print("\nACID guarantees the database is never left in a partial state.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)

    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON")

    init_db(conn)
    demo_joins(conn)
    demo_acid(conn)

    conn.close()
    os.remove(DB_FILE)
    print("\nCleaned up - database file removed.")


if __name__ == "__main__":
    main()
