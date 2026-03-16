"""
Rate-Limited Flask API
=======================
A Flask server with configurable rate limiting middleware that returns
proper HTTP 429 responses and X-RateLimit-* headers on every response.

Supports per-IP and per-API-key limiting with token bucket algorithm.

Run: python rate_limit_server.py
Test: curl http://localhost:5060/api/data
      curl http://localhost:5060/api/data -H "X-API-Key: user-alice"
"""

import time
from functools import wraps
from flask import Flask, request, jsonify, g


# ---------------------------------------------------------------------------
# Token Bucket (per-client)
# ---------------------------------------------------------------------------

class TokenBucket:
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()

    def _refill(self):
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

    def consume(self) -> tuple:
        """Returns (allowed, remaining, reset_seconds)."""
        self._refill()
        reset = (self.capacity - self.tokens) / self.refill_rate if self.refill_rate > 0 else 0
        if self.tokens >= 1:
            self.tokens -= 1
            return True, int(self.tokens), max(0, reset)
        return False, 0, max(0, (1 - self.tokens) / self.refill_rate)


# ---------------------------------------------------------------------------
# Rate Limiter Store
# ---------------------------------------------------------------------------

class RateLimiterStore:
    """Manages per-client token buckets."""

    def __init__(self):
        self.buckets = {}
        self.tiers = {
            "free":    {"capacity": 5,  "refill_rate": 1},
            "basic":   {"capacity": 20, "refill_rate": 5},
            "premium": {"capacity": 100, "refill_rate": 20},
        }
        self.api_keys = {
            "user-alice": "basic",
            "user-bob":   "premium",
        }

    def get_bucket(self, client_id: str) -> TokenBucket:
        if client_id not in self.buckets:
            tier_name = self.api_keys.get(client_id, "free")
            tier = self.tiers[tier_name]
            self.buckets[client_id] = TokenBucket(tier["capacity"], tier["refill_rate"])
        return self.buckets[client_id]

    def get_tier(self, client_id: str) -> str:
        return self.api_keys.get(client_id, "free")


store = RateLimiterStore()
app = Flask(__name__)


# ---------------------------------------------------------------------------
# Rate Limit Middleware
# ---------------------------------------------------------------------------

def rate_limit(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get("X-API-Key")
        client_id = api_key if api_key else request.remote_addr

        bucket = store.get_bucket(client_id)
        tier = store.get_tier(client_id)
        tier_config = store.tiers[tier]

        allowed, remaining, retry_after = bucket.consume()

        g.rate_limit_headers = {
            "X-RateLimit-Limit": str(tier_config["capacity"]),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(int(time.time() + retry_after)),
            "X-RateLimit-Tier": tier,
        }

        if not allowed:
            response = jsonify({
                "error": "rate_limit_exceeded",
                "message": f"Rate limit of {tier_config['capacity']} requests exceeded.",
                "tier": tier,
                "retry_after": round(retry_after, 1),
            })
            response.status_code = 429
            response.headers["Retry-After"] = str(int(retry_after) + 1)
            for k, v in g.rate_limit_headers.items():
                response.headers[k] = v
            return response

        return f(*args, **kwargs)
    return decorated


@app.after_request
def add_rate_limit_headers(response):
    headers = getattr(g, "rate_limit_headers", None)
    if headers:
        for k, v in headers.items():
            response.headers[k] = v
    return response


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.route("/api/data")
@rate_limit
def get_data():
    return jsonify({
        "message": "Here's your data",
        "timestamp": time.time(),
        "items": [
            {"id": 1, "name": "Widget A", "price": 9.99},
            {"id": 2, "name": "Widget B", "price": 19.99},
        ],
    })


@app.route("/api/expensive")
@rate_limit
def expensive_operation():
    time.sleep(0.5)
    return jsonify({
        "message": "Expensive computation complete",
        "result": 42,
    })


@app.route("/api/status")
def health_check():
    return jsonify({
        "status": "healthy",
        "active_clients": len(store.buckets),
        "tiers": {name: conf for name, conf in store.tiers.items()},
    })


# ---------------------------------------------------------------------------
# Burst Test Endpoint
# ---------------------------------------------------------------------------

@app.route("/api/burst-test")
def burst_test():
    """Simulates rapid requests to show rate limiting in action."""
    api_key = request.headers.get("X-API-Key")
    client_id = f"burst-test-{api_key or request.remote_addr}"

    tier = store.get_tier(client_id)
    tier_config = store.tiers[tier]
    bucket = TokenBucket(tier_config["capacity"], tier_config["refill_rate"])
    store.buckets[client_id] = bucket

    results = []
    for i in range(tier_config["capacity"] + 5):
        allowed, remaining, retry_after = bucket.consume()
        results.append({
            "request": i + 1,
            "allowed": allowed,
            "remaining": remaining,
        })

    allowed_count = sum(1 for r in results if r["allowed"])
    denied_count = len(results) - allowed_count

    return jsonify({
        "tier": tier,
        "limit": tier_config["capacity"],
        "total_requests": len(results),
        "allowed": allowed_count,
        "denied": denied_count,
        "details": results,
    })


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Rate-limited API running on http://localhost:5060")
    print(f"  Tiers: {list(store.tiers.keys())}")
    print(f"  Try: curl http://localhost:5060/api/data")
    print(f"       curl http://localhost:5060/api/burst-test")
    print(f"       curl http://localhost:5060/api/data -H 'X-API-Key: user-alice'")
    app.run(port=5060, debug=False)
