"""
Mesh Observability - Distributed Tracing Simulation
=====================================================
Simulates mesh observability: requests flow through a service chain,
sidecars collect spans, and we get distributed traces plus golden
signal metrics - the same data Envoy exports to Jaeger/Prometheus.

Usage:
  python mesh_observability.py
"""

import time
import uuid
import random
from collections import defaultdict


# ---------------------------------------------------------------------------
# Trace collector (simulates Jaeger / Zipkin)
# ---------------------------------------------------------------------------

class TraceCollector:
    def __init__(self):
        self.traces = {}
        self.metrics = defaultdict(lambda: {"reqs": 0, "errs": 0, "lats": []})

    def record(self, trace_id, span):
        self.traces.setdefault(trace_id, []).append(span)
        m = self.metrics[span["service"]]
        m["reqs"] += 1
        m["lats"].append(span["duration_ms"])
        if span["status"] >= 500:
            m["errs"] += 1

    def stats(self, svc):
        m = self.metrics[svc]
        if not m["reqs"]: return None
        lats = sorted(m["lats"])
        p = lambda pct: lats[min(int(len(lats) * pct), len(lats) - 1)]
        return {"service": svc, "reqs": m["reqs"], "errs": m["errs"],
                "err_pct": m["errs"] / m["reqs"] * 100,
                "p50": p(0.50), "p99": p(0.99), "avg": sum(lats) / len(lats)}


# ---------------------------------------------------------------------------
# Simulated meshed service
# ---------------------------------------------------------------------------

class Service:
    def __init__(self, name, base_lat_ms, err_rate, collector):
        self.name = name
        self.base_lat_ms = base_lat_ms
        self.err_rate = err_rate
        self.collector = collector
        self.downstream = []

    def add_downstream(self, svc):
        self.downstream.append(svc)

    def handle(self, trace_id, parent_id=None):
        span_id = uuid.uuid4().hex[:8]
        start = time.time()
        time.sleep((self.base_lat_ms + random.uniform(-3, 10)) / 1000.0)
        failed = random.random() < self.err_rate
        status, children = (500 if failed else 200), []
        if not failed:
            for ds in self.downstream:
                child = ds.handle(trace_id, span_id)
                children.append(child)
                if child["status"] >= 500:
                    status = 502; break
        dur = round((time.time() - start) * 1000, 2)
        self.collector.record(trace_id, {
            "span_id": span_id, "parent": parent_id,
            "service": self.name, "duration_ms": dur, "status": status})
        return {"span_id": span_id, "service": self.name,
                "status": status, "duration_ms": dur, "children": children}


def print_trace(result, depth=0):
    indent = "  " + "  " * depth
    tag = "ERR" if result["status"] >= 500 else " OK"
    print(f"{indent}[{tag}] {result['service']} ({result['duration_ms']:.1f}ms)")
    for child in result.get("children", []):
        print_trace(child, depth + 1)


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def main():
    print("\n" + "=" * 60)
    print("MESH OBSERVABILITY - DISTRIBUTED TRACING DEMO")
    print("=" * 60)

    collector = TraceCollector()

    gw = Service("api-gateway", 5, 0.01, collector)
    orders = Service("order-service", 10, 0.02, collector)
    pay = Service("payment-service", 25, 0.05, collector)
    inv = Service("inventory-service", 8, 0.03, collector)
    wh = Service("warehouse-db", 15, 0.01, collector)
    gw.add_downstream(orders)
    orders.add_downstream(pay)
    orders.add_downstream(inv)
    inv.add_downstream(wh)
    print("\n  Topology: gateway -> orders -> [payments, inventory -> warehouse]")

    print("\n" + "-" * 60)
    print("Single Request Trace")
    tid = uuid.uuid4().hex[:16]
    result = gw.handle(tid)
    print(f"\n  Trace ID: {tid}")
    print_trace(result)
    print(f"  End-to-end: {result['duration_ms']:.1f}ms | "
          f"Spans: {len(collector.traces[tid])}")

    print("\n" + "-" * 60)
    print("Simulating 500 requests...")
    errors = []
    for _ in range(500):
        t = uuid.uuid4().hex[:16]
        r = gw.handle(t)
        if r["status"] >= 500:
            errors.append(t)
    print(f"  Done: 500 | Failed: {len(errors)} | Success: {(500 - len(errors)) / 5:.1f}%")

    print("\n" + "-" * 60)
    print("Golden Signals")
    svcs = ["api-gateway", "order-service", "payment-service",
            "inventory-service", "warehouse-db"]
    print(f"\n  {'Service':<22} {'Reqs':>5} {'Errs':>5} {'Err%':>6} {'p50':>7} {'p99':>7}")
    print(f"  {'-'*22} {'-'*5} {'-'*5} {'-'*6} {'-'*7} {'-'*7}")
    for svc in svcs:
        s = collector.stats(svc)
        if s:
            print(f"  {s['service']:<22} {s['reqs']:>5} {s['errs']:>5} "
                  f"{s['err_pct']:>5.1f}% {s['p50']:>6.1f}ms {s['p99']:>6.1f}ms")

    if errors:
        print("\n" + "-" * 60)
        print(f"Error Investigation (trace: {errors[0]})")
        for s in collector.traces[errors[0]]:
            tag = "ERR" if s["status"] >= 500 else " OK"
            print(f"    [{tag}] {s['service']:<22} {s['duration_ms']:>7.1f}ms")
        failing = [s for s in collector.traces[errors[0]] if s["status"] >= 500]
        if failing:
            print(f"  Root cause: {failing[-1]['service']} returned {failing[-1]['status']}")

    print("\n" + "-" * 60)
    print("The mesh provides all of this automatically:")
    print("  Traces (Jaeger) | Metrics (Prometheus) | Access logs")
    print("  Zero instrumentation code required in your services.")
    print("=" * 60)


if __name__ == "__main__":
    main()
