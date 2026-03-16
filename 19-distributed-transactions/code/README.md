# Distributed Transactions - Code Lab

Hands-on simulations of distributed transaction patterns: 2PC, Saga (orchestrator and choreography), and the transactional outbox.

## What's Included

| File | Description |
|------|-------------|
| `two_phase_commit.py` | 2PC simulation with coordinator, participants, success and failure paths |
| `saga_orchestrator.py` | Saga pattern with a central orchestrator managing steps and compensations |
| `saga_choreography.py` | Event-driven saga where services react to events independently |
| `outbox_pattern.py` | Transactional outbox pattern ensuring reliable event publishing |

## Prerequisites

```bash
pip install sqlite3  # built-in, no install needed
```

No external dependencies - all demos use Python's standard library.

## Running the Demos

### 1. Two-Phase Commit

Simulates a coordinator managing a distributed transaction across three participants. Runs success, participant failure, and coordinator timeout scenarios:

```bash
python two_phase_commit.py
```

### 2. Saga Orchestrator

An orchestrator drives a trip booking saga (flight, hotel, car rental, payment). Watch it handle failures by running compensating transactions in reverse:

```bash
python saga_orchestrator.py
```

### 3. Saga Choreography

Event-driven saga where an order flows through payment, inventory, and shipping services. Each service reacts to events and publishes its own:

```bash
python saga_choreography.py
```

### 4. Outbox Pattern

Demonstrates the dual-write problem and how the outbox pattern solves it. Uses SQLite to show atomic writes of business data alongside event records:

```bash
python outbox_pattern.py
```
