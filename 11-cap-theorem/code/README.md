# CAP Theorem & Consistency Models - Code Lab

Hands-on simulations that make CAP tradeoffs tangible. Each demo runs a cluster of in-memory nodes and lets you watch what happens when partitions strike.

## What's Included

| File | Description |
|------|-------------|
| `cap_simulator.py` | Interactive CAP simulation - trigger partitions and watch CP vs AP behavior |
| `consistency_models.py` | Side-by-side comparison of strong, eventual, and causal consistency |
| `tunable_consistency.py` | Quorum system where you set W and R per operation and observe the tradeoffs |
| `pacelc_demo.py` | Shows system behavior during partitions vs normal operation (PACELC) |

## Prerequisites

No external dependencies. All demos use Python's standard library.

```bash
python --version  # 3.8+
```

## Running the Demos

### 1. CAP Simulator

Spins up a 3-node cluster and walks you through partition scenarios. You'll see a CP system reject requests and an AP system serve stale data.

```bash
python cap_simulator.py
```

### 2. Consistency Models

Runs the same workload through strong, eventual, and causal consistency models. Watch how reads behave differently under each model.

```bash
python consistency_models.py
```

### 3. Tunable Consistency

A 5-node quorum system where you control the consistency level (ONE, QUORUM, ALL). See how R + W > N determines whether you get stale reads.

```bash
python tunable_consistency.py
```

### 4. PACELC Demo

Compares a PA/EL system (like Cassandra) with a PC/EC system (like ZooKeeper). Shows behavior during partition and during normal operation.

```bash
python pacelc_demo.py
```

## Key Things to Watch For

- **CP mode:** Notice how the system returns errors during partitions. No stale data, but reduced availability.
- **AP mode:** Notice how reads return old values during partitions, then converge after healing.
- **Quorum math:** Try W=1, R=1 and watch stale reads appear. Then try W=2, R=2 and watch them disappear.
- **PACELC:** Compare the latency numbers during normal operation. EC systems are slower even when nothing is broken.
