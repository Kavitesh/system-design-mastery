# Chapter 18 - Distributed Consensus

> Five servers need to agree on who's the leader. One crashes mid-vote. Another has a network delay of 200ms. A third just rebooted and missed the last three decisions. Welcome to the hardest problem in distributed systems - getting machines to agree on anything.

📖 Read the full article on Medium: *Coming Soon*
# Subscribe to the newsletter for updates

🎬 Watch the video explanation: *Coming Soon*
# Like and subscribe for more system design content

---

## Why Consensus Matters

Every distributed system eventually hits this wall: multiple nodes need to agree on something. Who's the leader? What's the current configuration? Did that transaction commit or abort?

Without consensus, you get chaos. Two nodes both think they're the leader. A config change applies on three servers but not the other two. A committed transaction vanishes after a failover.

Consensus isn't optional. It's the foundation under every serious distributed system - databases, message queues, coordination services, container orchestration. If you don't understand consensus, you don't understand distributed systems.

Here's what makes it brutal: the network is unreliable, nodes crash at the worst possible moments, and clocks drift. You can't just "vote and pick the majority" because messages get lost, delayed, or reordered. The algorithms that actually solve this took decades of research to get right.

---

## The Consensus Problem

The consensus problem has a deceptively simple definition. A group of nodes must agree on a single value, and that agreement must satisfy three properties:

| Property | Meaning |
|---|---|
| **Agreement** | All non-faulty nodes decide on the same value |
| **Validity** | The decided value was proposed by some node |
| **Termination** | Every non-faulty node eventually decides |

That's it. Three properties. And yet the FLP impossibility result (Fischer, Lynch, Paterson, 1985) proved that no deterministic algorithm can guarantee all three in an asynchronous system with even one crash failure.

This sounds like a dead end, but it's not. Practical algorithms work around FLP by using timeouts (introducing partial synchrony) or randomization. They can't guarantee termination in all cases, but they work reliably in practice. That's good enough.

### What Needs Consensus

Consensus shows up everywhere:

- **Leader election** - picking one node to coordinate
- **Atomic broadcast** - delivering messages in the same order to all nodes
- **State machine replication** - keeping replicas in sync
- **Distributed locking** - mutual exclusion across machines
- **Configuration management** - agreeing on cluster membership

These are all equivalent problems. Solve one, and you can build the others on top of it.

---

## Paxos - The Original (and Hard to Understand)

Leslie Lamport published Paxos in 1998 (written in 1990). It's provably correct. It's also notoriously difficult to understand and even harder to implement.

### How Paxos Works (Simplified)

Paxos has three roles: **proposers**, **acceptors**, and **learners**. A single round has two phases:

**Phase 1 - Prepare:**
1. A proposer picks a proposal number `n` and sends `Prepare(n)` to a majority of acceptors
2. Each acceptor responds with a promise not to accept proposals numbered less than `n`
3. If the acceptor already accepted a value, it includes that value in the response

**Phase 2 - Accept:**
1. If the proposer gets promises from a majority, it sends `Accept(n, v)` where `v` is either the value from the highest-numbered previously accepted proposal, or the proposer's own value if no acceptor had accepted anything
2. Acceptors accept the proposal unless they've promised to a higher number
3. Once a majority accepts, the value is chosen

```
Proposer           Acceptor 1        Acceptor 2        Acceptor 3
   |                  |                  |                  |
   |-- Prepare(1) --> |                  |                  |
   |-- Prepare(1) ------------------>   |                  |
   |-- Prepare(1) -------------------------------------> |
   |                  |                  |                  |
   |<- Promise(1) --- |                  |                  |
   |<- Promise(1) ------------------- |                  |
   |                  |                  |    (slow/lost)   |
   |                  |                  |                  |
   |-- Accept(1,v) -> |                  |                  |
   |-- Accept(1,v) -----------------> |                  |
   |                  |                  |                  |
   |<- Accepted ------|                  |                  |
   |<- Accepted ----------------------|                  |
   |                  |                  |                  |
   | Value v is chosen (majority accepted)                 |
```

### Why Paxos is Hard

