"""
Rate Limiter Client
===================
A client that reads X-RateLimit-* headers and backs off
automatically when throttled. Demonstrates exponential
backoff with jitter - the right way to handle 429s.

Prerequisites: start rate_limiter_service.py first.
Run: python rate_limiter_client.py
"""

import time
import random
import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = "http://localhost:5100"
ENDPOINT = f"{BASE_URL}/api/data"
TOTAL_REQUESTS = 30
API_KEY = "demo-client-1"

MAX_BACKOFF = 8.0
BASE_BACKOFF = 0.5


# ---------------------------------------------------------------------------
# Smart client with header-aware backoff
# ---------------------------------------------------------------------------

class RateLimitAwareClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers["X-API-Key"] = api_key
        self.stats = {"sent": 0, "ok": 0, "throttled": 0, "errors": 0, "total_wait": 0.0}
        self.consecutive_429s = 0

    def _backoff_duration(self, retry_after: float | None) -> float:
        if retry_after and retry_after > 0:
            jitter = random.uniform(0, 0.3)
            return retry_after + jitter

        exp_backoff = min(MAX_BACKOFF, BASE_BACKOFF * (2 ** self.consecutive_429s))
        jitter = random.uniform(0, exp_backoff * 0.3)
        return exp_backoff + jitter

    def send_request(self) -> dict:
        self.stats["sent"] += 1
        try:
            resp = self.session.get(ENDPOINT, timeout=5)
        except requests.ConnectionError:
            self.stats["errors"] += 1
            return {"status": "error", "detail": "connection refused - is the server running?"}

        result = {
            "status_code": resp.status_code,
            "limit": resp.headers.get("X-RateLimit-Limit", "?"),
            "remaining": resp.headers.get("X-RateLimit-Remaining", "?"),
            "reset": resp.headers.get("X-RateLimit-Reset", "?"),
        }

        if resp.status_code == 200:
            self.stats["ok"] += 1
            self.consecutive_429s = 0
            result["status"] = "ok"
            return result

        if resp.status_code == 429:
            self.stats["throttled"] += 1
            self.consecutive_429s += 1
            retry_after = None
            if "Retry-After" in resp.headers:
                retry_after = float(resp.headers["Retry-After"])
            wait = self._backoff_duration(retry_after)
            self.stats["total_wait"] += wait
            result["status"] = "throttled"
            result["retry_after_header"] = retry_after
            result["actual_wait"] = round(wait, 2)
            return result

        self.stats["errors"] += 1
        result["status"] = "error"
        return result


# ---------------------------------------------------------------------------
# Demo: burst requests and observe backoff behavior
# ---------------------------------------------------------------------------

def run_demo():
    client = RateLimitAwareClient(API_KEY)

    print("=" * 70)
    print("RATE LIMITER CLIENT - HEADER-AWARE BACKOFF DEMO")
    print("=" * 70)
    print(f"\nTarget: {ENDPOINT}")
    print(f"API Key: {API_KEY}")
    print(f"Sending {TOTAL_REQUESTS} requests, observing rate limit headers\n")

    print(f"  {'#':>3}  {'Status':>10}  {'Code':>5}  {'Remaining':>10}  {'Action'}")
    print(f"  {'-'*3}  {'-'*10}  {'-'*5}  {'-'*10}  {'-'*30}")

    for i in range(1, TOTAL_REQUESTS + 1):
        result = client.send_request()

        if result["status"] == "error" and "connection refused" in result.get("detail", ""):
            print(f"\n  ERROR: {result['detail']}")
            print(f"  Start the server first: python rate_limiter_service.py")
            return

        status_display = result["status"].upper()
        code = result.get("status_code", "-")
        remaining = result.get("remaining", "-")

        if result["status"] == "ok":
            action = f"processed (remaining: {remaining})"
        elif result["status"] == "throttled":
            wait = result["actual_wait"]
            retry_hdr = result.get("retry_after_header")
            if retry_hdr:
                action = f"backing off {wait}s (server said {retry_hdr}s)"
            else:
                action = f"exp backoff {wait}s (attempt {client.consecutive_429s})"
            print(f"  {i:>3}  {status_display:>10}  {code:>5}  {remaining:>10}  {action}")
            time.sleep(wait)
            continue
        else:
            action = "unexpected response"

        print(f"  {i:>3}  {status_display:>10}  {code:>5}  {remaining:>10}  {action}")

    # Summary
    s = client.stats
    print(f"\n{'=' * 70}")
    print("RESULTS")
    print(f"{'=' * 70}")
    print(f"  Requests sent:    {s['sent']}")
    print(f"  Successful (200): {s['ok']}")
    print(f"  Throttled (429):  {s['throttled']}")
    print(f"  Errors:           {s['errors']}")
    print(f"  Total wait time:  {s['total_wait']:.1f}s")
    if s["throttled"] > 0:
        print(f"  Avg wait/backoff: {s['total_wait'] / s['throttled']:.2f}s")

    print(f"\n  The client respected rate limit headers instead of hammering the")
    print(f"  server. Retry-After from the server takes priority over exponential")
    print(f"  backoff. Jitter prevents thundering herd when multiple clients")
    print(f"  back off and retry at the same time.")
    print(f"{'=' * 70}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run_demo()
