# Chapter 18 - Distributed Consensus - Code Labs

Hands-on Python demos exploring consensus algorithms, leader election, and coordination patterns.

## Labs

| # | File | Description | Concepts |
|---|---|---|---|
| 1 | `raft_election.py` | Simplified Raft leader election with terms, votes, and randomized timeouts | Terms, RequestVote, majority quorum, election timeout |
| 2 | `log_replication.py` | Raft-style log replication across a cluster with commit tracking | AppendEntries, commit index, log matching, majority ack |
| 3 | `split_brain.py` | Demonstrates split-brain during network partition and fencing token fix | Network partition, dual leaders, fencing tokens, data divergence |
| 4 | `service_registry.py` | ZooKeeper-like service registry with ephemeral nodes and watches | Ephemeral nodes, watches, session TTL, service discovery |

## Running the Labs

Each lab is standalone - no external dependencies required beyond Python 3.7+.

```bash
python raft_election.py
python log_replication.py
python split_brain.py
python service_registry.py
```

## What to Look For

- **raft_election.py** - Watch how randomized timeouts break symmetry and one node wins leadership. Run it multiple times to see different nodes win.
- **log_replication.py** - See how entries only commit after majority acknowledgment. Notice what happens when a node falls behind and catches up.
- **split_brain.py** - First see the disaster when two leaders write independently, then see how fencing tokens prevent stale writes.
- **service_registry.py** - Observe how ephemeral nodes disappear when services crash, and watches notify other services immediately.
