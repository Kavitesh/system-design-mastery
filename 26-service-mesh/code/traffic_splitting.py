"""
Traffic Splitting - Canary Deployment Simulation
=================================================
Simulates a service mesh traffic splitting policy for canary deployments.
Traffic routes between stable (v1) and canary (v2) based on configurable
weights. Tracks error rates per version and decides whether to promote
or roll back the canary.

Usage:
  python traffic_splitting.py
"""

import time
import random
import threading
import requests
from flask import Flask, jsonify


# ---------------------------------------------------------------------------
# Service versions - stable and canary
# ---------------------------------------------------------------------------

stable_app = Flask("stable_v1")
canary_app = Flask("canary_v2")

@stable_app.route("/api/checkout")
def stable_checkout():
    time.sleep(random.uniform(0.005, 0.02))
    if random.random() < 0.02:
        return jsonify({"error": "internal", "version": "v1-stable"}), 500
    return jsonify({"status": "ok", "version": "v1-stable"})

@canary_app.route("/api/checkout")
def canary_checkout():
    time.sleep(random.uniform(0.005, 0.04))
    if random.random() < 0.08:
        return jsonify({"error": "internal", "version": "v2-canary"}), 500
    return jsonify({"status": "ok", "version": "v2-canary"})


# ---------------------------------------------------------------------------
# Mesh traffic splitter
# ---------------------------------------------------------------------------

class TrafficSplitter:
    def __init__(self, stable_pct, canary_pct):
        self.stable_pct = stable_pct
        self.canary_pct = canary_pct
        self.stats = {
            "v1-stable": {"sent": 0, "ok": 0, "err": 0, "lat_sum": 0},
            "v2-canary": {"sent": 0, "ok": 0, "err": 0, "lat_sum": 0},
        }

    def route(self):
        if random.random() * 100 < self.stable_pct:
            return "v1-stable", "http://127.0.0.1:9001/api/checkout"
        return "v2-canary", "http://127.0.0.1:9002/api/checkout"

    def record(self, version, ok, lat_ms):
        s = self.stats[version]
        s["sent"] += 1
        s["lat_sum"] += lat_ms
        s["ok" if ok else "err"] += 1

    def error_rate(self, version):
        s = self.stats[version]
        return (s["err"] / s["sent"] * 100) if s["sent"] else 0.0

    def avg_lat(self, version):
        s = self.stats[version]
        return (s["lat_sum"] / s["sent"]) if s["sent"] else 0.0


def send_requests(splitter, count):
    for _ in range(count):
        ver, url = splitter.route()
        start = time.time()
        try:
            resp = requests.get(url, timeout=2.0)
            splitter.record(ver, resp.status_code == 200, (time.time() - start) * 1000)
        except Exception:
            splitter.record(ver, False, (time.time() - start) * 1000)


def print_stats(splitter):
    print(f"\n  {'Version':<12} {'Sent':>6} {'OK':>6} {'Err':>5} {'Err%':>7} {'Avg Lat':>10}")
    print(f"  {'-'*12} {'-'*6} {'-'*6} {'-'*5} {'-'*7} {'-'*10}")
    for v in ["v1-stable", "v2-canary"]:
        s = splitter.stats[v]
        print(f"  {v:<12} {s['sent']:>6} {s['ok']:>6} {s['err']:>5} "
              f"{splitter.error_rate(v):>6.1f}% {splitter.avg_lat(v):>8.1f}ms")


# ---------------------------------------------------------------------------
# Demo runner
# ---------------------------------------------------------------------------

def run_demo():
    time.sleep(1.5)
    print("\n" + "=" * 60)
    print("CANARY DEPLOYMENT - TRAFFIC SPLITTING DEMO")
    print("=" * 60)

    print("\n--- Phase 1: 90/10 split (200 requests) ---")
    sp1 = TrafficSplitter(90, 10)
    send_requests(sp1, 200)
    print_stats(sp1)
    canary_err = sp1.error_rate("v2-canary")
    print(f"\n  Canary error rate: {canary_err:.1f}%", end="")

    if canary_err > 5.0:
        print(" - EXCEEDS 5% threshold")
        print("  Decision: ROLLBACK")
        print("\n--- Phase 2: Rollback (100/0, 100 requests) ---")
        sp2 = TrafficSplitter(100, 0)
        send_requests(sp2, 100)
        print_stats(sp2)
        print(f"\n  Rollback complete. Stable error rate: {sp2.error_rate('v1-stable'):.1f}%")
    else:
        print(" - within threshold")
        print("  Decision: RAMP UP")
        print("\n--- Phase 2: 70/30 split (200 requests) ---")
        sp2 = TrafficSplitter(70, 30)
        send_requests(sp2, 200)
        print_stats(sp2)
        canary_err2 = sp2.error_rate("v2-canary")
        print(f"\n  Canary error rate: {canary_err2:.1f}%", end="")
        if canary_err2 > 5.0:
            print(" - ROLLBACK to v1-stable")
        else:
            print(" - PROMOTE v2-canary to stable")

    print("\n--- In a real mesh ---")
    print("  Weight changes are Istio VirtualService config updates")
    print("  No redeployment needed - just a YAML change")
    print("  Envoy picks up new weights in seconds via xDS API")
    print("=" * 60)

    import os
    os._exit(0)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Starting traffic splitting demo...")
    threading.Thread(target=lambda: stable_app.run(port=9001, debug=False, use_reloader=False), daemon=True).start()
    threading.Thread(target=lambda: canary_app.run(port=9002, debug=False, use_reloader=False), daemon=True).start()
    threading.Thread(target=run_demo, daemon=True).start()
    time.sleep(20)
