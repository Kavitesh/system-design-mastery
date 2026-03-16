# Chapter 25 - Serverless Architecture - Code Lab

Hands-on Python simulations of serverless concepts. No cloud account required.

## Files

| File | Purpose | Key Concepts |
|------|---------|-------------|
| `lambda_simulator.py` | Simulates a FaaS runtime environment | Cold/warm starts, timeouts, memory limits, container lifecycle |
| `serverless_api.py` | Flask app structured as serverless functions | Function isolation, independent scaling, handler pattern |
| `cold_start_benchmark.py` | Benchmarks cold vs warm start latency | Performance impact, language comparison simulation, statistics |
| `event_triggers.py` | Event-driven function execution | S3 events, API triggers, cron schedules, queue messages |

## Quick Start

```bash
pip install flask
```

Run any file standalone:

```bash
python lambda_simulator.py
python serverless_api.py       # starts Flask on port 5000
python cold_start_benchmark.py
python event_triggers.py
```

## What You'll Learn

1. **Why cold starts matter** - see the real latency difference between first and subsequent invocations
2. **How FaaS containers work** - the lifecycle of spin-up, execute, idle, recycle
3. **Event-driven patterns** - how different event sources trigger different function behaviors
4. **Serverless API design** - structuring HTTP endpoints as independent, isolated functions
