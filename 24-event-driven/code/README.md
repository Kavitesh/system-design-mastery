# Event-Driven Architecture - Code Lab

Hands-on demos covering event buses, event sourcing, CQRS, and choreography vs orchestration.

## What's Included

| File | Description |
|------|-------------|
| `event_bus.py` | In-memory event bus with publish/subscribe, event history, and replay |
| `event_sourcing.py` | Event-sourced bank account - rebuild state from immutable events |
| `cqrs_demo.py` | CQRS pattern with separate write model and denormalized read views |
| `choreography_vs_orchestration.py` | Same order flow implemented both ways for comparison |

## Prerequisites

```bash
pip install flask
```

## Running the Demos

### 1. Event Bus

Publish events, subscribe handlers, inspect history, and replay events:

```bash
python event_bus.py
```

### 2. Event Sourcing

Bank account built entirely from events - deposits, withdrawals, balance reconstruction:

```bash
python event_sourcing.py
```

### 3. CQRS Demo

Separate write model (normalized) and read models (denormalized views) with projections:

```bash
python cqrs_demo.py
```

### 4. Choreography vs Orchestration

The same order processing workflow built two different ways - see the trade-offs firsthand:

```bash
python choreography_vs_orchestration.py
```
