"""
User Service (Microservice)
============================
Owns all user data. Other services must go through the API to access user info.
This is the same user functionality from monolith_app.py, but isolated.

Run:
  python user_service.py

Endpoints:
  POST /users         - Create a user
  GET  /users         - List all users
  GET  /users/<id>    - Get user by ID
  PUT  /users/<id>    - Update a user
  DELETE /users/<id>  - Delete a user
  GET  /health        - Health check for service discovery
"""

import time
from flask import Flask, jsonify, request

app = Flask(__name__)

# ---------------------------------------------------------------------------
# User service owns its own data store - no shared database
# ---------------------------------------------------------------------------

USERS = {}
NEXT_ID = 1
STARTED_AT = time.time()


def seed():
    global NEXT_ID
    USERS[1] = {"id": 1, "name": "Alice", "email": "alice@example.com", "created_at": time.time()}
    USERS[2] = {"id": 2, "name": "Bob", "email": "bob@example.com", "created_at": time.time()}
    USERS[3] = {"id": 3, "name": "Charlie", "email": "charlie@example.com", "created_at": time.time()}
    NEXT_ID = 4


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/users", methods=["POST"])
def create_user():
    global NEXT_ID
    data = request.json
    if not data.get("name") or not data.get("email"):
        return jsonify({"error": "name and email are required"}), 400
    user = {"id": NEXT_ID, "name": data["name"], "email": data["email"], "created_at": time.time()}
    USERS[NEXT_ID] = user
    NEXT_ID += 1
    return jsonify(user), 201


@app.route("/users")
def list_users():
    return jsonify(list(USERS.values()))


@app.route("/users/<int:user_id>")
def get_user(user_id):
    user = USERS.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user)


@app.route("/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    user = USERS.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    data = request.json
    if "name" in data:
        user["name"] = data["name"]
    if "email" in data:
        user["email"] = data["email"]
    return jsonify(user)


@app.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    if user_id not in USERS:
        return jsonify({"error": "User not found"}), 404
    del USERS[user_id]
    return jsonify({"deleted": user_id})


@app.route("/health")
def health():
    return jsonify({
        "service": "user-service",
        "status": "healthy",
        "users_count": len(USERS),
        "uptime_seconds": round(time.time() - STARTED_AT, 1),
    })


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    seed()
    print("User service starting on port 5001")
    app.run(port=5001, debug=False)