The single-decree version above decides one value. Real systems need to decide a sequence of values (a log). Multi-Paxos extends single-decree Paxos but Lamport's paper left many implementation details unspecified: leader election, log compaction, membership changes, and client interaction.

Every team that implements Multi-Paxos ends up building something different. Google's Chubby team said they spent years getting their Paxos implementation right. That difficulty is exactly why Raft was created.

---

## Raft - Consensus Made Understandable

Diego Ongaro designed Raft in 2014 with one explicit goal: understandability. It's equivalent to Multi-Paxos in terms of safety and performance, but it decomposes the problem into three clean subproblems:

1. **Leader election** - pick a single leader
2. **Log replication** - the leader accepts entries and replicates them
3. **Safety** - guarantee logs stay consistent

### Node States

Every Raft node is in one of three states:

```
                    times out,
                    starts election
    +----------+                  +-----------+
    | Follower | ---------------> | Candidate |
    +----------+                  +-----------+
         ^                         /        |
         |     discovers leader   /         | receives majority
         |     or higher term    /          | of votes
         |                      /           v
         +--------------------+       +---------+
                                      | Leader  |
                                      +---------+
```

- **Follower** - passive, responds to RPCs from leader and candidates
- **Candidate** - actively seeking votes for leadership
- **Leader** - handles all client requests, replicates log entries

### Terms

Raft divides time into **terms** - monotonically increasing integers. Each term begins with an election. If an election succeeds, the winner leads for the rest of the term. If it fails (split vote), a new term starts.

Terms act as a logical clock. Every RPC includes the sender's term. If a node receives a message with a higher term, it updates its own term and steps down to follower. Stale messages (lower term) get rejected.

### Leader Election

1. A follower's election timer expires (randomized, typically 150-300ms)
2. It increments its term and transitions to candidate
3. It votes for itself and sends `RequestVote` RPCs to all other nodes
4. Three outcomes:
   - **Wins** - gets votes from a majority, becomes leader, sends heartbeats
   - **Loses** - another node wins (receives heartbeat with equal or higher term)
   - **Split vote** - no majority, timer expires, starts new election

The randomized timeout is critical. Without it, nodes would repeatedly start elections at the same time and split the vote forever. With randomization, one node almost always times out first and wins cleanly.

### Log Replication

Once elected, the leader handles all writes:

1. Client sends a command to the leader
2. Leader appends the command to its local log
3. Leader sends `AppendEntries` RPCs to all followers
4. Once a majority acknowledges, the entry is **committed**
5. Leader applies the entry to its state machine and responds to the client
6. Followers learn about the commit in subsequent heartbeats and apply it

```
Leader Log:    [1:SET x=1] [1:SET y=2] [2:SET x=3] [2:DEL y]
                                                      ^
                                               commit index = 4

Follower A:   [1:SET x=1] [1:SET y=2] [2:SET x=3]
Follower B:   [1:SET x=1] [1:SET y=2] [2:SET x=3] [2:DEL y]
Follower C:   [1:SET x=1] [1:SET y=2]
```

The number before the colon is the term. The leader only commits entries from its own term (this prevents subtle bugs with leader changes).

### Log Matching Property

Raft guarantees:
- If two entries in different logs have the same index and term, they store the same command
- If two entries in different logs have the same index and term, all preceding entries are identical

This is enforced by the `AppendEntries` consistency check. Each RPC includes the index and term of the entry immediately preceding the new entries. If a follower doesn't have a matching entry, it rejects the RPC, and the leader decrements its index and retries.

### Safety Guarantee

Raft's election restriction ensures safety: a candidate can't win an election unless its log is at least as up-to-date as any log in the majority. "Up-to-date" means the last entry has a higher term, or the same term with a higher index.

This guarantees that the elected leader always has all committed entries. No committed data is ever lost during a leadership transition.

---

## Raft vs Paxos

| Aspect | Paxos | Raft |
|---|---|---|
| **Understandability** | Notoriously difficult | Designed for clarity |
| **Leader** | Optional optimization | Required, central role |
| **Log management** | Gaps allowed | No gaps, sequential |
| **Membership changes** | Not specified | Joint consensus protocol |
| **Implementations** | Many variants, hard to compare | Consistent across implementations |
| **Correctness proofs** | Well-established | Formally verified (TLA+) |
| **Performance** | Comparable | Comparable |
| **Adoption** | Google Chubby/Spanner | etcd, CockroachDB, TiKV |

