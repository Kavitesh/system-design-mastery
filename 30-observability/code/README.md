# Monitoring, Logging & Observability - Code Lab

Hands-on demos covering the three pillars of observability plus SLO-based alerting.

## What's Included

| File | Description |
|------|-------------|
| `metrics_collector.py` | Prometheus-style metrics with counters, gauges, and histograms |
| `structured_logging.py` | JSON structured logging with correlation IDs and log levels |
| `distributed_tracing.py` | Trace propagation across simulated microservices with span tree visualization |
| `alerting_system.py` | SLO-based alerting with burn rate and error budget tracking |

## Prerequisites

```bash
pip install flask requests
```

No external dependencies beyond the standard library for most demos. Flask is only needed if you want to extend the examples into live HTTP services.

## Running the Demos

### 1. Metrics Collector

Simulates a Prometheus-style metrics system with counter, gauge, and histogram types:

```bash
python metrics_collector.py
```

Watch it track request counts, active connections, and latency distributions across simulated traffic.

### 2. Structured Logging

Demonstrates the difference between unstructured and structured logging, with correlation ID propagation:

```bash
python structured_logging.py
```

Outputs JSON log lines you could pipe straight into Elasticsearch or Loki.

### 3. Distributed Tracing

Simulates a multi-service request flow with trace and span ID propagation:

```bash
python distributed_tracing.py
```

Visualizes the full span tree showing parent-child relationships and timing.

### 4. Alerting System

Simulates SLO monitoring with error budget burn rate alerting:

```bash
python alerting_system.py
```

Shows how burn rate alerting detects incidents faster than static threshold alerts.
