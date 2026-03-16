# Chapter 10 - Code Lab: Database Replication

Hands-on simulations of replication concepts. Each script is standalone and
runs without external dependencies (pure Python, no pip install needed).

---

## Files

| File                    | What It Demonstrates                                      |
|-------------------------|-----------------------------------------------------------|
| `leader_follower.py`    | Leader-follower replication with sync and async modes      |
| `quorum_demo.py`        | Quorum reads/writes with configurable W, R, N values       |
| `conflict_resolution.py`| Last-write-wins, version vectors, and custom merge         |
| `failover_sim.py`       | Leader failure detection and automatic failover            |

---

## Running the Labs

Each file runs directly with Python 3.7+:

```bash
python leader_follower.py
python quorum_demo.py
python conflict_resolution.py
python failover_sim.py
```

No virtual environment or third-party packages required.

---

## Lab 1: Leader-Follower Replication

`leader_follower.py` simulates a leader node that accepts writes and
replicates them to follower nodes. You can switch between synchronous and
asynchronous replication to observe the trade-offs firsthand.

In synchronous mode, every write blocks until all followers confirm. In
asynchronous mode, the leader returns immediately and followers catch up
in the background - introducing visible replication lag.

The simulation shows how a read from a follower can return stale data when
replication lag is present.

---

## Lab 2: Quorum Reads and Writes

`quorum_demo.py` implements the quorum formula W + R > N. You configure the
number of replicas (N), write quorum (W), and read quorum (R), then observe
whether reads return consistent data.

The demo runs through several configurations - the classic N=3/W=2/R=2
balanced setup, a write-heavy N=3/W=1/R=3 configuration, and an unsafe
N=3/W=1/R=1 that breaks consistency. Each scenario shows exactly which
nodes participate in reads and writes and whether the overlap guarantees
fresh data.

---

## Lab 3: Conflict Resolution

`conflict_resolution.py` simulates two leaders accepting concurrent writes
to the same key and demonstrates three resolution strategies:

- **Last-Write-Wins (LWW):** Picks the write with the higher timestamp.
  Simple but silently drops data.
- **Version Vectors:** Tracks causal history per node. Detects true
  conflicts vs. causally ordered updates.
- **Custom Merge:** Application-specific logic that merges conflicting
  values (e.g., union of sets).

---

## Lab 4: Failover Simulation

`failover_sim.py` simulates a leader-follower cluster where the leader
crashes. A monitor process detects the failure after missed heartbeats,
selects the most up-to-date follower, promotes it to leader, and
reconfigures the cluster.

The simulation also demonstrates the split-brain scenario - what happens
when the old leader comes back after a new leader has been elected, and how
fencing tokens prevent conflicting writes.

---

## What to Look For

- In Lab 1, compare the write latency between sync and async modes. Notice
  how the async follower can serve stale reads.
- In Lab 2, change the W and R values and observe when consistency breaks.
  The formula W + R > N is the dividing line.
- In Lab 3, compare LWW (data loss) vs. version vectors (conflict
  detection) vs. merge (data preservation). Each has real trade-offs.
- In Lab 4, watch the failover timeline. Count the missed heartbeats,
  observe the election, and see how fencing tokens block the zombie leader.
