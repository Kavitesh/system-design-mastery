"""
Product Service (Microservice)
===============================
Owns the product catalog and inventory. The order service calls this API
to check stock and decrement inventory - it never touches our database.

Run:
  python product_service.py

Endpoints:
  POST /products              - Create a product
  GET  /products              - List all products
  GET  /products/<id>         - Get product by ID
  POST /products/<id>/reserve - Reserve stock (called by order service)
  GET  /health                - Health check for service discovery
"""

import time
from flask import Flask, jsonify, request

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Product service owns its own data store
# ---------------------------------------------------------------------------

PRODUCTS = {}
NEXT_ID = 1


def seed():
    global NEXT_ID
    PRODUCTS[1] = {"id": 1, "name": "Mechanical Keyboard", "price": 89.99, "stock": 50}
    PRODUCTS[2] = {"id": 2, "name": "USB-C Monitor", "price": 349.99, "stock": 20}
    PRODUCTS[3] = {"id": 3, "name": "Standing Desk", "price": 599.99, "stock": 10}
    NEXT_ID = 4


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/products", methods=["POST"])
def create_product():
    global NEXT_ID
    data = request.json
    product = {"id": NEXT_ID, "name": data["name"], "price": data["price"], "stock": data.get("stock", 0)}
    PRODUCTS[NEXT_ID] = product
    NEXT_ID += 1
    return jsonify(product), 201


@app.route("/products")
def list_products():
    return jsonify(list(PRODUCTS.values()))


@app.route("/products/<int:product_id>")
def get_product(product_id):
    product = PRODUCTS.get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    return jsonify(product)


@app.route("/products/<int:product_id>/reserve", methods=["POST"])
def reserve_stock(product_id):
    """Called by order service to atomically check and decrement stock."""
    product = PRODUCTS.get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404

    quantity = request.json.get("quantity", 1)
    if product["stock"] < quantity:
        return jsonify({
            "error": "Insufficient stock",
            "available": product["stock"],
            "requested": quantity,
        }), 400

    product["stock"] -= quantity
    return jsonify({
        "product_id": product_id,
        "reserved": quantity,
        "remaining_stock": product["stock"],
        "unit_price": product["price"],
    })


@app.route("/health")
def health():
    return jsonify({"service": "product-service", "status": "healthy", "products_count": len(PRODUCTS)})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    seed()
    print("Product service starting on port 5002")
    app.run(port=5002, debug=False)
