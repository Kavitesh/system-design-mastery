# Service Mesh & Sidecar Pattern - Code Lab

Hands-on simulations of service mesh concepts: sidecar proxying, traffic splitting, mutual TLS, and distributed observability.

## What's Included

| File | Description |
|------|-------------|
| `sidecar_proxy.py` | Flask-based sidecar proxy that intercepts requests, adds headers, and logs metrics |
| `traffic_splitting.py` | Canary deployment simulation with configurable traffic split (90/10) |
| `mtls_demo.py` | Simulates mutual TLS authentication between services via sidecar proxies |
| `mesh_observability.py` | Distributed tracing simulation collecting latency and error metrics across services |

## Prerequisites

```bash
pip install flask requests
```

No external dependencies beyond Flask and requests. All demos are self-contained.

## Running the Demos

### 1. Sidecar Proxy

Shows how a sidecar intercepts HTTP traffic, injects headers (request ID, trace ID), enforces timeouts, and collects metrics - all without modifying the application:

```bash
python sidecar_proxy.py
```

### 2. Traffic Splitting (Canary Deployment)

Simulates a canary deployment where 90% of traffic goes to the stable version and 10% to the canary. Tracks error rates per version:

```bash
python traffic_splitting.py
```

### 3. Mutual TLS (mTLS)

Simulates the mTLS handshake between two services through their sidecar proxies. Demonstrates certificate verification, identity validation, and what happens when certificates are invalid:

```bash
python mtls_demo.py
```

### 4. Mesh Observability

Simulates a chain of microservice calls with distributed tracing. Collects per-service latency, error rates, and trace propagation across a multi-service request path:

```bash
python mesh_observability.py
```