My take: Raft wins for almost every practical use case. Paxos matters historically and in specialized scenarios (like flexible quorums), but if you're building something today, use Raft or a Raft-based system.

---

## Leader Election Algorithms

Beyond Raft's built-in election, several other approaches exist:

### Bully Algorithm

The simplest leader election. Every node has a numeric ID. When a node detects the leader is down:
1. It sends an election message to all nodes with higher IDs
2. If none respond, it declares itself leader
3. If a higher-ID node responds, that node takes over the election

Problems: the highest-ID node always wins, even if it's flaky. And network partitions cause havoc.

### Ring-Based Election

Nodes are arranged in a logical ring. Election messages pass around the ring, collecting votes. Simple and deterministic, but slow - O(n) messages minimum.

### ZAB (ZooKeeper Atomic Broadcast)

ZooKeeper uses its own protocol, ZAB, which is similar to Raft but predates it. ZAB separates the broadcast protocol from leader election more explicitly and handles recovery differently. In practice, the differences are subtle.

---

## The Split-Brain Problem

Split-brain is the nightmare scenario: a network partition creates two groups of nodes, and both groups elect a leader. Now you have two leaders accepting writes independently, and the data diverges.

```
                    Network Partition
                         |||
   [Node A - Leader]     |||     [Node C - Leader]
   [Node B - Follower]   |||     [Node D - Follower]
                         |||     [Node E - Follower]
```

### Why Majority Quorums Prevent Split-Brain

