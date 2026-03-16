# Fault Tolerance & High Availability - Code Lab

Hands-on demos covering health checks, failover detection, SLA calculations, and graceful degradation. Everything runs locally with no external dependencies.

## What's Included

| File | Description |
|------|-------------|
| `health_checker.py` | Health check system with liveness and readiness probes monitoring multiple services |
| `failover_demo.py` | Active-passive failover simulation with heartbeat detection and automatic promotion |
| `sla_calculator.py` | SLA/uptime calculator showing what each level of nines means in practice |
| `graceful_degradation.py` | Flask app that degrades gracefully when backend dependencies fail |

## Prerequisites

```bash
pip install flask requests
```

All demos use in-process simulations - no databases or external services needed.

## Running the Demos

### 1. Health Checker

Monitors multiple services with independent liveness and readiness probes:

```bash
python health_checker.py
```

Watch services go through healthy, degraded, and failed states. The checker distinguishes between "restart this process" (liveness failure) and "stop sending traffic" (readiness failure).

### 2. Failover Demo

Simulates an active-passive database cluster with heartbeat-based failure detection:

```bash
python failover_demo.py
```

The primary processes writes while the standby replicates. When the primary dies, the standby detects the missing heartbeats and promotes itself.

### 3. SLA Calculator

Calculates real downtime numbers for each availability level:

```bash
python sla_calculator.py
```

Shows what 99.9%, 99.99%, and 99.999% actually mean in hours, minutes, and seconds - plus cost-of-downtime estimates and composite system availability.

### 4. Graceful Degradation

A Flask API that keeps serving requests even when its dependencies fail:

```bash
python graceful_degradation.py
```

Then hit the endpoints to see degradation in action:

```bash
curl http://localhost:5014/products        # Full functionality
curl http://localhost:5014/fail/recommend   # Kill the recommendation service
curl http://localhost:5014/products        # Degraded - shows popular items instead
curl http://localhost:5014/fail/inventory   # Kill inventory too
curl http://localhost:5014/products        # Further degraded - cached stock levels
curl http://localhost:5014/status          # See which services are up/down
curl http://localhost:5014/recover/all     # Bring everything back
```
