"""
Graceful Degradation
=====================
A Flask app that keeps serving requests when backend dependencies
fail. Instead of returning 500 errors, it falls back to cached data,
default values, and reduced functionality.

Kill individual services via /fail/<service> endpoints and watch the
product API degrade step by step instead of crashing outright.

Run: python graceful_degradation.py
"""

import time
import random
from flask import Flask, jsonify


app = Flask(__name__)


# ---------------------------------------------------------------------------
# Simulated backend services
# ---------------------------------------------------------------------------

class BackendService:
    def __init__(self, name: str, healthy: bool = True):
        self.name = name
        self.healthy = healthy
        self.call_count = 0
        self.failure_count = 0

    def call(self, fallback=None):
        self.call_count += 1
        if not self.healthy:
            self.failure_count += 1
            if fallback is not None:
                return fallback
            raise ServiceUnavailableError(f"{self.name} is down")
        return None

    def kill(self):
        self.healthy = False

    def recover(self):
        self.healthy = True


class ServiceUnavailableError(Exception):
    pass


# ---------------------------------------------------------------------------
# Backend services with their data
# ---------------------------------------------------------------------------

recommendation_svc = BackendService("recommendation-service")
inventory_svc = BackendService("inventory-service")
pricing_svc = BackendService("pricing-service")
review_svc = BackendService("review-service")

ALL_SERVICES = {
    "recommend": recommendation_svc,
    "inventory": inventory_svc,
    "pricing": pricing_svc,
    "review": review_svc,
}

PRODUCT_CATALOG = [
    {"id": 1, "name": "Wireless Keyboard", "category": "electronics"},
    {"id": 2, "name": "Standing Desk", "category": "furniture"},
    {"id": 3, "name": "Noise-Canceling Headphones", "category": "electronics"},
    {"id": 4, "name": "Ergonomic Mouse", "category": "electronics"},
    {"id": 5, "name": "Monitor Light Bar", "category": "accessories"},
]

CACHED_PRICES = {1: 49.99, 2: 399.99, 3: 249.99, 4: 34.99, 5: 54.99}
CACHED_STOCK = {1: True, 2: True, 3: True, 4: False, 5: True}
POPULAR_PRODUCTS = [1, 3, 5]


def get_recommendations(user_id: int) -> list[int]:
    recommendation_svc.call()
    seed = user_id * 7 % len(PRODUCT_CATALOG)
    return [PRODUCT_CATALOG[(seed + i) % len(PRODUCT_CATALOG)]["id"] for i in range(3)]


def get_inventory(product_id: int) -> dict:
    inventory_svc.call()
    stock = random.randint(0, 50)
    return {"in_stock": stock > 0, "quantity": stock}


def get_price(product_id: int) -> dict:
    pricing_svc.call()
    base = CACHED_PRICES.get(product_id, 29.99)
    dynamic = round(base * random.uniform(0.95, 1.10), 2)
    return {"price": dynamic, "currency": "USD", "dynamic": True}


def get_reviews(product_id: int) -> dict:
    review_svc.call()
    return {
        "average_rating": round(random.uniform(3.5, 5.0), 1),
        "review_count": random.randint(10, 500),
        "sentiment": "positive",
    }


# ---------------------------------------------------------------------------
# Product API with graceful degradation
# ---------------------------------------------------------------------------

@app.route("/products")
def list_products():
    degraded_features = []
    products = []

    for product in PRODUCT_CATALOG:
        item = {"id": product["id"], "name": product["name"]}

        try:
            price_data = get_price(product["id"])
            item["price"] = price_data["price"]
            item["price_source"] = "live"
        except ServiceUnavailableError:
            item["price"] = CACHED_PRICES.get(product["id"], "unavailable")
            item["price_source"] = "cached"
            if "pricing" not in degraded_features:
                degraded_features.append("pricing")

        try:
            stock = get_inventory(product["id"])
            item["in_stock"] = stock["in_stock"]
            item["quantity"] = stock["quantity"]
            item["stock_source"] = "live"
        except ServiceUnavailableError:
            item["in_stock"] = CACHED_STOCK.get(product["id"], "unknown")
            item["quantity"] = "unknown"
            item["stock_source"] = "cached"
            if "inventory" not in degraded_features:
                degraded_features.append("inventory")

        try:
            reviews = get_reviews(product["id"])
            item["rating"] = reviews["average_rating"]
            item["review_count"] = reviews["review_count"]
        except ServiceUnavailableError:
            item["rating"] = "unavailable"
            item["review_count"] = "unavailable"
            if "reviews" not in degraded_features:
                degraded_features.append("reviews")

        products.append(item)

    try:
        rec_ids = get_recommendations(user_id=42)
        recommended = [p["name"] for p in PRODUCT_CATALOG if p["id"] in rec_ids]
    except ServiceUnavailableError:
        recommended = [p["name"] for p in PRODUCT_CATALOG if p["id"] in POPULAR_PRODUCTS]
        degraded_features.append("recommendations")

    status = "full" if not degraded_features else "degraded"
    return jsonify({
        "status": status,
        "degraded_features": degraded_features,
        "products": products,
        "recommended": recommended,
        "note": f"Serving with {len(degraded_features)} degraded feature(s)" if degraded_features else "All systems operational",
    })


# ---------------------------------------------------------------------------
# Service control endpoints
# ---------------------------------------------------------------------------

@app.route("/fail/<service_name>")
def fail_service(service_name):
    svc = ALL_SERVICES.get(service_name)
    if not svc:
        return jsonify({"error": f"Unknown service. Options: {list(ALL_SERVICES.keys())}"}), 404
    svc.kill()
    return jsonify({"action": "killed", "service": svc.name})


@app.route("/recover/<service_name>")
def recover_service(service_name):
    if service_name == "all":
        for svc in ALL_SERVICES.values():
            svc.recover()
        return jsonify({"action": "recovered", "services": [s.name for s in ALL_SERVICES.values()]})
    svc = ALL_SERVICES.get(service_name)
    if not svc:
        return jsonify({"error": f"Unknown service. Options: {list(ALL_SERVICES.keys())}"}), 404
    svc.recover()
    return jsonify({"action": "recovered", "service": svc.name})


@app.route("/status")
def service_status():
    statuses = {}
    for key, svc in ALL_SERVICES.items():
        statuses[svc.name] = {
            "healthy": svc.healthy,
            "calls": svc.call_count,
            "failures": svc.failure_count,
            "failure_rate": f"{(svc.failure_count/svc.call_count*100):.1f}%" if svc.call_count > 0 else "0%",
        }
    healthy_count = sum(1 for s in ALL_SERVICES.values() if s.healthy)
    return jsonify({
        "overall": f"{healthy_count}/{len(ALL_SERVICES)} services healthy",
        "services": statuses,
    })


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Graceful Degradation Demo - http://localhost:5014")
    app.run(port=5014, debug=False)