With 5 nodes, a leader needs 3 votes. After a partition of 2 and 3:
- The group of 3 can elect a leader (has a majority)
- The group of 2 cannot (doesn't have a majority)

This is why consensus clusters always have an odd number of nodes. With 4 nodes, a 2-2 split means neither side can make progress.

### Fencing Tokens

Even with quorum-based systems, split-brain can happen briefly during transitions. Fencing tokens provide an extra safety layer:

1. Every leader gets a monotonically increasing **fencing token** (essentially the term number)
2. All writes to shared resources include the fencing token
3. The resource rejects writes with a token lower than the highest it's seen

```
Old Leader (token=3):  WRITE x=5, token=3  --> Storage
New Leader (token=4):  WRITE x=7, token=4  --> Storage (accepted, token updated to 4)
Old Leader (token=3):  WRITE x=9, token=3  --> Storage (REJECTED, 3 < 4)
```

This is exactly how Martin Kleppmann recommends protecting against split-brain in "Designing Data-Intensive Applications." The storage layer becomes the final arbiter.

---

## ZooKeeper Concepts

Apache ZooKeeper is the OG coordination service. It doesn't implement consensus directly for your application - it provides primitives that you build coordination on top of.

### ZNodes

ZooKeeper's data model is a hierarchical namespace (like a filesystem):

```
/
├── /services
│   ├── /services/web-api
│   │   ├── /services/web-api/instance-001
│   │   └── /services/web-api/instance-002
│   └── /services/worker
│       └── /services/worker/instance-001
├── /config
│   └── /config/database-url
└── /locks
    └── /locks/inventory-update
```

Each znode can store up to 1MB of data (keep it small - this isn't a database).

### Ephemeral Nodes

Ephemeral nodes are tied to the client session. When the client disconnects (or its session times out), the node is automatically deleted. This is incredibly useful for:

- **Service discovery** - instances register ephemeral nodes; when they crash, they disappear
- **Leader election** - candidates create ephemeral sequential nodes; the lowest one wins
- **Health monitoring** - node existence equals liveness

### Watches

Clients can set watches on znodes. A watch fires once when:
- The znode's data changes
- The znode is deleted
- Child znodes are created or deleted

Watches are one-time triggers. After firing, you need to re-register. This is a deliberate design choice - it prevents the thundering herd problem where every watcher simultaneously reacts.

### ZooKeeper Recipes

Common patterns built on ZooKeeper primitives:

| Recipe | Mechanism |
|---|---|
| **Distributed lock** | Create ephemeral sequential znode under /locks; lowest sequence number holds lock |
| **Leader election** | Create ephemeral sequential znode under /election; lowest sequence number is leader |
| **Group membership** | Each member creates ephemeral node under /members; watch for children changes |
| **Barrier** | All nodes create znodes under /barrier; proceed when count reaches N |
| **Two-phase commit** | Coordinator creates /txn; participants create /txn/vote-yes or /txn/vote-no |

---

## etcd and Kubernetes

etcd is a distributed key-value store built on Raft. It's the backbone of Kubernetes - every piece of cluster state lives in etcd.

### What Kubernetes Stores in etcd

- Pod definitions and status
- Service endpoints
- ConfigMaps and Secrets
- Node registration and health
- RBAC policies
- Custom Resource Definitions

When you run `kubectl apply -f deployment.yaml`, here's what actually happens:

1. kubectl sends the request to the API server
2. The API server validates and persists to etcd (via Raft consensus)
3. Once etcd confirms the write is committed (majority of etcd nodes acknowledge), the API server responds
4. Controllers watch etcd for changes and reconcile desired vs actual state

### etcd Operations

```
# Set a value
etcdctl put /config/db-host "postgres.internal:5432"

# Get a value
etcdctl get /config/db-host

# Watch for changes
etcdctl watch /config/ --prefix

# Lease (TTL-based key)
etcdctl lease grant 30
etcdctl put /services/api/instance-1 "10.0.1.5:8080" --lease=<lease-id>
```

etcd leases are similar to ZooKeeper's ephemeral nodes - keys with a TTL that disappear when not renewed.

### etcd Cluster Sizing

| Cluster Size | Tolerates Failures | Recommended For |
|---|---|---|
| 1 | 0 | Development only |
| 3 | 1 | Small production clusters |
| 5 | 2 | Large production clusters |
| 7 | 3 | Very large clusters (diminishing returns) |

Don't go beyond 7. More nodes means more replication overhead and slower writes. The latency cost outweighs the fault-tolerance benefit.

---

## Quorum-Based Consensus

The magic number in consensus is the **quorum** - the minimum number of nodes that must agree for an operation to succeed.

For a cluster of N nodes:
- **Quorum size** = floor(N/2) + 1
- **Fault tolerance** = N - quorum = floor((N-1)/2)

| N | Quorum | Tolerates | Cost of Extra Node |
|---|---|---|---|
| 3 | 2 | 1 failure | Baseline |
| 4 | 3 | 1 failure | More overhead, same tolerance |
| 5 | 3 | 2 failures | Worth it |
| 6 | 4 | 2 failures | More overhead, same tolerance |
| 7 | 4 | 3 failures | Diminishing returns |

Notice: even-numbered clusters are wasteful. Going from 3 to 4 nodes doesn't improve fault tolerance - you just added cost. Always use odd numbers: 3, 5, or 7.

### Read and Write Quorums

Some systems separate read and write quorums:
- **Write quorum (W)**: nodes that must acknowledge a write
- **Read quorum (R)**: nodes that must respond to a read
- **Rule**: W + R > N (guarantees overlap, so reads see latest writes)

Common configurations:
- W=N, R=1: fast reads, slow writes (read-heavy workloads)
- W=1, R=N: fast writes, slow reads (write-heavy workloads)
- W=majority, R=majority: balanced (most consensus systems)

---

## Byzantine Fault Tolerance

Everything above assumes **crash-fault tolerance** - nodes either work correctly or stop. Byzantine fault tolerance (BFT) handles nodes that actively lie, send contradictory messages, or behave maliciously.

### The Byzantine Generals Problem

Lamport's 1982 paper: several generals must agree on whether to attack or retreat. Some generals are traitors who send conflicting messages. The result: you need at least 3f+1 nodes to tolerate f Byzantine faults.

| Fault Type | Nodes Needed | Overhead |
|---|---|---|
| Crash faults | 2f+1 | Moderate |
| Byzantine faults | 3f+1 | High |

BFT algorithms (PBFT, Tendermint, HotStuff) require significantly more message rounds and computational work. For most infrastructure, crash-fault tolerance is sufficient - you trust your own servers not to be actively malicious.

**Where BFT matters:** blockchain consensus (you don't trust other participants), multi-party computation, and safety-critical systems where hardware corruption is a concern.

---

## Real-World Consensus in Action

### Kafka and ZooKeeper (and KRaft)

Kafka historically depended on ZooKeeper for:
- Broker registration and liveness
- Topic/partition metadata
- Controller election (the broker that manages partition leadership)
- Consumer group coordination (older versions)

Starting with Kafka 3.3, **KRaft mode** removes the ZooKeeper dependency entirely. Kafka now runs its own Raft-based consensus for metadata management. This simplifies operations significantly - one fewer system to deploy and monitor.

### CockroachDB and Raft

CockroachDB uses Raft at the range level. The database splits data into ranges (~64MB each), and each range is a separate Raft group. A single CockroachDB cluster might run thousands of concurrent Raft groups.

This design means:
- Each range replicates independently
- A node failure only affects ranges with replicas on that node
- Leadership is distributed across the cluster, avoiding bottlenecks

### Google Spanner and Paxos

Spanner uses Multi-Paxos for replication across data centers. Combined with TrueTime (GPS and atomic clocks), it achieves globally consistent reads without consensus round-trips. It's probably the most sophisticated consensus deployment in production.

---

## Common Pitfalls

### 1. Running Consensus Over WAN Without Accounting for Latency

Raft and Paxos assume relatively low-latency networks. Cross-datacenter consensus means every write waits for a round-trip across data centers (50-200ms). Solutions: use Multi-Raft with local leaders, or accept eventual consistency for cross-region reads.

### 2. Too Many Nodes in the Consensus Group

More nodes don't mean more safety after a point. Going from 5 to 9 nodes doubles your replication traffic but only adds one more tolerated failure. Keep consensus groups small (3-5 nodes) and shard if you need scale.

### 3. Ignoring Disk Fsync

Consensus algorithms assume durable writes. If a node acknowledges a vote or log entry and then loses it on crash (because it was in a write-back cache), you violate safety. Always fsync before acknowledging. Yes, it's slower. No, you can't skip it.

### 4. Clock-Dependent Leader Leases

Some systems use time-based leader leases for efficiency. If the leader's clock is faster than followers' clocks, it might believe its lease is valid while followers have already elected a new leader. Use bounded clock skew assumptions carefully, or avoid clock-dependent protocols entirely.

### 5. Forgetting About Network Partitions in Tests

Your consensus implementation works great on a healthy network. But have you tested: asymmetric partitions (A can reach B but not C)? Partitions that heal and re-form? Partitions during leadership transitions? If not, you'll find out about bugs in production.

---

## Key Takeaways

1. **Consensus is the foundation** - leader election, replication, coordination all reduce to consensus
2. **Raft over Paxos** for new implementations - equivalent correctness, far easier to understand and implement
3. **Odd-numbered clusters** - always 3, 5, or 7 nodes; even numbers waste resources
4. **Fencing tokens prevent split-brain damage** - the storage layer is the final safety net
5. **ZooKeeper/etcd are coordination services**, not databases - keep data small, use them for metadata
6. **Byzantine fault tolerance is overkill** for most systems - save it for truly adversarial environments
7. **Test network partitions** - consensus bugs hide until partitions happen

---

## Code Labs

Explore these hands-on demos in the `code/` directory:

| Lab | File | What You'll Learn |
|---|---|---|
| Raft Leader Election | `raft_election.py` | Term-based voting, randomized timeouts, leader emergence |
| Log Replication | `log_replication.py` | Append-only logs, commit index, majority acknowledgment |
| Split-Brain Demo | `split_brain.py` | Network partitions, dual leaders, fencing token defense |
| Service Registry | `service_registry.py` | Ephemeral nodes, watches, health-based deregistration |

---

## What's Next?

- **Chapter 19:** [Distributed Transactions](../19-distributed-transactions/) - two-phase commit, sagas, and how to coordinate writes across multiple services
- **Chapter 20:** [Stream Processing](../20-stream-processing/) - real-time data pipelines with Kafka Streams, Flink, and event sourcing
