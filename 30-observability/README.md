# Chapter 30 - Monitoring, Logging & Observability

> You can't fix what you can't see. Production systems fail in weird, unpredictable ways - and the teams that recover fastest are the ones that built observability in from day one, not bolted it on after the first outage.

📖 [Read on Medium](#) · 🎬 [Watch on YouTube](#)

---

## Monitoring vs Observability

Most people use these words interchangeably. They shouldn't.

**Monitoring** tells you *when* something is broken. You define checks upfront - CPU over 90%, error rate above 1%, disk filling up - and get alerts when thresholds are crossed. It answers known questions.

**Observability** lets you ask *why* something is broken, even if you've never seen that failure before. It's the ability to understand a system's internal state from its external outputs. It answers unknown questions.

| Aspect | Monitoring | Observability |
|--------|-----------|---------------|
| Approach | Predefined checks | Exploratory investigation |
| Questions | Known unknowns | Unknown unknowns |
| Scope | "Is this thing broken?" | "Why is this thing broken?" |
| Setup | Dashboards and alerts | Instrumented telemetry data |
| Example | "Error rate spiked to 5%" | "Errors spike only for users in EU, on iOS, hitting the /checkout endpoint, when the payment service's connection pool is exhausted" |

Monitoring is a subset of observability. You need both.

---

## The Three Pillars of Observability

Every observability system rests on three types of telemetry data. Miss one and you're flying partially blind.

```
┌─────────────────────────────────────────────────────────┐
│                   OBSERVABILITY                          │
│                                                          │
│   ┌───────────┐   ┌───────────┐   ┌───────────┐        │
│   │  METRICS   │   │   LOGS    │   │  TRACES   │        │
│   │           │   │           │   │           │        │
│   │ What is   │   │ What      │   │ What path │        │
│   │ happening │   │ happened  │   │ did it    │        │
│   │ right now │   │ exactly   │   │ take      │        │
│   └───────────┘   └───────────┘   └───────────┘        │
│                                                          │
│   Counters         Structured       Spans               │
│   Gauges           JSON             Trace IDs           │
│   Histograms       Correlation IDs  Parent-child        │
└─────────────────────────────────────────────────────────┘
```

### Pillar 1: Metrics

Metrics are **numeric measurements** collected over time. They're cheap to store, fast to query, and the backbone of dashboards and alerts.

**Four metric types:**

| Type | What It Measures | Example | Goes Up? Goes Down? |
|------|-----------------|---------|-------------------|
| **Counter** | Cumulative total | Total HTTP requests served | Only up (resets on restart) |
| **Gauge** | Current value | Active connections right now | Up and down |
| **Histogram** | Distribution of values | Request latency buckets | Accumulates into buckets |
| **Summary** | Quantiles over a window | p99 latency over 5 min | Rolling calculation |

**Counter vs Gauge** is the most important distinction. Counters always go up - you derive rates from them (requests per second). Gauges bounce around - they capture a snapshot (memory usage, queue depth, active threads).

**Histograms vs Summaries** is subtler. Histograms let the server aggregate across instances; summaries compute quantiles client-side and can't be aggregated. Prefer histograms unless you have a specific reason for summaries.

### Pillar 2: Logs

Logs are **timestamped records** of discrete events. They give you the narrative - the exact sequence of what happened.

**Structured logging** is non-negotiable for production. Unstructured logs look like this:

```
2024-03-15 10:23:45 ERROR Failed to process payment for user 12345
```

Structured logs look like this:

```json
{
  "timestamp": "2024-03-15T10:23:45.123Z",
  "level": "ERROR",
  "message": "Payment processing failed",
  "user_id": 12345,
  "payment_id": "pay_abc123",
  "amount": 49.99,
  "error": "card_declined",
  "trace_id": "abc123def456",
  "service": "payment-service",
  "host": "prod-pay-03"
}
```

The second one is searchable, filterable, and aggregatable. The first one requires regex and hope.

**Log levels and when to use each:**

| Level | When to Use | Example |
|-------|------------|---------|
| **DEBUG** | Development only, verbose details | "Parsed request body: {fields}" |
| **INFO** | Normal operations worth recording | "Order #456 created for user #123" |
| **WARNING** | Something unexpected but handled | "Retry 2/3 for payment gateway timeout" |
| **ERROR** | Operation failed, needs attention | "Database connection refused on host db-03" |
| **CRITICAL** | System is going down | "Out of memory - shutting down" |

The rule of thumb: if you get paged for it, it's ERROR or CRITICAL. If you'd want to know about it during an incident investigation, it's INFO. If it's only useful during development, it's DEBUG. WARNING is for "this worked, but barely."

### Pillar 3: Distributed Traces

Traces follow a single request as it moves through multiple services. In a microservices architecture, one user action might hit 10+ services. Without tracing, debugging latency is pure guesswork.

**Key concepts:**

- **Trace** - the entire journey of a request, identified by a **trace ID**
- **Span** - a single operation within a trace (e.g., "query the database"), identified by a **span ID**
- **Parent span** - the span that triggered this one, linking spans into a tree

```
Trace ID: abc-123
│
├── [Span 1] API Gateway (2ms)
│   ├── [Span 2] Auth Service (5ms)
│   │   └── [Span 3] Token validation (3ms)
│   └── [Span 4] Order Service (45ms)
│       ├── [Span 5] Database query (12ms)
│       └── [Span 6] Payment Service (28ms)
│           └── [Span 7] Stripe API call (25ms)
```

The trace ID propagates through HTTP headers (`traceparent` in the W3C standard, `X-B3-TraceId` in Zipkin). Each service creates its own spans and passes the trace context downstream.

---

## Metrics Methodologies

Two frameworks dominate how engineers think about what to measure.

### The RED Method (Request-driven)

Built for request-driven services (APIs, web servers). Track three things:

| Signal | What to Measure | Why |
|--------|----------------|-----|
| **Rate** | Requests per second | Tells you traffic volume |
| **Errors** | Failed requests per second | Tells you reliability |
| **Duration** | Latency distribution (p50, p95, p99) | Tells you user experience |

RED works because most services exist to serve requests. If you know the rate, error rate, and latency distribution, you know the health of a service.

### The USE Method (Resource-driven)

Built for infrastructure components (CPU, memory, disk, network). Track three things:

| Signal | What to Measure | Why |
|--------|----------------|-----|
| **Utilization** | % of resource capacity in use | Tells you how full it is |
| **Saturation** | Work that's queued / waiting | Tells you if it's overloaded |
| **Errors** | Resource-level error count | Tells you if it's broken |

Use RED for your services, USE for your infrastructure. Together they cover the full picture.

---

## SLIs, SLOs, and Error Budgets

Google's SRE book formalized this approach, and it's now the industry standard for reliability engineering.

**SLI (Service Level Indicator)** - A quantitative measurement of service behavior. "The proportion of requests that complete in under 200ms."

**SLO (Service Level Objective)** - A target value for an SLI. "99.9% of requests should complete in under 200ms."

**SLA (Service Level Agreement)** - A contract with consequences. "If we drop below 99.9% availability, we refund 10% of the bill." SLAs are business documents. SLOs are engineering targets. SLOs should always be tighter than SLAs.

**Error budgets** make SLOs actionable:

```
Error Budget = 1 - SLO target

Example: SLO = 99.9% availability
Error Budget = 0.1% = ~43 minutes of downtime per month

If you've used 30 minutes of your budget this month:
  - Remaining: 13 minutes
  - Action: Slow down deployments, prioritize reliability

If you've used 5 minutes of your budget:
  - Remaining: 38 minutes
  - Action: Ship features, take calculated risks
```

Error budgets create a shared language between product and engineering. Product wants to ship features. Engineering wants stability. The error budget tells you which one to prioritize right now.

**Burn rate** measures how fast you're consuming your error budget:

- Burn rate 1.0 = consuming budget at exactly the expected rate
- Burn rate 2.0 = consuming budget twice as fast (you'll exhaust it in half the time)
- Burn rate 10.0 = something is very wrong, alert immediately

---

## The Observability Stack

### Prometheus + Grafana (Metrics)

Prometheus is the de facto standard for metrics collection. It uses a **pull model** - Prometheus scrapes metrics endpoints on your services.

```
┌──────────┐    scrape     ┌──────────────┐
│ Service A │◄─────────────│              │
└──────────┘               │              │    ┌──────────┐
                           │  Prometheus  │───►│ Grafana  │
┌──────────┐    scrape     │              │    │(dashboards│
│ Service B │◄─────────────│              │    └──────────┘
└──────────┘               └──────┬───────┘
                                  │
┌──────────┐    scrape            │
│ Service C │◄────────────────────┘
└──────────┘
```

**Why pull over push?** Pull lets Prometheus decide the scrape interval. If a target is down, Prometheus knows immediately (failed scrape). Push models can't distinguish "service is healthy but idle" from "service is dead."

PromQL (Prometheus Query Language) is powerful but has a learning curve:

```promql
# Request rate over 5 minutes
rate(http_requests_total[5m])

# Error percentage
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) * 100

# 95th percentile latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

### ELK Stack (Logs)

Elasticsearch, Logstash, and Kibana - the classic logging pipeline:

- **Elasticsearch** - stores and indexes log data for fast full-text search
- **Logstash** - ingests, transforms, and ships logs (increasingly replaced by Fluentd or Vector)
- **Kibana** - visualization and exploration UI

Modern alternatives: **Loki** (by Grafana Labs) is cheaper because it only indexes labels, not full text. For most teams, Loki + Grafana is more practical than a full ELK deployment.

### Distributed Tracing (Jaeger / Zipkin)

Both implement the OpenTracing standard. Jaeger (originally from Uber) has better scaling characteristics. Zipkin (from Twitter) is simpler to deploy.

### OpenTelemetry - The Convergence

OpenTelemetry (OTel) is merging all three pillars into one instrumentation framework. It provides:

- Vendor-neutral APIs and SDKs for metrics, logs, and traces
- Auto-instrumentation for popular frameworks
- A collector that can export to any backend

If you're starting from scratch today, use OpenTelemetry. It's the future of observability instrumentation, backed by every major vendor.

---

## Alerting Best Practices

Bad alerting is worse than no alerting. Alert fatigue is real - when every alert is "urgent," none of them are.

### The Alerting Hierarchy

```
┌─────────────────────────────────────────────┐
│  PAGE (wake someone up at 3am)              │
│  - Service is DOWN for users                │
│  - Error budget burning at 10x+ rate        │
│  - Data loss or security breach             │
├─────────────────────────────────────────────┤
│  TICKET (fix within business hours)         │
│  - Error budget burning at 2-5x rate        │
│  - Degraded but functional                  │
│  - Capacity trending toward limits          │
├─────────────────────────────────────────────┤
│  LOG (record for investigation)             │
│  - Transient errors that self-resolve       │
│  - Expected operational events              │
│  - Performance fluctuations in normal range │
└─────────────────────────────────────────────┘
```

### Rules for Sustainable Alerting

1. **Alert on symptoms, not causes.** Alert on "users are getting 500 errors" not "CPU is at 80%." High CPU that doesn't affect users isn't an alert.

2. **Every alert needs a runbook.** If the on-call engineer can't do anything about it, don't page them.

3. **Use multi-window burn rates.** A 1-minute spike isn't the same as 30 minutes of elevated errors. Use fast burns (high threshold, short window) and slow burns (lower threshold, longer window).

4. **Delete noisy alerts.** Track alert frequency. If an alert fires and gets dismissed without action more than 50% of the time, fix it or remove it.

5. **Err on the side of fewer alerts.** It's better to miss a minor issue than to train your team to ignore pages.

---

## Real-World Examples

### Google SRE

Google popularized error budgets and SLO-based alerting. Their approach:

- Every service has an SLO. No exceptions.
- If the error budget is exhausted, feature work stops until reliability improves.
- SRE teams can hand back a service to the dev team if reliability targets aren't met.
- They measure **global** metrics, not per-server. A single unhealthy server doesn't matter if user experience is fine.

### Netflix

Netflix processes billions of events per day across hundreds of microservices. Their observability stack:

- **Atlas** - custom time-series database handling 2.5 billion metrics per minute
- **Edgar** - distributed tracing system that correlates traces with device-level logs
- **Mantis** - real-time stream processing for operational events
- They invest heavily in **correlation** - connecting metrics spikes to specific traces to specific log entries

### Uber

Uber built **M3** for metrics at extreme scale:

- Handles tens of billions of data points per day
- Stores metrics with 10-second resolution
- Uses a custom aggregation tier to pre-compute common queries
- Open-sourced as M3DB

---

## Common Pitfalls

| Pitfall | Why It Hurts | Fix |
|---------|-------------|-----|
| **Logging everything** | Storage costs explode, signal drowns in noise | Sample high-volume events, keep structured fields lean |
| **Metric cardinality explosion** | Adding user_id as a label creates millions of time series | Only use bounded values as labels (status code, region - not user ID) |
| **No correlation IDs** | Can't connect logs from different services for the same request | Generate a trace ID at the edge, propagate through all services |
| **Dashboards nobody checks** | Vanity metrics feel productive but waste time | Every dashboard should answer a specific question |
| **Alert fatigue** | Team starts ignoring pages, real incidents get missed | Fewer, better alerts with clear runbooks |
| **Monitoring only happy paths** | You catch errors but miss slowness | Track latency percentiles (p95, p99), not just averages |
| **No baseline** | You can't tell if current behavior is abnormal | Record baselines during normal operation, compare against them |
| **Sampling too aggressively** | Rare errors disappear from your data | Use tail-based sampling - keep interesting traces, drop boring ones |

---

## Structured Logging - Do It Right

A practical guide to structured logging that will save you during your next incident.

### Correlation IDs

Every request gets a unique ID at the edge. Every service includes it in every log line. This lets you reconstruct the entire journey:

```
# At the API gateway
correlation_id = generate_uuid()
response.headers["X-Correlation-ID"] = correlation_id

# In every downstream service
logger.info("Processing order", extra={
    "correlation_id": request.headers["X-Correlation-ID"],
    "order_id": order.id,
    "user_id": user.id
})
```

### What to Log at Each Level

**INFO** - Business events: "User signed up," "Order placed," "Payment processed"

**WARNING** - Recoverable issues: "Circuit breaker opened," "Rate limit approaching," "Retry succeeded on attempt 3"

**ERROR** - Failures requiring investigation: "Payment declined," "Database query timeout," "External API returned 503"

**DEBUG** - Diagnostic details: "Cache hit/miss," "SQL query text," "Request/response bodies"

Keep DEBUG off in production unless you're actively investigating. The volume will crush your log pipeline.

---

## Key Takeaways

1. **Observability > Monitoring** - Monitoring answers known questions; observability lets you investigate the unknown
2. **Three pillars work together** - Metrics for detection, logs for context, traces for causation
3. **Structured logging is mandatory** - If your logs aren't structured JSON with correlation IDs, fix that first
4. **Use RED for services, USE for infrastructure** - These frameworks prevent you from measuring the wrong things
5. **SLOs drive alerting** - Alert on error budget burn rate, not arbitrary thresholds
6. **Fewer alerts, better alerts** - Every page should be actionable. Alert fatigue kills reliability culture
7. **OpenTelemetry is the future** - One instrumentation framework for metrics, logs, and traces
8. **Cardinality is the enemy of metrics** - Keep label values bounded or your storage costs will destroy you

---

## What's Next?

- **Chapter 31:** [Design a URL Shortener](../31-url-shortener/) - Your first end-to-end system design, applying everything you've learned about scalability, databases, caching, and observability
