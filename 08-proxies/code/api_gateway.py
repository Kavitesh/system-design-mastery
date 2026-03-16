"""
api_gateway.py
==============
An API gateway built on Flask that demonstrates three core gateway concerns:
path-based routing to different backend services, token-based authentication,
and per-client rate limiting using a token bucket algorithm.

Requests without a valid Bearer token get a 401. Requests that exceed the
rate limit (5 requests per 10-second window) get a 429. Valid requests are
routed to the appropriate backend service based on the URL path prefix.

Usage:
    python api_gateway.py

Starts two backend services (users on 6010, orders on 6011) and the gateway
on port 5050. Send requests to http://localhost:5050 with header
"Authorization: Bearer secret-token-123".
"""

import threading
import time
from collections import defaultdict

from flask import Flask, Response, jsonify, request
import requests as http_client

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

VALID_TOKENS = {"secret-token-123", "admin-token-456"}

RATE_LIMIT = 5
RATE_WINDOW = 10

ROUTES = {
    "/api/users": "http://127.0.0.1:6010",
    "/api/orders": "http://127.0.0.1:6011",
}

# ---------------------------------------------------------------------------
# Rate limiter - fixed window per client IP
# ---------------------------------------------------------------------------

class RateLimiter:
    """Fixed-window rate limiter keyed by client IP. Thread-safe through the
    GIL for counter increments, which is sufficient for a demo."""

    def __init__(self, limit, window_seconds):
        self.limit = limit
        self.window = window_seconds
        self.counters = defaultdict(lambda: {"count": 0, "reset_at": 0.0})

    def allow(self, client_ip):
        now = time.time()
        entry = self.counters[client_ip]
        if now >= entry["reset_at"]:
            entry["count"] = 0
            entry["reset_at"] = now + self.window
        entry["count"] += 1
        remaining = max(0, self.limit - entry["count"])
        return entry["count"] <= self.limit, remaining, entry["reset_at"]


rate_limiter = RateLimiter(RATE_LIMIT, RATE_WINDOW)

# ---------------------------------------------------------------------------
# Backend service factories
# ---------------------------------------------------------------------------

def create_user_service():
    app = Flask("user_service")
    users = {"1": "Alice", "2": "Bob", "3": "Carol"}

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def handle(path):
        user_id = path.strip("/") if path else None
        if user_id and user_id in users:
            return {"service": "users", "user_id": user_id, "name": users[user_id]}
        return {"service": "users", "users": users}

    return app


def create_order_service():
    app = Flask("order_service")
    orders = {"101": {"item": "Laptop", "total": 999}, "102": {"item": "Mouse", "total": 25}}

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def handle(path):
        order_id = path.strip("/") if path else None
        if order_id and order_id in orders:
            return {"service": "orders", "order_id": order_id, **orders[order_id]}
        return {"service": "orders", "orders": orders}

    return app


# ---------------------------------------------------------------------------
# API Gateway
# ---------------------------------------------------------------------------

gateway = Flask("api_gateway")


@gateway.route("/", defaults={"path": ""}, methods=["GET", "POST", "PUT", "DELETE"])
@gateway.route("/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
def handle_request(path):
    full_path = f"/{path}"

    # --- Authentication ---
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"error": "missing Bearer token"}), 401
    token = auth[len("Bearer "):]
    if token not in VALID_TOKENS:
        return jsonify({"error": "invalid token"}), 401

    # --- Rate limiting ---
    client_ip = request.remote_addr
    allowed, remaining, reset_at = rate_limiter.allow(client_ip)
    if not allowed:
        resp = jsonify({"error": "rate limit exceeded", "retry_after_seconds": round(reset_at - time.time(), 1)})
        resp.status_code = 429
        resp.headers["Retry-After"] = str(int(reset_at - time.time()))
        resp.headers["X-RateLimit-Remaining"] = "0"
        print(f"[gateway] RATE LIMITED {client_ip} on {full_path}")
        return resp

    # --- Routing ---
    target = None
    strip_prefix = ""
    for prefix, backend_url in ROUTES.items():
        if full_path.startswith(prefix):
            target = backend_url
            strip_prefix = prefix
            break

    if not target:
        return jsonify({"error": "no route matched", "path": full_path}), 404

    backend_path = full_path[len(strip_prefix):]
    url = f"{target}{backend_path}"

    try:
        resp = http_client.request(
            method=request.method,
            url=url,
            timeout=5,
        )
        print(f"[gateway] {request.method} {full_path} -> {target} | {resp.status_code} | remaining={remaining}")

        response = Response(resp.content, status=resp.status_code)
        response.headers["Content-Type"] = resp.headers.get("Content-Type", "application/json")
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response

    except http_client.exceptions.RequestException as exc:
        print(f"[gateway] {full_path} -> {target} FAILED: {exc}")
        return jsonify({"error": "service unavailable"}), 502


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

def run_app(app, port):
    app.run(port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    threading.Thread(target=run_app, args=(create_user_service(), 6010), daemon=True).start()
    threading.Thread(target=run_app, args=(create_order_service(), 6011), daemon=True).start()

    time.sleep(1)
    print("API Gateway running on http://localhost:5050")
    gateway.run(port=5050, debug=False, use_reloader=False)
