"""
Rate Limiter Service
====================
Flask API gateway with pluggable rate limiting algorithms.
Supports token bucket and sliding window counter. Returns
standard rate limit headers on every response.

Run: python rate_limiter_service.py
"""

import time
import threading
from flask import Flask, jsonify, request

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Token Bucket algorithm
# ---------------------------------------------------------------------------

class TokenBucket:
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
        self.lock = threading.Lock()

    def consume(self) -> dict:
        with self.lock:
            now = time.time()
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now

            if self.tokens >= 1:
                self.tokens -= 1
                return {
                    "allowed": True,
                    "remaining": int(self.tokens),
                    "limit": self.capacity,
                    "reset": now + (self.capacity - self.tokens) / self.refill_rate,
                }
            retry_after = (1 - self.tokens) / self.refill_rate
            return {
                "allowed": False,
                "remaining": 0,
                "limit": self.capacity,
                "reset": now + retry_after,
                "retry_after": round(retry_after, 1),
            }


# ---------------------------------------------------------------------------
# Sliding Window Counter algorithm
# ---------------------------------------------------------------------------

class SlidingWindowCounter:
    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window = window_seconds
        self.prev_count = 0
        self.curr_count = 0
        self.window_start = time.time()
        self.lock = threading.Lock()

    def _rotate_if_needed(self, now: float):
        elapsed = now - self.window_start
        if elapsed >= self.window:
            windows_passed = int(elapsed / self.window)
            if windows_passed == 1:
                self.prev_count = self.curr_count
            else:
                self.prev_count = 0
            self.curr_count = 0
            self.window_start += windows_passed * self.window

    def consume(self) -> dict:
        with self.lock:
            now = time.time()
            self._rotate_if_needed(now)

            position = (now - self.window_start) / self.window
            weight = 1 - position
            estimated = self.prev_count * weight + self.curr_count

            reset_time = self.window_start + self.window

            if estimated < self.limit:
                self.curr_count += 1
                remaining = max(0, int(self.limit - estimated - 1))
                return {
                    "allowed": True,
                    "remaining": remaining,
                    "limit": self.limit,
                    "reset": reset_time,
                }
            return {
                "allowed": False,
                "remaining": 0,
                "limit": self.limit,
                "reset": reset_time,
                "retry_after": round(reset_time - now, 1),
            }


# ---------------------------------------------------------------------------
# Per-client bucket registry
# ---------------------------------------------------------------------------

ALGORITHM = "token_bucket"  # switch to "sliding_window" to compare
CAPACITY = 10
REFILL_RATE = 2.0
WINDOW_SECONDS = 10

buckets = {}
buckets_lock = threading.Lock()
stats = {"allowed": 0, "rejected": 0}


def get_bucket(client_id: str):
    with buckets_lock:
        if client_id not in buckets:
            if ALGORITHM == "token_bucket":
                buckets[client_id] = TokenBucket(CAPACITY, REFILL_RATE)
            else:
                buckets[client_id] = SlidingWindowCounter(CAPACITY, WINDOW_SECONDS)
        return buckets[client_id]


def identify_client() -> str:
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"key:{api_key}"
    return f"ip:{request.remote_addr}"


# ---------------------------------------------------------------------------
# Rate limit middleware
# ---------------------------------------------------------------------------

@app.after_request
def attach_rate_headers(response):
    result = getattr(request, "_rate_result", None)
    if result:
        response.headers["X-RateLimit-Limit"] = str(result["limit"])
        response.headers["X-RateLimit-Remaining"] = str(result["remaining"])
        response.headers["X-RateLimit-Reset"] = str(int(result["reset"]))
        if not result["allowed"]:
            response.headers["Retry-After"] = str(result.get("retry_after", 1))
    return response


@app.before_request
def rate_limit_check():
    if request.path in ("/api/health", "/api/stats"):
        return None

    client_id = identify_client()
    bucket = get_bucket(client_id)
    result = bucket.consume()
    request._rate_result = result

    if not result["allowed"]:
        stats["rejected"] += 1
        return jsonify({
            "error": "rate_limit_exceeded",
            "retry_after": result.get("retry_after", 1),
        }), 429

    stats["allowed"] += 1
    return None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.route("/api/data")
def get_data():
    client_id = identify_client()
    return jsonify({
        "message": "Here is your data",
        "client": client_id,
        "timestamp": time.time(),
    })


@app.route("/api/health")
def health():
    return jsonify({"status": "healthy", "algorithm": ALGORITHM})


@app.route("/api/stats")
def get_stats():
    with buckets_lock:
        client_info = {}
        for cid, b in buckets.items():
            if isinstance(b, TokenBucket):
                client_info[cid] = {"tokens": round(b.tokens, 1)}
            else:
                client_info[cid] = {
                    "curr_window_count": b.curr_count,
                    "prev_window_count": b.prev_count,
                }
    return jsonify({
        "algorithm": ALGORITHM,
        "total_allowed": stats["allowed"],
        "total_rejected": stats["rejected"],
        "active_clients": client_info,
    })


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"Rate limiter service starting - algorithm={ALGORITHM}, capacity={CAPACITY}")
    app.run(port=5100, debug=False)
