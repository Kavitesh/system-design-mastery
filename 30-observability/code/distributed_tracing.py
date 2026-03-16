"""
Distributed Tracing Simulation
================================
Simulates trace propagation across microservices with span creation,
parent-child relationships, and a visual span tree.

Run: python distributed_tracing.py
"""

import uuid
import time
import random

# ---------------------------------------------------------------------------
# Span and Trace primitives
# ---------------------------------------------------------------------------

class Span:
    def __init__(self, trace_id, name, service, parent_id=None):
        self.trace_id = trace_id
        self.span_id = uuid.uuid4().hex[:8]
        self.parent_id = parent_id
        self.name = name
        self.service = service
        self.start_time = time.time()
        self.end_time = None
        self.tags = {}
        self.status = "OK"

    def set_tag(self, key, value):
        self.tags[key] = value
        return self

    def set_error(self, message):
        self.status = "ERROR"
        self.tags["error.message"] = message
        return self

    def finish(self):
        self.end_time = time.time()

    @property
    def duration_ms(self):
        if self.end_time is None:
            return 0
        return (self.end_time - self.start_time) * 1000


class Tracer:
    def __init__(self):
        self.spans = []

    def start_trace(self, name, service):
        trace_id = uuid.uuid4().hex[:16]
        span = Span(trace_id, name, service)
        self.spans.append(span)
        return span

    def start_span(self, name, service, parent):
        span = Span(parent.trace_id, name, service, parent_id=parent.span_id)
        self.spans.append(span)
        return span

    def get_trace(self, trace_id):
        return [s for s in self.spans if s.trace_id == trace_id]


# ---------------------------------------------------------------------------
# Simulated microservices
# ---------------------------------------------------------------------------

def api_gateway(tracer):
    root = tracer.start_trace("HTTP GET /api/order/789", "api-gateway")
    root.set_tag("http.method", "GET")
    root.set_tag("http.url", "/api/order/789")
    root.set_tag("client.ip", "203.0.113.42")

    time.sleep(random.uniform(0.001, 0.003))

    auth_service(tracer, root)
    order_service(tracer, root)

    root.set_tag("http.status_code", 200)
    root.finish()
    return root


def auth_service(tracer, parent):
    span = tracer.start_span("authenticate", "auth-service", parent)
    span.set_tag("auth.method", "JWT")

    time.sleep(random.uniform(0.002, 0.008))

    cache_span = tracer.start_span("redis.get token_cache", "auth-service", span)
    cache_hit = random.random() > 0.3
    cache_span.set_tag("cache.hit", cache_hit)
    time.sleep(random.uniform(0.001, 0.002))
    cache_span.finish()

    if not cache_hit:
        db_span = tracer.start_span("postgres.query users", "auth-service", span)
        db_span.set_tag("db.statement", "SELECT * FROM users WHERE token = $1")
        time.sleep(random.uniform(0.003, 0.010))
        db_span.finish()

    span.set_tag("auth.user_id", 4521)
    span.finish()


def order_service(tracer, parent):
    span = tracer.start_span("get_order", "order-service", parent)
    span.set_tag("order.id", 789)

    time.sleep(random.uniform(0.002, 0.005))

    db_span = tracer.start_span("postgres.query orders", "order-service", span)
    db_span.set_tag("db.statement", "SELECT * FROM orders WHERE id = $1")
    time.sleep(random.uniform(0.005, 0.015))
    db_span.finish()

    payment_service(tracer, span)
    inventory_service(tracer, span)

    span.finish()


def payment_service(tracer, parent):
    span = tracer.start_span("get_payment_status", "payment-service", parent)
    span.set_tag("payment.provider", "stripe")

    time.sleep(random.uniform(0.002, 0.005))

    ext_span = tracer.start_span("HTTP GET stripe.com/v1/charges", "payment-service", span)
    ext_span.set_tag("http.method", "GET")
    ext_span.set_tag("peer.service", "stripe-api")
    latency = random.uniform(0.015, 0.040)
    time.sleep(latency)

    if random.random() < 0.1:
        ext_span.set_error("Stripe timeout after 30ms")
        ext_span.set_tag("http.status_code", 504)
    else:
        ext_span.set_tag("http.status_code", 200)
    ext_span.finish()

    span.finish()


