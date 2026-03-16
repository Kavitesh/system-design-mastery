# Chapter 17 - Code Labs: Disaster Recovery & Backup

Hands-on Python simulations for disaster recovery and backup strategies.

## Labs

| # | File | Description |
|---|---|---|
| 1 | `backup_strategies.py` | Simulates full, incremental, and differential backup strategies with size and time comparisons |
| 2 | `rpo_rto_calculator.py` | Interactive calculator showing RPO/RTO tradeoffs for different DR strategies |
| 3 | `dr_simulation.py` | Simulates disaster scenarios and recovery with different DR strategies |
| 4 | `failover_orchestrator.py` | Automated failover orchestrator with health monitoring and region switching |

## Running the Labs

Each lab is standalone. Run with Python 3.8+:

```bash
python backup_strategies.py
python rpo_rto_calculator.py
python rpo_rto_calculator.py --strategy pilot-light --data-size 500
python dr_simulation.py
python failover_orchestrator.py
```

No external dependencies required - all labs use the Python standard library.
