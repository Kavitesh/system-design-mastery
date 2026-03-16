"""
caching_proxy.py
================
A reverse proxy with an in-memory response cache. Cached entries have a
configurable TTL and are served directly without forwarding to the backend.
The proxy tracks cache hits, misses, and expirations, and exposes a
/_cache/stats endpoint for inspecting cache performance. A /_cache/purge
endpoint demonstrates manual cache invalidation.

The backend intentionally includes a timestamp in every response so you can
verify that cached responses return the same timestamp until the TTL expires.

Usage:
    python caching_proxy.py

Starts a backend on port 6020 and the caching proxy on port 5060. Hit
http://localhost:5060/products a few times to see cache hits, then wait
for the TTL to expire and see a cache miss.
"""

import hashlib
import json
import threading
import time

import requests as http_client
from flask import Flask, Response, jsonify, request

# ---------------------------------------------------------------------------
# Cache implementation
# ---------------------------------------------------------------------------

class ProxyCache:
    """Thread-safe in-memory cache with per-entry TTL. Keys are derived from
    the request method and full URL so that GET /a and GET /b are cached
    independently."""

    def __init__(self, default_ttl=10):
        self.default_ttl = default_ttl
        self.store = {}
        self.lock = threading.Lock()
        self.stats = {"hits": 0, "misses": 0, "expirations": 0, "invalidations": 0}

    def _key(self, method, url):
        raw = f"{method}:{url}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def get(self, method, url):
        key = self._key(method, url)
        with self.lock:
            entry = self.store.get(key)
            if entry is None:
                self.stats["misses"] += 1
                return None
            if time.time() > entry["expires_at"]:
                del self.store[key]
                self.stats["expirations"] += 1
                self.stats["misses"] += 1
                return None
            self.stats["hits"] += 1
            remaining_ttl = round(entry["expires_at"] - time.time(), 1)
            return {**entry, "remaining_ttl": remaining_ttl}

    def put(self, method, url, status, body, headers, ttl=None):
        key = self._key(method, url)
        ttl = ttl or self.default_ttl
        with self.lock:
            self.store[key] = {
                "status": status,
                "body": body,
                "headers": headers,
                "cached_at": time.time(),
                "expires_at": time.time() + ttl,
            }

    def purge(self, method, url):
        key = self._key(method, url)
        with self.lock:
            if key in self.store:
                del self.store[key]
                self.stats["invalidations"] += 1
                return True
            return False

    def purge_all(self):
        with self.lock:
            count = len(self.store)
            self.store.clear()
            self.stats["invalidations"] += count
            return count

    def get_stats(self):
        with self.lock:
            total = self.stats["hits"] + self.stats["misses"]
            hit_rate = round(self.stats["hits"] / total * 100, 1) if total > 0 else 0.0
            return {**self.stats, "total_requests": total, "hit_rate_pct": hit_rate, "entries": len(self.store)}


cache = ProxyCache(default_ttl=10)

BACKEND = "http://127.0.0.1:6020"

# ---------------------------------------------------------------------------
# Backend with timestamps
# ---------------------------------------------------------------------------

def create_backend():
    app = Flask("backend")
    products = [
        {"id": 1, "name": "Keyboard", "price": 75},
        {"id": 2, "name": "Monitor", "price": 300},
        {"id": 3, "name": "Headphones", "price": 150},
    ]

    @app.route("/products")
    def list_products():
        return {"products": products, "generated_at": time.strftime("%H:%M:%S")}

    @app.route("/products/<int:pid>")
    def get_product(pid):
        for p in products:
            if p["id"] == pid:
                return {"product": p, "generated_at": time.strftime("%H:%M:%S")}
        return {"error": "not found"}, 404

    return app


# ---------------------------------------------------------------------------
# Caching proxy
# ---------------------------------------------------------------------------

proxy = Flask("caching_proxy")

CACHEABLE_METHODS = {"GET"}


@proxy.route("/_cache/stats")
def cache_stats():
    return jsonify(cache.get_stats())


@proxy.route("/_cache/purge", methods=["POST"])
def cache_purge():
    path = request.args.get("path")
    if path:
        url = f"{BACKEND}{path}"
        found = cache.purge("GET", url)
        return jsonify({"purged": found, "path": path})
    count = cache.purge_all()
    return jsonify({"purged_all": True, "entries_removed": count})


@proxy.route("/", defaults={"path": ""}, methods=["GET", "POST", "PUT", "DELETE"])
@proxy.route("/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
def handle(path):
    full_url = f"{BACKEND}/{path}"

    if request.method in CACHEABLE_METHODS:
        cached = cache.get(request.method, full_url)
        if cached:
            print(f"[cache] HIT  /{path} (ttl={cached['remaining_ttl']}s)")
            resp = Response(cached["body"], status=cached["status"])
            resp.headers["Content-Type"] = cached["headers"].get("Content-Type", "application/json")
            resp.headers["X-Cache"] = "HIT"
            resp.headers["X-Cache-TTL"] = str(cached["remaining_ttl"])
            return resp

    try:
        backend_resp = http_client.request(
            method=request.method,
            url=full_url,
            headers={"Accept": "application/json"},
            data=request.get_data(),
            timeout=5,
        )
    except http_client.exceptions.RequestException as exc:
        print(f"[cache] BACKEND ERROR /{path}: {exc}")
        return jsonify({"error": "backend unavailable"}), 502

    if request.method in CACHEABLE_METHODS and 200 <= backend_resp.status_code < 300:
        cache.put(
            request.method,
            full_url,
            backend_resp.status_code,
            backend_resp.content,
            dict(backend_resp.headers),
        )
        print(f"[cache] MISS /{path} - cached for {cache.default_ttl}s")
    else:
        print(f"[cache] SKIP /{path} (method={request.method}, status={backend_resp.status_code})")

    resp = Response(backend_resp.content, status=backend_resp.status_code)
    resp.headers["Content-Type"] = backend_resp.headers.get("Content-Type", "application/json")
    resp.headers["X-Cache"] = "MISS"
    return resp


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    threading.Thread(target=lambda: create_backend().run(port=6020, debug=False, use_reloader=False), daemon=True).start()

    time.sleep(1)
    print("Caching proxy running on http://localhost:5060")
    proxy.run(port=5060, debug=False, use_reloader=False)
