"""
Cache Server
=============
A Flask API serving product data with an in-memory LRU cache layer.
Demonstrates cache-aside in a real HTTP context with TTL, hit/miss
stats, and a /benchmark endpoint measuring cached vs uncached latency.

No Redis required - the cache is built into the app.

Run: python cache_server.py
"""

import time
from collections import OrderedDict
from flask import Flask, jsonify, request

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Simulated slow database (100ms per query)
# ---------------------------------------------------------------------------

PRODUCTS = {
    1: {"id": 1, "name": "Laptop", "price": 999.99, "category": "electronics"},
    2: {"id": 2, "name": "Keyboard", "price": 149.99, "category": "electronics"},
    3: {"id": 3, "name": "Standing Desk", "price": 599.99, "category": "furniture"},
    4: {"id": 4, "name": "Monitor", "price": 399.99, "category": "electronics"},
    5: {"id": 5, "name": "Webcam", "price": 79.99, "category": "electronics"},
}
db_queries = 0


def db_get(pid):
    global db_queries
    time.sleep(0.1)
    db_queries += 1
    return PRODUCTS.get(pid)


# ---------------------------------------------------------------------------
# LRU cache with TTL
# ---------------------------------------------------------------------------

class LRUCache:
    def __init__(self, max_size=50, default_ttl=60):
        self._data = OrderedDict()
        self._exp = {}
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.hits = 0
        self.misses = 0

    def get(self, key):
        if key in self._data:
            if time.time() > self._exp[key]:
                del self._data[key]; del self._exp[key]
                self.misses += 1
                return None
            self._data.move_to_end(key)
            self.hits += 1
            return self._data[key]
        self.misses += 1
        return None

    def set(self, key, value, ttl=None):
        self._data[key] = value
        self._data.move_to_end(key)
        self._exp[key] = time.time() + (ttl or self.default_ttl)
        if len(self._data) > self.max_size:
            old, _ = self._data.popitem(last=False)
            del self._exp[old]

    def clear(self):
        self._data.clear(); self._exp.clear()
        self.hits = 0; self.misses = 0

    @property
    def hit_ratio(self):
        t = self.hits + self.misses
        return self.hits / t if t else 0


cache = LRUCache()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    return jsonify({
        "endpoints": {
            "GET /product/<id>": "Fetch product (cache-aside)",
            "GET /product/<id>?nocache=1": "Skip cache",
            "GET /benchmark": "Latency comparison",
            "GET /cache/stats": "Hit/miss stats",
        },
    })


@app.route("/product/<int:pid>")
def get_product(pid):
    skip = request.args.get("nocache")
    start = time.time()
    if not skip:
        cached = cache.get(f"product:{pid}")
        if cached:
            return jsonify({"source": "cache", "ms": round((time.time()-start)*1000, 2), "product": cached})
    product = db_get(pid)
    if not product:
        return jsonify({"error": "Not found"}), 404
    if not skip:
        cache.set(f"product:{pid}", product)
    return jsonify({"source": "database", "ms": round((time.time()-start)*1000, 2), "product": product})


@app.route("/cache/stats")
def stats():
    return jsonify({"size": len(cache._data), "hits": cache.hits,
                     "misses": cache.misses, "hit_ratio": f"{cache.hit_ratio:.1%}",
                     "db_queries": db_queries})


@app.route("/benchmark")
def benchmark():
    global db_queries
    cache.clear(); db_queries = 0
    avg = lambda lst: sum(lst) / len(lst)

    uncached = []
    for pid in range(1, 6):
        t = time.time(); db_get(pid); uncached.append((time.time()-t)*1000)

    cache.clear(); db_queries_cold = db_queries; db_queries = 0
    cold = []
    for pid in range(1, 6):
        t = time.time()
        if not cache.get(f"product:{pid}"):
            cache.set(f"product:{pid}", db_get(pid))
        cold.append((time.time()-t)*1000)

    db_queries_warm = db_queries; db_queries = 0
    warm = []
    for pid in range(1, 6):
        t = time.time(); cache.get(f"product:{pid}"); warm.append((time.time()-t)*1000)

    return jsonify({
        "uncached_avg_ms": round(avg(uncached), 2),
        "cold_cache_avg_ms": round(avg(cold), 2),
        "warm_cache_avg_ms": round(avg(warm), 2),
        "speedup": f"{avg(uncached)/max(avg(warm),0.001):.0f}x",
    })


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Cache server running at http://localhost:5055")
    app.run(port=5055, debug=False)
