"""
Sidecar Proxy Simulation
========================
Flask-based sidecar proxy that intercepts HTTP traffic, injects tracing
headers, enforces timeouts, and collects latency metrics - all without
the application knowing about it.

Usage:
  python sidecar_proxy.py
"""

import time
import uuid
import threading
import requests
from flask import Flask, jsonify, request


# ---------------------------------------------------------------------------
# Application server - pure business logic
# ---------------------------------------------------------------------------

app_server = Flask("app_server")

@app_server.route("/orders/<order_id>")
def get_order(order_id):
    time.sleep(0.02)
    return jsonify({"order_id": order_id, "item": "Widget Pro", "quantity": 3})

@app_server.route("/health")
def health():
    return jsonify({"status": "healthy"})

@app_server.route("/slow")
def slow_endpoint():
    time.sleep(2.0)
    return jsonify({"result": "finally done"})


# ---------------------------------------------------------------------------
# Sidecar proxy - intercepts traffic, adds headers, collects metrics
# ---------------------------------------------------------------------------

sidecar = Flask("sidecar_proxy")
UPSTREAM = "http://127.0.0.1:8081"
TIMEOUT = 1.0

metrics = {"total": 0, "ok": 0, "fail": 0, "timeout": 0, "latency_sum": 0.0}
lock = threading.Lock()

def record(latency_ms, success, timed_out=False):
    with lock:
        metrics["total"] += 1
        metrics["latency_sum"] += latency_ms
        if timed_out:
            metrics["timeout"] += 1
            metrics["fail"] += 1
        elif success:
            metrics["ok"] += 1
        else:
            metrics["fail"] += 1

@sidecar.route("/metrics")
def get_metrics():
    with lock:
        avg = metrics["latency_sum"] / metrics["total"] if metrics["total"] else 0
        return jsonify({**metrics, "avg_latency_ms": round(avg, 2)})

@sidecar.route("/", defaults={"path": ""})
@sidecar.route("/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
def proxy(path):
    if path == "metrics":
        return get_metrics()

    req_id = str(uuid.uuid4())[:8]
    trace_id = request.headers.get("x-trace-id", str(uuid.uuid4())[:16])
    headers = {"x-request-id": req_id, "x-trace-id": trace_id, "x-forwarded-by": "sidecar"}
    start = time.time()

    try:
        resp = requests.request(request.method, f"{UPSTREAM}/{path}", headers=headers, timeout=TIMEOUT)
        lat = (time.time() - start) * 1000
        record(lat, resp.ok)
        return jsonify({
            "data": resp.json(),
            "sidecar": {"request_id": req_id, "trace_id": trace_id, "latency_ms": round(lat, 2)}
        }), resp.status_code
    except requests.Timeout:
        lat = (time.time() - start) * 1000
        record(lat, False, timed_out=True)
        return jsonify({"error": "upstream timeout", "request_id": req_id}), 504


# ---------------------------------------------------------------------------
# Demo runner
# ---------------------------------------------------------------------------

def run_demo():
    time.sleep(1.5)
    base = "http://127.0.0.1:8080"
    print("\n" + "=" * 60)
    print("SIDECAR PROXY DEMO")
    print("=" * 60)

    print("\n--- Normal request (order lookup) ---")
    r = requests.get(f"{base}/orders/ORD-42").json()
    print(f"  Order: {r['data']['item']} x{r['data']['quantity']}")
    print(f"  Request ID: {r['sidecar']['request_id']}")
    print(f"  Latency: {r['sidecar']['latency_ms']}ms")

    print("\n--- Timeout enforcement (slow endpoint, 1s limit) ---")
    r = requests.get(f"{base}/slow").json()
    print(f"  Error: {r['error']}")

    print("\n--- Trace propagation ---")
    r = requests.get(f"{base}/orders/ORD-99", headers={"x-trace-id": "ext-abc123"}).json()
    print(f"  Sent: ext-abc123 | Got: {r['sidecar']['trace_id']}")
    print(f"  Preserved: {r['sidecar']['trace_id'] == 'ext-abc123'}")

    print("\n--- Sidecar metrics ---")
    m = requests.get(f"{base}/metrics").json()
    print(f"  Total: {m['total']} | OK: {m['ok']} | Fail: {m['fail']} | "
          f"Timeout: {m['timeout']} | Avg: {m['avg_latency_ms']}ms")
    print("\n" + "=" * 60)

    import os
    os._exit(0)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Starting sidecar proxy demo...")
    threading.Thread(target=lambda: app_server.run(port=8081, debug=False, use_reloader=False), daemon=True).start()
    threading.Thread(target=run_demo, daemon=True).start()
    sidecar.run(port=8080, debug=False, use_reloader=False)
