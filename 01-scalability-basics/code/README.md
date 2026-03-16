# Scalability Basics  - Code Lab

A hands-on simulation demonstrating vertical scaling, horizontal scaling, and Amdahl's Law.

## What's Included

| File | Description |
|------|-------------|
| `scalability_sim.py` | Simulates vertical vs horizontal scaling with load |
| `amdahls_law.py` | Interactive visualization of Amdahl's Law |
| `stateless_server.py` | A simple stateless Flask API server demo |

## Prerequisites

```bash
pip install flask requests matplotlib
```

## Running the Demos

### 1. Scalability Simulation

Simulates processing requests with 1 server (vertical) vs N servers (horizontal):

```bash
python scalability_sim.py
```

### 2. Amdahl's Law Calculator

Shows the theoretical speedup limit based on parallelizable fraction:

```bash
python amdahls_law.py
```

### 3. Stateless Server Demo

Run multiple instances behind a simple round-robin to see horizontal scaling in action:

```bash
# Terminal 1  - start server on port 5001
python stateless_server.py 5001

# Terminal 2  - start server on port 5002
python stateless_server.py 5002

# Terminal 3  - send requests (round-robin across both servers)
python load_test.py
```