def inventory_service(tracer, parent):
    span = tracer.start_span("check_inventory", "inventory-service", parent)
    span.set_tag("warehouse", "us-east-1")

    cache_span = tracer.start_span("redis.get inventory_cache", "inventory-service", span)
    time.sleep(random.uniform(0.001, 0.003))
    cache_span.set_tag("cache.hit", True)
    cache_span.finish()

    span.finish()


# ---------------------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------------------

def render_trace_tree(tracer, trace_id):
    spans = tracer.get_trace(trace_id)
    if not spans:
        return

    root = [s for s in spans if s.parent_id is None][0]
    trace_start = root.start_time

    max_duration = max(s.duration_ms for s in spans)
    bar_width = 40

    print(f"\nTrace ID: {trace_id}")
    print(f"{'Service':<22} {'Span':<30} {'Duration':>8}  Timeline")
    print("-" * 110)

    def render_span(span, depth=0):
        indent = "  " * depth + ("+-" if depth > 0 else "")
        offset = (span.start_time - trace_start) * 1000
        dur = span.duration_ms

        offset_chars = int((offset / max(max_duration, 1)) * bar_width) if max_duration > 0 else 0
        dur_chars = max(1, int((dur / max(max_duration, 1)) * bar_width)) if max_duration > 0 else 1

        status_marker = "\033[31mX\033[0m" if span.status == "ERROR" else ""
        bar = " " * offset_chars + "\033[36m" + "=" * dur_chars + "\033[0m"

        name_display = f"{indent}{span.name}"
        print(f"  {span.service:<20} {name_display:<30} {dur:>6.1f}ms  |{bar}| {status_marker}")

        children = [s for s in spans if s.parent_id == span.span_id]
        children.sort(key=lambda s: s.start_time)
        for child in children:
            render_span(child, depth + 1)

    render_span(root)


def print_span_details(tracer, trace_id):
    spans = tracer.get_trace(trace_id)

    print(f"\nSPAN DETAILS ({len(spans)} spans)")
    print("=" * 80)

    for span in sorted(spans, key=lambda s: s.start_time):
        parent_info = f"parent={span.parent_id}" if span.parent_id else "ROOT"
        status_color = "\033[31m" if span.status == "ERROR" else "\033[32m"

        print(f"\n  [{span.span_id}] {span.service} / {span.name}")
        print(f"    {parent_info} | {status_color}{span.status}\033[0m | {span.duration_ms:.1f}ms")

        if span.tags:
            tags_str = ", ".join(f"{k}={v}" for k, v in span.tags.items())
            print(f"    tags: {tags_str}")


# ---------------------------------------------------------------------------
# Run the demo
# ---------------------------------------------------------------------------

def main():
    print("Distributed Tracing - microservice span propagation")
    print("=" * 60)

    tracer = Tracer()

    print("\nSimulating request: GET /api/order/789")
    print("Request flows: gateway -> auth -> order -> payment -> inventory\n")

    root = api_gateway(tracer)

    render_trace_tree(tracer, root.trace_id)
    print_span_details(tracer, root.trace_id)

    print(f"\n{'=' * 60}")
    print("W3C TRACE CONTEXT HEADERS (propagated between services)")
    print(f"{'=' * 60}")
    print(f"  traceparent: 00-{root.trace_id}-{root.span_id}-01")
    print(f"  tracestate: vendor=example")

    total_ms = root.duration_ms
    spans = tracer.get_trace(root.trace_id)
    errors = [s for s in spans if s.status == "ERROR"]
    services = set(s.service for s in spans)

    print(f"\n  Total latency:  {total_ms:.1f}ms")
    print(f"  Total spans:    {len(spans)}")
    print(f"  Services hit:   {len(services)} ({', '.join(sorted(services))})")
    print(f"  Errors:         {len(errors)}")


if __name__ == "__main__":
    main()
