"""
Stateless Server Demo
=====================
A simple Flask server that demonstrates stateless design.
State (request count, session) is stored externally in a JSON file
(simulating Redis/DB), so any server instance can handle any request.

Run multiple instances on different ports:
  python stateless_server.py 5001
  python stateless_server.py 5002

Then use load_test.py to distribute requests across them.
"""

import sys
import os
import json
import time
import socket

from flask import Flask, jsonify, request

app = Flask(__name__)

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 5001
SERVER_ID = f"server-{PORT}"
STATE_FILE = "shared_state.json"  # Simulates external store (Redis/DB)


# ---------------------------------------------------------------------------
# Shared state helpers (simulating Redis / external DB)
# ---------------------------------------------------------------------------

def read_state() -> dict:
    """Read shared state from file (simulates reading from Redis)."""
    if not os.path.exists(STATE_FILE):
        return {"total_requests": 0, "servers_seen": []}
    with open(STATE_FILE, "r") as f:
        return json.load(f)


def write_state(state: dict):
    """Write shared state to file (simulates writing to Redis)."""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    return jsonify({
        "server": SERVER_ID,
        "message": "I am stateless! Any server can handle any request.",
        "hostname": socket.gethostname()
    })


@app.route("/process", methods=["POST"])
def process():
    state = read_state()
    state["total_requests"] += 1

    if SERVER_ID not in state["servers_seen"]:
        state["servers_seen"].append(SERVER_ID)

    write_state(state)

    return jsonify({
        "handled_by": SERVER_ID,
        "total_requests": state["total_requests"],
        "servers_active": state["servers_seen"],
        "timestamp": time.time()
    })


@app.route("/stats")
def stats():
    state = read_state()
    return jsonify({
        "reporting_server": SERVER_ID,
        "total_requests_all_servers": state["total_requests"],
        "servers_seen": state["servers_seen"],
        "note": "Any server can report these stats because state is shared!"
    })


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"\n🚀 Starting {SERVER_ID} on port {PORT}")
    print(f"   This is a STATELESS server  - state lives in {STATE_FILE}")
    print(f"   Run another instance: python stateless_server.py {PORT + 1}\n")
    app.run(port=PORT, debug=False)
