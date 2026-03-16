# Chapter 22 - Clocks & Ordering

> "What time is it?" sounds like a simple question - until you ask two computers and get two different answers. Distributed systems can't agree on the time, and that disagreement breaks everything from database writes to leader elections.

📖 [Read on Medium](#) · 🎬 [Watch on YouTube](#)

---

## Why Time Is Hard in Distributed Systems

On a single machine, time is straightforward. You call `time.now()`, you get a number, and every thread on that box sees the same clock. The moment you add a second machine, that guarantee vanishes.

Here's the core problem: **there's no global clock**. Every machine has its own oscillator - a quartz crystal vibrating at roughly 32,768 Hz. "Roughly" is the operative word. Crystals drift. A cheap server-grade oscillator drifts 10-20 parts per million. That's up to 1.7 seconds per day.

Why does this matter? Because distributed systems constantly ask ordering questions:

- Did this write happen before or after that write?
- Which replica has the newest data?
- Did the lock expire before or after the request arrived?
- Should this transaction commit or abort?

If your clocks disagree by even a millisecond, you'll get wrong answers to these questions. And wrong answers mean lost writes, phantom reads, and split-brain disasters.

---

## Physical Clocks and Clock Drift

Every computer has two physical clocks:

| Clock | How It Works | Accuracy | Use Case |
|-------|-------------|----------|----------|
| **Real-Time Clock (RTC)** | Battery-backed quartz crystal, survives reboots | Drifts 10-20 ppm | Wall-clock time at boot |
| **System Clock** | OS-maintained, initialized from RTC, adjusted by NTP | Depends on sync frequency | Timestamps, scheduling |

### Clock Drift in Numbers

A drift of 20 ppm means:

| Duration | Maximum Drift |
|----------|--------------|
| 1 second | 20 microseconds |
| 1 minute | 1.2 milliseconds |
| 1 hour | 72 milliseconds |
| 1 day | 1.7 seconds |
| 1 month | 52 seconds |

That 1.7-second daily drift doesn't sound catastrophic until you realize that a database processing 50,000 writes per second can fit 85,000 writes into that gap. If two nodes disagree about ordering for even a fraction of that window, you've got data corruption.

### Clock Skew vs. Clock Drift

These terms get conflated, but they're different:

- **Clock drift** - the rate at which a clock diverges from true time (measured in ppm)
- **Clock skew** - the difference between two clocks at a specific moment (measured in time units)

Drift causes skew. Skew causes bugs.

---

## NTP - The Best Bad Solution

The Network Time Protocol (NTP) has been synchronizing clocks since 1985. It's a hierarchical system:

```
Stratum 0: Atomic clocks, GPS receivers (reference clocks)
    |
Stratum 1: Servers directly connected to Stratum 0
    |
Stratum 2: Servers syncing from Stratum 1
    |
Stratum 3: Servers syncing from Stratum 2
    ...
```

NTP estimates round-trip delay, calculates offset, and adjusts the local clock. On a good LAN, NTP achieves sub-millisecond accuracy. Over the public internet, you're looking at 1-10ms accuracy on a good day and 100ms+ on a bad one.

### NTP's Limitations

1. **Network jitter** - Variable latency makes offset estimation noisy
2. **Asymmetric paths** - NTP assumes equal send/receive latency. If they differ, the estimate is wrong
3. **Clock jumps** - NTP sometimes steps the clock backward. Your timestamp-based logic just broke
4. **Smearing** - To avoid jumps, some NTP implementations "smear" leap seconds across hours. Different smearing implementations disagree with each other
5. **Byzantine failures** - A misconfigured NTP server can feed you garbage time with full confidence

The takeaway: **NTP is good enough for logs and debugging. It's not good enough for ordering guarantees.**

---

## The Happens-Before Relationship

Leslie Lamport realized in 1978 that you don't always need real time. You need to know **what happened before what**. He defined the "happens-before" relation (written as ->):

1. **Same process**: If event A occurs before event B in the same process, then A -> B
2. **Message passing**: If process P sends a message and process Q receives it, then send -> receive
3. **Transitivity**: If A -> B and B -> C, then A -> C

If neither A -> B nor B -> A, the events are **concurrent**. They happened independently - no causal connection exists between them. This is a partial order, not a total order.

```
Process P:  ----[A]--------[B]---[send msg]------------->
                                      |
Process Q:  ------[C]---[D]----------[recv msg]---[E]--->

Ordering:
  A -> B  (same process)
  C -> D  (same process)
  B -> send -> recv -> E  (message passing + transitivity)
  A and C?  CONCURRENT - no causal link
  A and D?  CONCURRENT - no causal link
  B and D?  CONCURRENT - no causal link
```

This is a powerful insight. Most events in a distributed system are concurrent. You only need to track causality - and causality flows through messages.

---

## Lamport Clocks (Logical Clocks)

Lamport clocks implement the happens-before relation with a single integer counter. The rules are dead simple:

1. Every process maintains a counter `C`, initialized to 0
2. Before each local event, increment: `C = C + 1`
3. When sending a message, attach your current `C`
4. When receiving a message with timestamp `T`, update: `C = max(C, T) + 1`

```
Process P (C=0):   [C=1]----[C=2]----send(C=2)--->
                                          |
Process Q (C=0):   [C=1]----[C=2]--------recv(T=2)-->[C=3]-->[C=4]
```

### What Lamport Clocks Guarantee

If A -> B, then `C(A) < C(B)`. The converse is **not** true - `C(A) < C(B)` does not imply A -> B. The events might be concurrent with coincidentally ordered timestamps.

This one-way guarantee is enough for many use cases:

- **Total ordering** - Sort events by (timestamp, process_id) for a deterministic total order
- **Mutex** - Lamport's bakery algorithm uses these clocks for distributed mutual exclusion
- **Log ordering** - Assign consistent sequence numbers across nodes

### What Lamport Clocks Can't Do

They can't detect concurrency. If `C(A) = 5` and `C(B) = 7`, you can't tell whether A -> B or they're concurrent. For that, you need vector clocks.

---

## Vector Clocks

Vector clocks replace the single counter with a vector - one counter per process. For a system with N processes, each process maintains an array of N integers.

### Rules

1. Initialize all counters to 0: `[0, 0, ..., 0]`
2. Before each local event, increment your own position: `VC[self] += 1`
3. When sending, attach your current vector
4. When receiving vector `T`, merge element-wise: `VC[i] = max(VC[i], T[i])` for all i, then increment self

### Comparing Vector Clocks

```
VC(A) = [2, 3, 1]
VC(B) = [2, 4, 1]

A -> B?  Every element of A <= corresponding element of B,
         and at least one is strictly less. YES.

VC(X) = [3, 2, 1]
VC(Y) = [2, 3, 1]

X -> Y?  X[0]=3 > Y[0]=2, so NO.
Y -> X?  Y[1]=3 > X[1]=2, so NO.
Conclusion: X and Y are CONCURRENT.
```

The comparison rules:

| Condition | Meaning |
|-----------|---------|
| VC(A) <= VC(B) and VC(A) != VC(B) | A happens-before B |
| VC(B) <= VC(A) and VC(B) != VC(A) | B happens-before A |
| Neither | A and B are concurrent |

### The Scalability Problem

Vector clocks grow linearly with the number of processes. In a system with 1,000 nodes, every message carries a vector of 1,000 integers. That's overhead you feel.

Solutions:

- **Pruning** - Remove entries for nodes that haven't participated recently (Dynamo's approach, but it has known issues with sibling explosion)
- **Interval tree clocks** - Dynamically sized, but more complex
- **Dotted version vectors** - Used in Riak, handles multiple concurrent values per key cleanly

