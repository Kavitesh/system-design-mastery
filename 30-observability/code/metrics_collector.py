"""
Prometheus-Style Metrics Collector
===================================
Implements counter, gauge, and histogram metric types from scratch.
Simulates traffic and shows how each metric type captures different signals.

Run: python metrics_collector.py
"""

import time
import random
import threading
from collections import defaultdict

# ---------------------------------------------------------------------------
# Metric types
# ---------------------------------------------------------------------------

class Counter:
    """Monotonically increasing value. Only goes up (resets on restart)."""

    def __init__(self, name, description):
        self.name = name
        self.description = description
        self._value = 0
        self._lock = threading.Lock()

    def inc(self, amount=1):
        with self._lock:
            self._value += amount

    @property
    def value(self):
        return self._value


class Gauge:
    """Point-in-time value. Goes up and down."""

    def __init__(self, name, description):
        self.name = name
        self.description = description
        self._value = 0
        self._lock = threading.Lock()

    def set(self, value):
        with self._lock:
            self._value = value

    def inc(self, amount=1):
        with self._lock:
            self._value += amount

    def dec(self, amount=1):
        with self._lock:
            self._value -= amount

    @property
    def value(self):
        return self._value


class Histogram:
    """Tracks distribution of values across predefined buckets."""

    def __init__(self, name, description, buckets=None):
        self.name = name
        self.description = description
        self.buckets = buckets or [0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5]
        self._counts = defaultdict(int)
        self._sum = 0.0
        self._count = 0
        self._lock = threading.Lock()

    def observe(self, value):
        with self._lock:
            self._sum += value
            self._count += 1
            for b in self.buckets:
                if value <= b:
                    self._counts[b] += 1

    def snapshot(self):
        with self._lock:
            cumulative = 0
            result = {}
            for b in self.buckets:
                cumulative += self._counts[b]
                result[b] = cumulative
            result["+Inf"] = self._count
            return result, self._sum, self._count


# ---------------------------------------------------------------------------
# Metrics registry
# ---------------------------------------------------------------------------

class MetricsRegistry:
    def __init__(self):
        self.metrics = {}

    def register(self, metric):
        self.metrics[metric.name] = metric
        return metric

    def dump_prometheus_format(self):
        lines = []
        for name, m in self.metrics.items():
            lines.append(f"# HELP {name} {m.description}")
            if isinstance(m, Counter):
                lines.append(f"# TYPE {name} counter")
                lines.append(f"{name} {m.value}")
            elif isinstance(m, Gauge):
                lines.append(f"# TYPE {name} gauge")
                lines.append(f"{name} {m.value}")
            elif isinstance(m, Histogram):
                lines.append(f"# TYPE {name} histogram")
                buckets, total, count = m.snapshot()
                for bound, cumcount in buckets.items():
                    lines.append(f'{name}_bucket{{le="{bound}"}} {cumcount}')
                lines.append(f"{name}_sum {total:.4f}")
                lines.append(f"{name}_count {count}")
            lines.append("")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Simulate traffic
# ---------------------------------------------------------------------------

def simulate_request(registry):
    req_counter = registry.metrics["http_requests_total"]
    active_gauge = registry.metrics["active_connections"]
    latency_hist = registry.metrics["request_duration_seconds"]

    active_gauge.inc()
    req_counter.inc()

    latency = random.expovariate(1 / 0.08)
    time.sleep(min(latency, 0.3))

    latency_hist.observe(latency)
    active_gauge.dec()

    return latency


def run_simulation():
    registry = MetricsRegistry()
    registry.register(Counter("http_requests_total", "Total HTTP requests served"))
    registry.register(Gauge("active_connections", "Currently active connections"))
    registry.register(Histogram(
        "request_duration_seconds",
        "Request latency in seconds",
        buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
    ))

    print("Metrics Collector - Prometheus-style metrics simulation")
    print("=" * 60)

    num_requests = 200
    latencies = []

    for batch in range(4):
        batch_latencies = []
        for _ in range(50):
            lat = simulate_request(registry)
            batch_latencies.append(lat)
            latencies.append(lat)

        avg = sum(batch_latencies) / len(batch_latencies)
        print(f"\nBatch {batch + 1}: 50 requests | avg latency {avg*1000:.1f}ms | "
              f"total served: {registry.metrics['http_requests_total'].value}")

    print(f"\n{'=' * 60}")
    print("LATENCY DISTRIBUTION")
    print(f"{'=' * 60}")

    hist = registry.metrics["request_duration_seconds"]
    buckets, total_sum, total_count = hist.snapshot()
    prev = 0
    for bound, cumcount in buckets.items():
        count_in_bucket = cumcount - prev if bound != "+Inf" else cumcount - prev
        bar = "#" * count_in_bucket
        label = f"<= {bound}s" if bound != "+Inf" else "+Inf"
        print(f"  {label:<12} {count_in_bucket:>4}  {bar}")
        prev = cumcount

    print(f"\n  Total: {total_count} requests | Mean: {total_sum/total_count*1000:.1f}ms")

    print(f"\n{'=' * 60}")
    print("PROMETHEUS EXPOSITION FORMAT")
    print(f"{'=' * 60}")
    print(registry.dump_prometheus_format())


if __name__ == "__main__":
    run_simulation()
