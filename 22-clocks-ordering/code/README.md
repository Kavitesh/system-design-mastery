# Clocks & Ordering - Code Lab

Hands-on simulations of clock mechanisms used in distributed systems - from physical clock drift to Lamport clocks, vector clocks, and Hybrid Logical Clocks.

## What's Included

| File | Description |
|------|-------------|
| `clock_drift.py` | Simulates physical clock drift and shows why wall clocks can't be trusted for ordering |
| `lamport_clock.py` | Lamport clock simulation with multiple processes exchanging messages |
| `vector_clock.py` | Vector clock implementation that detects concurrent events |
| `hybrid_clock.py` | Hybrid Logical Clock combining physical and logical timestamps |

## Prerequisites

No external dependencies - all demos use Python's standard library.

```bash
python --version  # Python 3.7+
```

## Running the Demos

### 1. Clock Drift Simulation

Shows how physical clocks diverge over time and why comparing timestamps across machines produces wrong ordering:

```bash
python clock_drift.py
```

### 2. Lamport Clock Simulation

Simulates three processes exchanging messages with Lamport timestamps. Shows how logical clocks establish total ordering:

```bash
python lamport_clock.py
```

### 3. Vector Clock Simulation

Demonstrates concurrent event detection. Two processes write independently - vector clocks identify the conflict:

```bash
python vector_clock.py
```

### 4. Hybrid Logical Clock

Combines wall-clock time with logical counters. Shows how HLCs stay close to physical time while preserving causality:

```bash
python hybrid_clock.py
```
