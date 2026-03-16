"""
API Gateway Demo
=================
A simple API gateway that sits in front of the microservices. It handles:
  - Request routing (path-based)
  - Response aggregation (combine data from multiple services)
  - Basic error handling when downstream services are unavailable

This is what tools like Kong, Zuul, or AWS API Gateway do in production.

Run (requires all three microservices running):
  python microservices/user_service.py     # port 5001
  python microservices/product_service.py  # port 5002
  python microservices/order_service.py    # port 5003
  python api_gateway_demo.py              # port 5000

Endpoints:
  GET  /api/users/*          - Proxied to user service
  GET  /api/products/*       - Proxied to product service
  POST /api/orders           - Proxied to order service
  GET  /api/dashboard/<uid>  - Aggregated: user + orders + product catalog
  GET  /api/health           - Aggregated health from all services
"""

import time
import requests as http_client
from flask import Flask, jsonify, request, Response

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Service registry - hardcoded here, dynamic in service_discovery.py
# ---------------------------------------------------------------------------

SERVICES = {
    "users":    "http://localhost:5001",
    "products": "http://localhost:5002",
    "orders":   "http://localhost:5003",
}

TIMEOUT = 2

# ---------------------------------------------------------------------------
# Proxy helper
# ---------------------------------------------------------------------------

def proxy_request(service_name, path):
    """Forward the current request to a downstream service."""
    base_url = SERVICES[service_name]
    url = f"{base_url}{path}"
    try:
        resp = http_client.request(
            method=request.method,
            url=url,
            json=request.get_json(silent=True),
            timeout=TIMEOUT,
        )
        return Response(resp.content, status=resp.status_code, content_type="application/json")
    except http_client.ConnectionError:
        return jsonify({"error": f"{service_name} service unavailable"}), 503


# ---------------------------------------------------------------------------
# Proxy routes - gateway forwards requests to the right service
# ---------------------------------------------------------------------------

@app.route("/api/users", defaults={"path": ""}, methods=["GET", "POST"])
@app.route("/api/users/<path:path>", methods=["GET"])
def proxy_users(path):
    return proxy_request("users", f"/users/{path}" if path else "/users")


@app.route("/api/products", defaults={"path": ""}, methods=["GET", "POST"])
@app.route("/api/products/<path:path>", methods=["GET"])
def proxy_products(path):
    return proxy_request("products", f"/products/{path}" if path else "/products")


@app.route("/api/orders", methods=["GET", "POST"])
@app.route("/api/orders/<path:path>", methods=["GET"])
def proxy_orders(path=""):
    return proxy_request("orders", f"/orders/{path}" if path else "/orders")


# ---------------------------------------------------------------------------
# Aggregation - the gateway's real power
# ---------------------------------------------------------------------------

@app.route("/api/dashboard/<int:user_id>")
def user_dashboard(user_id):
    """
    Aggregate data from multiple services into one response.
    Without a gateway, the client would make 3 separate API calls.
    """
    result = {"user": None, "orders": [], "products": [], "errors": []}

    try:
        resp = http_client.get(f"{SERVICES['users']}/users/{user_id}", timeout=TIMEOUT)
        result["user"] = resp.json() if resp.status_code == 200 else None
        if resp.status_code == 404:
            return jsonify({"error": "User not found"}), 404
    except http_client.ConnectionError:
        result["errors"].append("user-service unavailable")

    try:
        resp = http_client.get(f"{SERVICES['orders']}/orders/user/{user_id}", timeout=TIMEOUT)
        result["orders"] = resp.json() if resp.status_code == 200 else []
    except http_client.ConnectionError:
        result["errors"].append("order-service unavailable")

    try:
        resp = http_client.get(f"{SERVICES['products']}/products", timeout=TIMEOUT)
        result["products"] = resp.json() if resp.status_code == 200 else []
    except http_client.ConnectionError:
        result["errors"].append("product-service unavailable")

    result["aggregated_at"] = time.time()
    result["served_by"] = "api-gateway"
    return jsonify(result)


# ---------------------------------------------------------------------------
# Aggregated health check
# ---------------------------------------------------------------------------

@app.route("/api/health")
def gateway_health():
    """Check all downstream services and report aggregate health."""
    statuses = {}
    for name, url in SERVICES.items():
        try:
            resp = http_client.get(f"{url}/health", timeout=1)
            statuses[name] = resp.json() if resp.status_code == 200 else {"status": "error"}
        except http_client.ConnectionError:
            statuses[name] = {"status": "unreachable"}

    all_healthy = all(s.get("status") == "healthy" for s in statuses.values())
    return jsonify({
        "gateway": "api-gateway",
        "status": "healthy" if all_healthy else "degraded",
        "services": statuses,
        "checked_at": time.time(),
    })


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("API Gateway starting on port 5000")
    print("  Routes:  /api/users -> :5001  /api/products -> :5002  /api/orders -> :5003")
    print("  Aggregation: /api/dashboard/<user_id>  /api/health")
    app.run(port=5000, debug=False)
