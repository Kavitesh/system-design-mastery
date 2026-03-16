# Load Balancing - Code Lab

Hands-on demos implementing load balancing algorithms from scratch, simulating traffic distribution, and building a health-checked failover system.

## What's Included

| File | Description |
|------|-------------|
| `lb_algorithms.py` | Implements round-robin, weighted round-robin, least-connections, and IP hash algorithms |
| `lb_simulator.py` | Simulates traffic across servers with different algorithms and compares distribution |
| `health_check.py` | Flask app with multiple backends, active health checks, and automatic failover |
| `consistent_hash_lb.py` | Consistent hashing load balancer showing how nodes join/leave affects distribution |

## Prerequisites

```bash
pip install flask
```

No other dependencies needed - all algorithms are built from scratch using the standard library.

## Running the Demos

### 1. Load Balancing Algorithms

Demonstrates each algorithm in isolation with a small server pool:

```bash
python lb_algorithms.py
```

### 2. Traffic Simulator

Runs 10,000 requests through each algorithm and shows the resulting traffic distribution across servers:

```bash
python lb_simulator.py
```

### 3. Health Check and Failover

Starts a Flask app simulating three backend servers. Servers can be toggled healthy/unhealthy, and the load balancer automatically reroutes traffic:

```bash
python health_check.py
```

Then visit `http://localhost:5060` for the API.

### 4. Consistent Hashing

Shows how consistent hashing minimizes redistribution when servers join or leave, compared to simple modulo hashing:

```bash
python consistent_hash_lb.py
```
