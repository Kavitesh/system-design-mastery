"""
Monolith E-Commerce App
=======================
A single Flask app handling users, products, and orders - all in one process,
one database, one deployment. This is how most apps should start.

Run:
  python monolith_app.py

Endpoints:
  POST /users              - Create a user
  GET  /users/<id>         - Get user details
  POST /products           - Create a product
  GET  /products           - List all products
  POST /orders             - Place an order (validates user + product + stock)
  GET  /orders/<user_id>   - Get orders for a user
  GET  /stats              - System-wide stats
"""

import time
from flask import Flask, jsonify, request

app = Flask(__name__)

# ---------------------------------------------------------------------------
# In-memory "database" - shared across all modules (that's the point)
# ---------------------------------------------------------------------------

DB = {
    "users": {},
    "products": {},
    "orders": [],
    "next_user_id": 1,
    "next_product_id": 1,
    "next_order_id": 1,
}


def seed_data():
    DB["users"] = {
        1: {"id": 1, "name": "Alice", "email": "alice@example.com", "created_at": time.time()},
        2: {"id": 2, "name": "Bob", "email": "bob@example.com", "created_at": time.time()},
    }
    DB["products"] = {
        1: {"id": 1, "name": "Mechanical Keyboard", "price": 89.99, "stock": 50},
        2: {"id": 2, "name": "USB-C Monitor", "price": 349.99, "stock": 20},
        3: {"id": 3, "name": "Standing Desk", "price": 599.99, "stock": 10},
    }
    DB["next_user_id"] = 3
    DB["next_product_id"] = 4


# ---------------------------------------------------------------------------
# User routes
# ---------------------------------------------------------------------------

@app.route("/users", methods=["POST"])
def create_user():
    data = request.json
    uid = DB["next_user_id"]
    DB["next_user_id"] += 1
    user = {"id": uid, "name": data["name"], "email": data["email"], "created_at": time.time()}
    DB["users"][uid] = user
    return jsonify(user), 201


@app.route("/users/<int:user_id>")
def get_user(user_id):
    user = DB["users"].get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user)


# ---------------------------------------------------------------------------
# Product routes
# ---------------------------------------------------------------------------

@app.route("/products", methods=["POST"])
def create_product():
    data = request.json
    pid = DB["next_product_id"]
    DB["next_product_id"] += 1
    product = {"id": pid, "name": data["name"], "price": data["price"], "stock": data.get("stock", 0)}
    DB["products"][pid] = product
    return jsonify(product), 201


@app.route("/products")
def list_products():
    return jsonify(list(DB["products"].values()))


# ---------------------------------------------------------------------------
# Order routes - this is where the monolith shines: direct data access
# ---------------------------------------------------------------------------

@app.route("/orders", methods=["POST"])
def create_order():
    data = request.json
    user_id = data["user_id"]
    product_id = data["product_id"]
    quantity = data.get("quantity", 1)

    user = DB["users"].get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    product = DB["products"].get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404

    if product["stock"] < quantity:
        return jsonify({"error": f"Insufficient stock. Available: {product['stock']}"}), 400

    product["stock"] -= quantity

    oid = DB["next_order_id"]
    DB["next_order_id"] += 1
    order = {
        "id": oid,
        "user_id": user_id,
        "user_name": user["name"],
        "product_id": product_id,
        "product_name": product["name"],
        "quantity": quantity,
        "total": product["price"] * quantity,
        "created_at": time.time(),
    }
    DB["orders"].append(order)
    return jsonify(order), 201


@app.route("/orders/<int:user_id>")
def get_user_orders(user_id):
    user_orders = [o for o in DB["orders"] if o["user_id"] == user_id]
    return jsonify(user_orders)


# ---------------------------------------------------------------------------
# Stats - trivial in a monolith, painful in microservices
# ---------------------------------------------------------------------------

@app.route("/stats")
def stats():
    total_revenue = sum(o["total"] for o in DB["orders"])
    return jsonify({
        "total_users": len(DB["users"]),
        "total_products": len(DB["products"]),
        "total_orders": len(DB["orders"]),
        "total_revenue": round(total_revenue, 2),
        "architecture": "monolith - all data in one place",
    })


# ---------------------------------------------------------------------------
# Demo runner
# ---------------------------------------------------------------------------

def run_demo():
    """Demonstrate the monolith by simulating requests."""
    print("\n=== Monolith E-Commerce Demo ===\n")
    seed_data()

    with app.test_client() as client:
        print("[Users] Listing seeded users...")
        for uid in [1, 2]:
            resp = client.get(f"/users/{uid}")
            u = resp.get_json()
            print(f"  User {u['id']}: {u['name']} ({u['email']})")

        print("\n[Products] Current catalog:")
        resp = client.get("/products")
        for p in resp.get_json():
            print(f"  #{p['id']} {p['name']} - ${p['price']} (stock: {p['stock']})")

        print("\n[Orders] Alice buys 2 Mechanical Keyboards...")
        resp = client.post("/orders", json={"user_id": 1, "product_id": 1, "quantity": 2})
        order = resp.get_json()
        print(f"  Order #{order['id']}: {order['quantity']}x {order['product_name']} = ${order['total']}")

        print("\n[Orders] Bob buys 1 Standing Desk...")
        resp = client.post("/orders", json={"user_id": 2, "product_id": 3, "quantity": 1})
        order = resp.get_json()
        print(f"  Order #{order['id']}: {order['quantity']}x {order['product_name']} = ${order['total']}")

        print("\n[Orders] Alice tries to buy 100 Monitors (should fail)...")
        resp = client.post("/orders", json={"user_id": 1, "product_id": 2, "quantity": 100})
        print(f"  Result: {resp.get_json()['error']}")

        print("\n[Stats] System overview:")
        resp = client.get("/stats")
        stats = resp.get_json()
        for k, v in stats.items():
            print(f"  {k}: {v}")

        print("\n[Key insight] Everything shares memory - no network calls,")
        print("  no serialization, no eventual consistency. Just function calls.")
        print("  This is why monoliths are fast and simple.\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    if "--serve" in sys.argv:
        seed_data()
        print("Monolith server starting on port 5000")
        app.run(port=5000, debug=False)
    else:
        run_demo()
