"""
Health Check Load Balancer
===========================
A Flask app that simulates three backend servers behind a load balancer
with active health checks. Backends can be toggled healthy/unhealthy
through an API, and the load balancer automatically stops routing
traffic to failed servers. Demonstrates the detection-and-recovery
cycle that production load balancers use.

Run: python health_check.py
Then visit http://localhost:5060
"""

import threading
import time
from flask import Flask, jsonify, request

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Simulated backend servers
# ---------------------------------------------------------------------------

backends = {
    "backend-1": {"healthy": True, "requests_served": 0, "last_check": None},
    "backend-2": {"healthy": True, "requests_served": 0, "last_check": None},
    "backend-3": {"healthy": True, "requests_served": 0, "last_check": None},
}

HEALTH_CHECK_INTERVAL = 3
UNHEALTHY_THRESHOLD = 2

check_log = []
lb_index = -1
lock = threading.Lock()


# ---------------------------------------------------------------------------
# Health checker (runs in background thread)
# ---------------------------------------------------------------------------

def health_checker():
    failure_counts = {name: 0 for name in backends}

    while True:
        time.sleep(HEALTH_CHECK_INTERVAL)
        with lock:
            for name, backend in backends.items():
                simulated_healthy = backend.get("_simulate_healthy", True)
                backend["last_check"] = time.strftime("%H:%M:%S")

                if simulated_healthy:
                    failure_counts[name] = 0
                    if not backend["healthy"]:
                        backend["healthy"] = True
                        msg = f"[{backend['last_check']}] {name}: recovered - back in rotation"
                        check_log.append(msg)
                        print(f"  HEALTH: {msg}")
                else:
                    failure_counts[name] += 1
                    if failure_counts[name] >= UNHEALTHY_THRESHOLD and backend["healthy"]:
                        backend["healthy"] = False
                        msg = f"[{backend['last_check']}] {name}: FAILED {UNHEALTHY_THRESHOLD} checks - removed from rotation"
                        check_log.append(msg)
                        print(f"  HEALTH: {msg}")


# ---------------------------------------------------------------------------
# Load balancer (round-robin across healthy servers only)
# ---------------------------------------------------------------------------

def pick_server():
    global lb_index
    with lock:
        healthy = [n for n, b in backends.items() if b["healthy"]]
        if not healthy:
            return None
        lb_index = (lb_index + 1) % len(healthy)
        chosen = healthy[lb_index]
        backends[chosen]["requests_served"] += 1
        return chosen


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    return jsonify({
        "service": "Health Check Load Balancer Demo",
        "health_check_interval": f"{HEALTH_CHECK_INTERVAL}s",
        "unhealthy_threshold": f"{UNHEALTHY_THRESHOLD} consecutive failures",
        "endpoints": {
            "GET /request": "Send a request through the load balancer",
            "GET /status": "View all backends and their health",
            "POST /fail/<name>": "Simulate a backend failure",
            "POST /recover/<name>": "Bring a failed backend back",
            "GET /log": "View health check history",
        },
    })


@app.route("/request")
def handle_request():
    server = pick_server()
    if not server:
        return jsonify({"error": "All backends are down - no healthy servers available"}), 503

    return jsonify({
        "routed_to": server,
        "total_served_by_this_server": backends[server]["requests_served"],
        "healthy_backends": [n for n, b in backends.items() if b["healthy"]],
    })


@app.route("/status")
def status():
    with lock:
        info = {}
        for name, b in backends.items():
            info[name] = {
                "healthy": b["healthy"],
                "requests_served": b["requests_served"],
                "last_check": b["last_check"],
            }
    return jsonify({"backends": info})


@app.route("/fail/<name>", methods=["POST"])
def fail_backend(name):
    if name not in backends:
        return jsonify({"error": f"Unknown backend: {name}"}), 404
    with lock:
        backends[name]["_simulate_healthy"] = False
    return jsonify({
        "action": f"Simulating failure on {name}",
        "note": f"Will be removed from rotation after {UNHEALTHY_THRESHOLD} failed checks ({UNHEALTHY_THRESHOLD * HEALTH_CHECK_INTERVAL}s max)",
    })


@app.route("/recover/<name>", methods=["POST"])
def recover_backend(name):
    if name not in backends:
        return jsonify({"error": f"Unknown backend: {name}"}), 404
    with lock:
        backends[name]["_simulate_healthy"] = True
    return jsonify({
        "action": f"Recovering {name}",
        "note": "Will be added back to rotation on next successful health check",
    })


@app.route("/log")
def get_log():
    return jsonify({"health_check_log": check_log[-20:]})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    checker_thread = threading.Thread(target=health_checker, daemon=True)
    checker_thread.start()
    print("Health Check LB running at http://localhost:5060")
    app.run(port=5060, debug=False)
