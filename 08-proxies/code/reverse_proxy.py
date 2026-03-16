"""
reverse_proxy.py
================
A Flask-based reverse proxy that forwards incoming requests to a pool of
backend servers using round-robin selection. Each request is logged with the
chosen backend, response status, and round-trip latency. The proxy preserves
the original Host header and injects X-Forwarded-For so backends can see the
real client IP.

Usage:
    python reverse_proxy.py

Starts three backend servers on ports 6001-6003 and a reverse proxy on port
5000. Send requests to http://localhost:5000 and watch the proxy distribute
them across backends.
"""

import itertools
import threading
import time

import requests as http_client
from flask import Flask, Response, request

# ---------------------------------------------------------------------------
# Backend server factory
# ---------------------------------------------------------------------------

def create_backend(name, port):
    """Return a Flask app that identifies itself by name in every response."""
    app = Flask(name)

    @app.route("/", defaults={"path": ""}, methods=["GET", "POST", "PUT", "DELETE"])
    @app.route("/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
    def handle(path):
        return {
            "backend": name,
            "port": port,
            "path": f"/{path}",
            "method": request.method,
            "message": f"Handled by {name}",
        }

    return app


# ---------------------------------------------------------------------------
# Reverse proxy
# ---------------------------------------------------------------------------

BACKENDS = [
    "http://127.0.0.1:6001",
    "http://127.0.0.1:6002",
    "http://127.0.0.1:6003",
]

backend_cycle = itertools.cycle(BACKENDS)

proxy_app = Flask("reverse_proxy")


@proxy_app.route("/", defaults={"path": ""}, methods=["GET", "POST", "PUT", "DELETE"])
@proxy_app.route("/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
def proxy(path):
    target = next(backend_cycle)
    url = f"{target}/{path}"

    headers = {k: v for k, v in request.headers if k.lower() != "host"}
    headers["X-Forwarded-For"] = request.remote_addr
    headers["X-Forwarded-Host"] = request.host

    start = time.time()
    try:
        resp = http_client.request(
            method=request.method,
            url=url,
            headers=headers,
            data=request.get_data(),
            params=request.args,
            timeout=5,
        )
        elapsed_ms = (time.time() - start) * 1000
        print(f"[proxy] {request.method} /{path} -> {target} | {resp.status_code} | {elapsed_ms:.1f}ms")

        excluded = {"content-encoding", "content-length", "transfer-encoding", "connection"}
        response_headers = {k: v for k, v in resp.headers.items() if k.lower() not in excluded}

        return Response(resp.content, status=resp.status_code, headers=response_headers)

    except http_client.exceptions.RequestException as exc:
        elapsed_ms = (time.time() - start) * 1000
        print(f"[proxy] {request.method} /{path} -> {target} | FAILED | {elapsed_ms:.1f}ms | {exc}")
        return {"error": "backend unavailable", "target": target}, 502


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

def run_backend(name, port):
    app = create_backend(name, port)
    app.run(port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    for name, port in [("backend-1", 6001), ("backend-2", 6002), ("backend-3", 6003)]:
        t = threading.Thread(target=run_backend, args=(name, port), daemon=True)
        t.start()

    time.sleep(1)
    print("Reverse proxy running on http://localhost:5000")
    proxy_app.run(port=5000, debug=False, use_reloader=False)
