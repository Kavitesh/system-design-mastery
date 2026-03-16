"""
Serverless API - Flask as Independent Functions
=================================================
Each route is an independent function handler, mimicking how serverless
APIs work. Functions are isolated, stateless, and individually deployable.

Usage:
    python serverless_api.py
    # Then: curl http://localhost:5000/api/users
"""

import time
import random
import json
import functools
from datetime import datetime

from flask import Flask, request, jsonify

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Serverless Middleware - Simulates FaaS behavior per request
# ---------------------------------------------------------------------------

invocation_stats = {
    "total": 0,
    "by_function": {},
    "cold_starts": set(),
}

_warm_functions = set()


def serverless_function(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        func_name = func.__name__
        invocation_stats["total"] += 1
        invocation_stats["by_function"].setdefault(func_name, 0)
        invocation_stats["by_function"][func_name] += 1

        is_cold = func_name not in _warm_functions
        if is_cold:
            cold_delay = random.uniform(0.1, 0.3)
            time.sleep(cold_delay)
            _warm_functions.add(func_name)
            invocation_stats["cold_starts"].add(func_name)

        start = time.time()
        request_id = f"req-{random.randint(100000, 999999)}"

        try:
            result = func(*args, **kwargs)
            elapsed = (time.time() - start) * 1000
            start_type = "COLD" if is_cold else "WARM"

            print(f"  [{start_type:4}] {request_id} | {func_name:<20} | "
                  f"{elapsed:.1f}ms | {request.method} {request.path}")

            if isinstance(result, dict):
                result["_meta"] = {
                    "request_id": request_id,
                    "function": func_name,
                    "start_type": start_type,
                    "duration_ms": round(elapsed, 2),
                    "billed_ms": max(1, round(elapsed)),
                    "memory_mb": 128,
                }
            return result

        except Exception as e:
            elapsed = (time.time() - start) * 1000
            print(f"  [ERR ] {request_id} | {func_name:<20} | "
                  f"{elapsed:.1f}ms | {str(e)}")
            return jsonify({"error": str(e), "request_id": request_id}), 500

    return wrapper


# ---------------------------------------------------------------------------
# Simulated Data Store (stands in for DynamoDB / FaunaDB)
# ---------------------------------------------------------------------------

USERS_TABLE = {
    "u-001": {"name": "Alice Chen", "email": "alice@example.com", "plan": "pro"},
    "u-002": {"name": "Bob Martinez", "email": "bob@example.com", "plan": "free"},
    "u-003": {"name": "Carol Kim", "email": "carol@example.com", "plan": "enterprise"},
}

ORDERS_TABLE = {
    "ord-101": {"user_id": "u-001", "item": "Widget Pro", "amount": 49.99, "status": "shipped"},
    "ord-102": {"user_id": "u-001", "item": "Gadget X", "amount": 29.99, "status": "delivered"},
    "ord-103": {"user_id": "u-002", "item": "Widget Basic", "amount": 9.99, "status": "pending"},
}

# ---------------------------------------------------------------------------
# Function Handlers - Each is an independent, deployable unit
# ---------------------------------------------------------------------------

@app.route("/api/users", methods=["GET"])
@serverless_function
def list_users():
    users = [{"id": uid, **data} for uid, data in USERS_TABLE.items()]
    return jsonify({"users": users, "count": len(users)})


@app.route("/api/users/<user_id>", methods=["GET"])
@serverless_function
def get_user(user_id):
    user = USERS_TABLE.get(user_id)
    if not user:
        return jsonify({"error": f"User {user_id} not found"}), 404
    return jsonify({"id": user_id, **user})


@app.route("/api/users", methods=["POST"])
@serverless_function
def create_user():
    body = request.get_json(force=True)
    if not body.get("name") or not body.get("email"):
        return jsonify({"error": "name and email are required"}), 400

    user_id = f"u-{random.randint(100, 999)}"
    USERS_TABLE[user_id] = {
        "name": body["name"],
        "email": body["email"],
        "plan": body.get("plan", "free"),
    }
    return jsonify({"id": user_id, "created": True, **USERS_TABLE[user_id]}), 201


@app.route("/api/orders/<user_id>", methods=["GET"])
@serverless_function
def get_orders(user_id):
    if user_id not in USERS_TABLE:
        return jsonify({"error": f"User {user_id} not found"}), 404

    orders = [
        {"id": oid, **data}
        for oid, data in ORDERS_TABLE.items()
        if data["user_id"] == user_id
    ]
    return jsonify({"user_id": user_id, "orders": orders, "count": len(orders)})


@app.route("/api/health", methods=["GET"])
@serverless_function
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "region": "us-east-1",
        "version": "1.4.2",
    })


@app.route("/api/stats", methods=["GET"])
@serverless_function
def get_stats():
    return jsonify({
        "total_invocations": invocation_stats["total"],
        "by_function": invocation_stats["by_function"],
        "cold_started_functions": list(invocation_stats["cold_starts"]),
        "warm_functions": list(_warm_functions),
    })


@app.route("/api/process", methods=["POST"])
@serverless_function
def process_data():
    body = request.get_json(force=True)
    data = body.get("data", [])
    operation = body.get("operation", "sum")

    if not isinstance(data, list):
        return jsonify({"error": "data must be a list"}), 400

    ops = {
        "sum": lambda d: sum(d),
        "avg": lambda d: sum(d) / len(d) if d else 0,
        "max": lambda d: max(d) if d else None,
        "min": lambda d: min(d) if d else None,
        "count": lambda d: len(d),
    }

    if operation not in ops:
        return jsonify({"error": f"Unknown operation: {operation}"}), 400

    result = ops[operation](data)
    return jsonify({"operation": operation, "input_size": len(data), "result": result})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Serverless API - Flask as Independent Functions")
    print("Endpoints:")
    print("  GET  /api/health          - Health check")
    print("  GET  /api/users           - List all users")
    print("  GET  /api/users/<id>      - Get user by ID")
    print("  POST /api/users           - Create user (JSON: name, email)")
    print("  GET  /api/orders/<uid>    - Get orders for user")
    print("  POST /api/process         - Process data (JSON: data, operation)")
    print("  GET  /api/stats           - Invocation statistics")
    print()
    app.run(port=5000, debug=False)
