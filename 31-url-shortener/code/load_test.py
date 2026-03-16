"""
URL Shortener Load Test
=======================
Measures the throughput and latency of the URL shortener service by
hammering it with concurrent create and redirect requests. Start the
url_shortener.py server first, then run this script.

Prerequisites:
  1. Start server: python url_shortener.py
  2. Run this:     python load_test.py
"""

import json
import random
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import Request, urlopen
from urllib.error import URLError

BASE_URL = "http://localhost:5000"
NUM_CREATES = 200
NUM_REDIRECTS = 500
CONCURRENCY = 10


# ---------------------------------------------------------------------------
# HTTP helpers (stdlib only - no extra dependencies)
# ---------------------------------------------------------------------------

def create_short_url(long_url: str) -> tuple[float, str]:
    payload = json.dumps({"long_url": long_url}).encode()
    req = Request(f"{BASE_URL}/api/v1/urls", data=payload,
                  headers={"Content-Type": "application/json"}, method="POST")
    start = time.perf_counter()
    try:
        with urlopen(req) as resp:
            body = json.loads(resp.read())
            return (time.perf_counter() - start) * 1000, body.get("short_code", "")
    except URLError:
        return (time.perf_counter() - start) * 1000, ""


def follow_redirect(short_code: str) -> tuple[float, int]:
    req = Request(f"{BASE_URL}/{short_code}", method="GET")
    start = time.perf_counter()
    try:
        with urlopen(req) as resp:
            return (time.perf_counter() - start) * 1000, resp.status
    except URLError as e:
        latency = (time.perf_counter() - start) * 1000
        return latency, getattr(e, "code", 0)


# ---------------------------------------------------------------------------
# Latency stats
# ---------------------------------------------------------------------------

def print_stats(label: str, latencies: list[float], total: int, wall_time: float):
    if not latencies:
        print(f"  {label}: No successful requests")
        return
    latencies.sort()
    errors = total - len(latencies)
    print(f"\n  {label}")
    print(f"  {'Requests:':<14} {total} total, {errors} failed")
    print(f"  {'Throughput:':<14} {total / wall_time:.0f} req/sec")
    print(f"  {'Mean:':<14} {statistics.mean(latencies):>8.1f} ms")
    print(f"  {'Median:':<14} {statistics.median(latencies):>8.1f} ms")
    print(f"  {'p90:':<14} {latencies[int(len(latencies) * 0.90)]:>8.1f} ms")
    print(f"  {'p99:':<14} {latencies[int(len(latencies) * 0.99)]:>8.1f} ms")
    print(f"  {'Min/Max:':<14} {min(latencies):.1f} / {max(latencies):.1f} ms")

    buckets = [5, 10, 25, 50, 100, 250, 500]
    print(f"\n  Latency distribution:")
    prev = 0
    for b in buckets:
        count = sum(1 for l in latencies if prev < l <= b)
        if count:
            print(f"    {prev:>4}-{b:>4}ms: {'#' * min(count, 50)} ({count})")
        prev = b


# ---------------------------------------------------------------------------
# Run the load test
# ---------------------------------------------------------------------------

def run_phase(label, func, args_list):
    latencies, codes = [], []
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        futures = {pool.submit(func, *a): i for i, a in enumerate(args_list)}
        for f in as_completed(futures):
            latency, result = f.result()
            if result:
                latencies.append(latency)
                codes.append(result)
    wall = time.perf_counter() - start
    return latencies, codes, wall


def main():
    print(f"URL Shortener Load Test - {BASE_URL}")
    print(f"Concurrency: {CONCURRENCY} threads\n")

    print(f"{'='*55}\nPHASE 1: Creating {NUM_CREATES} short URLs\n{'='*55}")
    create_args = [(f"https://example.com/page/{i}?t={time.time()}",) for i in range(NUM_CREATES)]
    create_lats, short_codes, create_wall = run_phase("CREATE", create_short_url, create_args)
    print_stats("CREATE (POST /api/v1/urls)", create_lats, NUM_CREATES, create_wall)

    if not short_codes:
        print("\nNo URLs created. Is the server running?")
        return

    print(f"\n{'='*55}\nPHASE 2: {NUM_REDIRECTS} redirect requests\n{'='*55}")
    random.shuffle(short_codes)
    redirect_args = [(short_codes[i % len(short_codes)],) for i in range(NUM_REDIRECTS)]
    redirect_lats, _, redirect_wall = run_phase("REDIRECT", follow_redirect, redirect_args)
    print_stats("REDIRECT (GET /<code>)", redirect_lats, NUM_REDIRECTS, redirect_wall)

    print(f"\n{'='*55}\nSUMMARY\n{'='*55}")
    print(f"  URLs created:       {len(short_codes)}")
    print(f"  Redirects served:   {len(redirect_lats)}")
    print(f"  Create throughput:  {NUM_CREATES / create_wall:.0f} req/sec")
    print(f"  Read throughput:    {NUM_REDIRECTS / redirect_wall:.0f} req/sec")
    if create_lats and redirect_lats:
        ratio = (NUM_REDIRECTS / redirect_wall) / (NUM_CREATES / create_wall)
        print(f"  Read/Write ratio:   {ratio:.1f}x (reads are faster)")


if __name__ == "__main__":
    main()
