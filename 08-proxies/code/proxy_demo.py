"""
proxy_demo.py
=============
An end-to-end demonstration that starts three backend servers and a reverse
proxy, then sends a burst of requests to show round-robin distribution,
header forwarding, and error handling. The demo runs entirely in one process
using threads - no external setup required.

The script prints a summary table at the end showing how requests were
distributed across backends and the average latency per backend.

Usage:
    python proxy_demo.py
"""

import itertools
import json
import threading
import time
from collections import defaultdict

import requests as http_client
from flask import Flask, Response, request

# ---------------------------------------------------------------------------
# Backend servers
# ---------------------------------------------------------------------------

def create_backend(name, port, delay=0):
    """Return a Flask app. The optional delay parameter simulates a slow
    backend so you can observe latency differences across the pool."""
    app = Flask(name)

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def handle(path):
        if delay:
            time.sleep(delay)
        return {
            "backend": name,
            "port": port,
            "path": f"/{path}",
            "client_ip": request.headers.get("X-Forwarded-For", request.remote_addr),
            "timestamp": time.strftime("%H:%M:%S"),
        }

    return app


# ---------------------------------------------------------------------------
# Reverse proxy with round-robin
# ---------------------------------------------------------------------------

BACKENDS = [
    "http://127.0.0.1:7001",
    "http://127.0.0.1:7002",
    "http://127.0.0.1:7003",
]

backend_cycle = itertools.cycle(BACKENDS)
proxy = Flask("demo_proxy")


@proxy.route("/", defaults={"path": ""})
@proxy.route("/<path:path>")
def forward(path):
    target = next(backend_cycle)
    url = f"{target}/{path}"
    headers = {"X-Forwarded-For": request.remote_addr, "X-Forwarded-Host": request.host}

    try:
        resp = http_client.get(url, headers=headers, timeout=5)
        return Response(resp.content, status=resp.status_code,
                        headers={"Content-Type": resp.headers.get("Content-Type", "application/json")})
    except http_client.exceptions.RequestException:
        return {"error": "backend unavailable", "target": target}, 502


# ---------------------------------------------------------------------------
# Demo runner
# ---------------------------------------------------------------------------

def run_app(app, port):
    import logging
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.ERROR)
    app.run(port=port, debug=False, use_reloader=False)


def send_requests(count, base_url, path=""):
    """Send count requests to the proxy and collect results."""
    results = []
    for i in range(count):
        start = time.time()
        try:
            resp = http_client.get(f"{base_url}/{path}", timeout=5)
            elapsed = (time.time() - start) * 1000
            data = resp.json()
            results.append({
                "request": i + 1,
                "status": resp.status_code,
                "backend": data.get("backend", "unknown"),
                "latency_ms": round(elapsed, 1),
            })
        except Exception as exc:
            elapsed = (time.time() - start) * 1000
            results.append({
                "request": i + 1,
                "status": 0,
                "backend": "error",
                "latency_ms": round(elapsed, 1),
            })
    return results


def print_results(results):
    """Print per-request log and a summary table."""
    print("\n--- Request Log ---")
    print(f"{'#':<4} {'Status':<8} {'Backend':<14} {'Latency':>10}")
    print("-" * 40)
    for r in results:
        print(f"{r['request']:<4} {r['status']:<8} {r['backend']:<14} {r['latency_ms']:>8.1f}ms")

    print("\n--- Distribution Summary ---")
    by_backend = defaultdict(list)
    for r in results:
        by_backend[r["backend"]].append(r["latency_ms"])

    print(f"{'Backend':<14} {'Requests':>10} {'Avg Latency':>14}")
    print("-" * 42)
    for backend, latencies in sorted(by_backend.items()):
        avg = sum(latencies) / len(latencies)
        print(f"{backend:<14} {len(latencies):>10} {avg:>12.1f}ms")

    total = len(results)
    success = sum(1 for r in results if 200 <= r["status"] < 300)
    print(f"\nTotal: {total} requests, {success} successful, {total - success} failed")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    backends = [
        ("backend-A", 7001, 0),
        ("backend-B", 7002, 0.05),
        ("backend-C", 7003, 0.1),
    ]

    for name, port, delay in backends:
        app = create_backend(name, port, delay)
        threading.Thread(target=run_app, args=(app, port), daemon=True).start()

    threading.Thread(target=run_app, args=(proxy, 5070), daemon=True).start()

    time.sleep(1.5)
    print("Proxy demo running on http://localhost:5070")
    print(f"Backends: {', '.join(f'{n} (:{p}, delay={d}s)' for n, p, d in backends)}")
    print(f"\nSending 12 requests through the proxy...\n")

    results = send_requests(12, "http://127.0.0.1:5070")
    print_results(results)

    print("\n--- Testing specific paths ---")
    for path in ["api/users", "api/orders", "health"]:
        resp = http_client.get(f"http://127.0.0.1:5070/{path}", timeout=5)
        data = resp.json()
        print(f"  GET /{path} -> {data['backend']} (port {data['port']})")

    print("\n--- Testing with a downed backend ---")
    print("(backend-C on :7003 has the highest delay, simulating a slow server)")
    print("In production, the proxy would health-check and remove it from the pool.")

    print("\nDemo complete.")