---

## Total Order vs. Partial Order

This distinction matters more than most engineers realize:

| Property | Partial Order | Total Order |
|----------|--------------|-------------|
| Every pair comparable? | No - some events are concurrent | Yes - every pair has an order |
| Real-world analogy | Family tree (cousins aren't ordered) | Line at a checkout counter |
| Provided by | Vector clocks, happens-before | Lamport clocks + tiebreaker, Raft log |
| Strength | Captures exactly causality | Enables sequential reasoning |
| Cost | Cheaper, less coordination | Requires consensus or central authority |

Partial order is what actually exists in a distributed system. Total order is what databases need for serial execution. Bridging that gap is what consensus protocols (Raft, Paxos) and specialized clocks (TrueTime) are for.

---

## Google TrueTime - GPS + Atomic Clocks

Google looked at the clock problem and decided to throw hardware at it. TrueTime, used in Google Spanner, equips every data center with GPS receivers and atomic clocks.

Instead of returning a single timestamp, TrueTime returns an **interval**: `[earliest, latest]`. The true time is guaranteed to fall somewhere in that interval.

```
TrueTime.now() -> TT.interval {
    earliest: 1709234567.123456
    latest:   1709234567.130456
    // True time is somewhere in this 7ms window
}
```

The uncertainty window (called epsilon) is typically 1-7ms. Spanner uses this by **waiting out the uncertainty**:

1. Assign a commit timestamp at the end of the uncertainty window
2. Wait until the uncertainty window passes (`2 * epsilon`)
3. Only then make the write visible

This means every write in Spanner costs a few milliseconds of latency. That's the price of globally consistent timestamps. Google decided it's worth paying.

### Why Only Google Can Do This

The hardware infrastructure for TrueTime costs serious money. Every data center needs redundant GPS antennas and atomic clocks. The GPS receivers provide absolute time, the atomic clocks provide stability when GPS loses signal. Running and calibrating this infrastructure at scale is nontrivial.

Cloud Spanner (the managed service) gives you TrueTime without owning the hardware. CockroachDB approximates TrueTime's guarantees using NTP with configurable uncertainty windows - it works, but with wider bounds and more waiting.

---

## Hybrid Logical Clocks (HLC)

HLCs, introduced by Kulkarni et al. in 2014, combine physical and logical timestamps. They're the practical middle ground between "trust the wall clock" and "use only logical counters."

An HLC timestamp has three components:

| Component | Purpose |
|-----------|---------|
| `pt` (physical) | Wall-clock time, tracks real time |
| `l` (logical) | Captures causality when physical clocks collide |
| `c` (counter) | Breaks ties when both physical and logical match |

### HLC Algorithm

**Local event or send:**
```
l' = max(l, physical_time())
if l' == l:
    c = c + 1
else:
    c = 0
l = l'
```

**Receive message with timestamp (l_m, c_m):**
```
l' = max(l, l_m, physical_time())
if l' == l == l_m:
    c = max(c, c_m) + 1
elif l' == l:
    c = c + 1
elif l' == l_m:
    c = c_m + 1
else:
    c = 0
l = l'
```

### Why HLCs Are Practical

1. **Compact** - Just (physical_time, counter), not a vector of N integers
2. **Close to real time** - The physical component means timestamps are meaningful, not arbitrary
3. **Causal** - Still captures happens-before within the precision of the physical clock
4. **NTP-compatible** - Works with standard clock synchronization, no special hardware needed

CockroachDB uses HLCs as its primary timestamp mechanism. MongoDB's oplog uses a similar approach.

---

## Real-World Systems and Their Clock Choices

| System | Clock Type | Why |
|--------|-----------|-----|
| **Google Spanner** | TrueTime (GPS + atomic) | Needs globally consistent timestamps for external consistency |
| **CockroachDB** | HLC + configurable uncertainty | Spanner-like semantics without custom hardware |
| **Amazon DynamoDB** | Vector clocks (originally) | Detects conflicts for eventual consistency. Later moved to last-writer-wins |
| **Cassandra** | Last-writer-wins with NTP | Simple, fast, but silently drops conflicting writes |
| **Riak** | Dotted version vectors | Handles sibling explosion better than plain vector clocks |
| **MongoDB** | Hybrid timestamp (similar to HLC) | Oplog ordering across replica set members |
| **etcd / Raft** | Logical (Raft log index) | Total order from leader, no wall-clock dependency |

### Cassandra's Cautionary Tale

Cassandra uses last-writer-wins (LWW) with NTP timestamps. If two clients write to the same key at "the same time," the higher timestamp wins. Sounds reasonable until:

- Node A's clock is 200ms ahead of Node B's clock
- Client writes value "X" to Node B at real time T
- Client writes value "Y" to Node A at real time T + 100ms
- Node A's timestamp: T + 300ms. Node B's timestamp: T.
- Cassandra picks "Y" because 300ms > 0ms
- But "Y" was written 100ms after "X" in real time - the correct winner

This isn't a bug. It's a design choice. LWW with physical clocks trades correctness for simplicity and performance. Know what you're giving up.

---

## Common Pitfalls

| Pitfall | What Goes Wrong | Fix |
|---------|----------------|-----|
| Using `System.currentTimeMillis()` for ordering | Clock skew between nodes causes wrong order | Use logical or hybrid clocks |
| Assuming NTP is precise | NTP drifts 1-100ms, enough to reorder events | Design for bounded uncertainty |
| Ignoring leap seconds | 23:59:60 breaks timestamp parsers and arithmetic | Use TAI or smeared UTC |
| Comparing timestamps across machines | Clocks aren't synchronized, comparison is meaningless | Use happens-before or vector clocks |
| Growing vector clocks unboundedly | Message size explodes with node count | Prune old entries or use HLCs |
| Last-writer-wins without understanding trade-offs | Silently drops concurrent writes | Use CRDTs or application-level merge |
| Trusting monotonic clocks across reboots | Monotonic clock resets on restart | Persist sequence numbers or use HLCs |

---

## Ordering in Practice - A Decision Framework

When you're designing a system and need to choose a clock mechanism:

```
Do you need to order events?
├── No  -> Don't bother with clocks beyond logging
├── Yes
    ├── Only within a single node?
    │   └── Monotonic clock. Done.
    ├── Across nodes, but only causal order?
    │   ├── Small cluster (<20 nodes)? -> Vector clocks
    │   └── Large cluster? -> HLC
    ├── Need total order?
    │   ├── Have a leader? -> Raft/Paxos log index
    │   └── No leader? -> Lamport clock + node ID tiebreaker
    └── Need globally consistent wall-clock order?
        ├── Can afford specialized hardware? -> TrueTime
        └── Can't? -> HLC with bounded uncertainty (accept the latency tax)
```

---

## Timestamps in Databases - Deeper Dive

### MVCC and Timestamps

Multi-Version Concurrency Control (MVCC) is the backbone of modern databases. Every row version gets a timestamp. Reads see a consistent snapshot at a given timestamp. This only works if timestamps are correctly ordered.

- **PostgreSQL** uses a transaction ID (essentially a Lamport clock) - works because it's single-node
- **Spanner** uses TrueTime timestamps - works globally because of hardware guarantees
- **CockroachDB** uses HLC timestamps - works across nodes with bounded uncertainty windows

### The Read Uncertainty Problem

When CockroachDB reads a key, it might find a value with a timestamp in the uncertainty window. Is this value from the past (should be visible) or the future (shouldn't be visible)? CockroachDB resolves this by restarting the transaction at a higher timestamp. This adds latency but preserves correctness.

---

## Key Takeaways

1. **Physical clocks drift** - Never trust wall-clock time for ordering across machines
2. **Lamport clocks** are simple but can't detect concurrency - good enough for total ordering with a tiebreaker
3. **Vector clocks** detect concurrency precisely but scale poorly - use them in small clusters
4. **HLCs** are the practical sweet spot - physical time for humans, logical counters for causality
5. **TrueTime** is the gold standard but requires specialized hardware - you're probably not Google
6. **Last-writer-wins** is a valid choice if you understand and accept that you'll lose writes
7. **The right clock depends on your ordering requirements** - don't over-engineer, but don't under-engineer either

---

## What's Next?

- **Chapter 23:** [Monolith vs Microservices](../23-microservices/) - When to split, when to stay, and why most teams split too early
