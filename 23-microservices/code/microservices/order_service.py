"""
Order Service (Microservice)
=============================
Handles order placement. Depends on user_service and product_service via
HTTP calls - not shared memory, not a shared database. This is the key
difference from the monolith: cross-service operations require network calls.

Run (requires user_service and product_service running):
  python user_service.py     # port 5001
  python product_service.py  # port 5002
  python order_service.py    # port 5003

Endpoints:
  POST /orders             - Place an order (calls user + product services)
  GET  /orders             - List all orders
  GET  /orders/<user_id>   - Get orders for a user
  GET  /health             - Health check for service discovery
"""

import time
import requests as http_client
from flask import Flask, jsonify, request

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Service URLs - in production, these come from service discovery
# ---------------------------------------------------------------------------

USER_SERVICE = "http://localhost:5001"
PRODUCT_SERVICE = "http://localhost:5002"

# ---------------------------------------------------------------------------
# Order service owns only order data
# ---------------------------------------------------------------------------

ORDERS = []
NEXT_ID = 1


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/orders", methods=["POST"])
def create_order():
    """
    Place an order. This is where microservices get real:
    - Call user service to validate the user exists
    - Call product service to reserve stock
    - If either fails, the order fails
    - In the monolith, these were just dictionary lookups
    """
    global NEXT_ID
    data = request.json
    user_id = data["user_id"]
    product_id = data["product_id"]
    quantity = data.get("quantity", 1)

    # Step 1: Validate user exists (network call instead of dict lookup)
    try:
        resp = http_client.get(f"{USER_SERVICE}/users/{user_id}", timeout=2)
        if resp.status_code == 404:
            return jsonify({"error": "User not found", "source": "user-service"}), 404
        user = resp.json()
    except http_client.ConnectionError:
        return jsonify({"error": "User service unavailable"}), 503

    # Step 2: Reserve product stock (network call + stock decrement)
    try:
        resp = http_client.post(
            f"{PRODUCT_SERVICE}/products/{product_id}/reserve",
            json={"quantity": quantity},
            timeout=2,
        )
        if resp.status_code == 404:
            return jsonify({"error": "Product not found", "source": "product-service"}), 404
        if resp.status_code == 400:
            return jsonify(resp.json()), 400
        reservation = resp.json()
    except http_client.ConnectionError:
        return jsonify({"error": "Product service unavailable"}), 503

    # Step 3: Create the order in our own data store
    order = {
        "id": NEXT_ID,
        "user_id": user_id,
        "user_name": user["name"],
        "product_id": product_id,
        "quantity": quantity,
        "unit_price": reservation["unit_price"],
        "total": reservation["unit_price"] * quantity,
        "created_at": time.time(),
    }
    ORDERS.append(order)
    NEXT_ID += 1

    return jsonify(order), 201


@app.route("/orders")
def list_orders():
    return jsonify(ORDERS)


@app.route("/orders/user/<int:user_id>")
def get_user_orders(user_id):
    user_orders = [o for o in ORDERS if o["user_id"] == user_id]
    return jsonify(user_orders)


@app.route("/health")
def health():
    user_ok = False
    product_ok = False
    try:
        user_ok = http_client.get(f"{USER_SERVICE}/health", timeout=1).status_code == 200
    except http_client.ConnectionError:
        pass
    try:
        product_ok = http_client.get(f"{PRODUCT_SERVICE}/health", timeout=1).status_code == 200
    except http_client.ConnectionError:
        pass

    status = "healthy" if (user_ok and product_ok) else "degraded"
    return jsonify({
        "service": "order-service",
        "status": status,
        "dependencies": {"user-service": user_ok, "product-service": product_ok},
        "orders_count": len(ORDERS),
    })


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Order service starting on port 5003")
    app.run(port=5003, debug=False)
