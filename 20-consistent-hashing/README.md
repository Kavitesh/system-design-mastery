# Chapter 20 - Consistent Hashing

> Every distributed system that shards data hits the same wall: you add a server, and suddenly almost every key maps to the wrong place. Consistent hashing is the algorithm that turns a catastrophic reshuffling into a minor adjustment.

📖 Read the full article on Medium: *Coming Soon*
# Watch the video explanation: *Coming Soon*
🎬 YouTube Code Walkthrough: *Coming Soon*
# Star the repo: *Coming Soon*

---

## Table of Contents

- [The Rehashing Problem](#the-rehashing-problem)
- [Hash Rings - The Core Idea](#hash-rings---the-core-idea)
- [How Consistent Hashing Works](#how-consistent-hashing-works)
- [Virtual Nodes](#virtual-nodes)
- [Adding and Removing Nodes](#adding-and-removing-nodes)
- [Variations and Improvements](#variations-and-improvements)
- [Real-World Applications](#real-world-applications)
- [Production Examples](#production-examples)
- [Common Pitfalls](#common-pitfalls)
- [Quick Reference](#quick-reference)
- [Hands-On Code Labs](#hands-on-code-labs)
- [What's Next?](#whats-next)

---

## The Rehashing Problem

Here's the naive approach everyone starts with. You have N servers and you want to distribute keys evenly:

```
server = hash(key) % N
```

This works fine - until you change N.

Say you have 4 servers and 12 keys mapped across them. Now you add a fifth server. The formula changes from `hash(key) % 4` to `hash(key) % 5`. What happens?

| Key Hash | Old Server (% 4) | New Server (% 5) | Moved? |
|----------|-------------------|-------------------|--------|
| 7        | 3                 | 2                 | Yes    |
| 12       | 0                 | 2                 | Yes    |
| 15       | 3                 | 0                 | Yes    |
| 20       | 0                 | 0                 | No     |
| 23       | 3                 | 3                 | No     |
| 31       | 3                 | 1                 | Yes    |

On average, `(N-1)/N` of all keys get remapped. Going from 4 to 5 servers means roughly 75% of your keys move. Going from 99 to 100 servers? Still 99% of keys move.

For a cache cluster, this means a near-total cache miss storm. Every remapped key triggers a trip back to the database. If you've got millions of keys, you just created a thundering herd that can flatten your database.

**This is why modulo hashing doesn't work for dynamic systems.** You need an algorithm where adding or removing a server only moves `K/N` keys - the theoretical minimum.

---

## Hash Rings - The Core Idea

Consistent hashing was introduced by Karger et al. in 1997, originally to solve hot-spot problems in web caching. The insight is elegant: arrange the hash space as a ring instead of a line.

### The Ring Structure

1. Take your hash function's output range (e.g., 0 to 2^32 - 1 for a 32-bit hash)
2. Imagine wrapping that range into a circle - the number line bends so that 0 and 2^32 meet
3. Hash each server name onto a position on this ring
4. Hash each key onto a position on this ring
5. Each key belongs to the first server you encounter walking clockwise from the key's position

```
                    0
                    |
               S3 --+-- K1
              /           \
            /               \
          K4                 S1
          |                   |
          |      HASH RING    |
          |                   |
          S2                 K2
            \               /
              \           /
               K3 --+--
                    |
                  2^32
```

In this diagram, K1 maps to S1 (next server clockwise), K2 maps to S2, K3 maps to S2, and K4 maps to S3.

### Why This Works

The ring structure means each server "owns" an arc of the ring - from its position back counter-clockwise to the previous server. When you add or remove a server, only the keys in one arc need to move. Everything else stays put.

---

## How Consistent Hashing Works

Let's walk through the mechanics step by step.

### Step 1: Hash the Servers

Pick a hash function (SHA-1, MD5, xxHash - anything with good distribution). Hash each server identifier to get its position on the ring:

```
position(S1) = hash("server-1") = 45000
position(S2) = hash("server-2") = 120000
position(S3) = hash("server-3") = 250000
```

### Step 2: Hash the Keys

Use the same hash function for keys:

```
position(K_user:alice) = hash("user:alice") = 60000
position(K_user:bob)   = hash("user:bob")   = 200000
position(K_user:carol) = hash("user:carol") = 30000
```

### Step 3: Assign Keys to Servers

Walk clockwise from each key's position. The first server you hit owns that key:

```
user:alice (60000)  -> S2 (120000)   [next clockwise]
user:bob   (200000) -> S3 (250000)   [next clockwise]
user:carol (30000)  -> S1 (45000)    [next clockwise]
```

### Step 4: Lookup

Finding which server owns a key is an O(log N) operation - you're just doing a binary search on the sorted list of server positions to find the next one clockwise.

```python
def find_server(key, ring_positions):
    key_hash = hash(key)
    # Binary search for first server position >= key_hash
    idx = bisect_right(ring_positions, key_hash)
    # Wrap around if we've passed the last server
    return servers[idx % len(servers)]
```

---

## Virtual Nodes

Here's the problem with basic consistent hashing: with only a few physical servers, the arc lengths are wildly uneven. One server might own 60% of the ring while another owns 10%. Hash functions don't guarantee even spacing when you only have a handful of points.

### The Solution: Virtual Nodes (vnodes)

Instead of placing each server at one position on the ring, place it at many positions. Each physical server gets multiple "virtual" positions:

```
Server A -> vnode_A_0, vnode_A_1, vnode_A_2, ..., vnode_A_149
Server B -> vnode_B_0, vnode_B_1, vnode_B_2, ..., vnode_B_149
Server C -> vnode_C_0, vnode_C_1, vnode_C_2, ..., vnode_C_149
```

With 150 vnodes per server and 3 servers, you've got 450 points on the ring. The arcs are much more uniform. The load distribution approaches the ideal `1/N` per server.

### How Many Virtual Nodes?

| Virtual Nodes | Load Spread (std dev) | Memory per Node |
|---------------|-----------------------|-----------------|
| 1             | Very high (~50%+)     | Minimal         |
| 10            | ~10-15%               | Low             |
| 100           | ~3-5%                 | Moderate        |
| 150           | ~2-3%                 | Moderate        |
| 500           | ~1-2%                 | Higher          |
| 1000          | <1%                   | High            |

The sweet spot for most systems is 100-200 vnodes per physical node. Cassandra defaults to 256 tokens (vnodes) per node. Going higher gives diminishing returns while increasing the ring's memory footprint and lookup time.

### Weighted Virtual Nodes

Virtual nodes also let you handle heterogeneous hardware. Got a beefy server with twice the RAM? Give it twice the vnodes:

```
Small server:  100 vnodes
Large server:  200 vnodes
```

The large server naturally receives twice the traffic. No special logic needed.

---

## Adding and Removing Nodes

This is where consistent hashing earns its keep.

### Adding a Node

When server D joins the ring:

1. Hash D's identifier(s) to find its position(s) on the ring
2. D takes over keys from the arc immediately counter-clockwise
3. Only the next clockwise server loses some keys - every other server is untouched

```
Before:  ... --[S2]-- keys --[S3]-- ...
After:   ... --[S2]-- keys --[D]-- keys --[S3]-- ...
```

D takes a subset of S3's keys. S1, S2, and every other server keep all their keys.

**Keys moved: approximately K/N** (where K is total keys, N is new number of servers). This is the theoretical minimum - you can't do better without moving fewer keys than the new server needs.

### Removing a Node

When server D leaves:

1. All keys that belonged to D transfer to D's clockwise successor
2. Every other server is untouched

Same math: roughly K/N keys move. Compare this to modulo hashing where (N-1)/N keys move.

### The Numbers

| Servers | Keys  | Modulo Hashing (keys moved) | Consistent Hashing (keys moved) |
|---------|-------|-----------------------------|---------------------------------|
| 4 -> 5  | 1M    | ~750,000                    | ~200,000                        |
| 9 -> 10 | 1M    | ~900,000                    | ~100,000                        |
| 99->100 | 10M   | ~9,900,000                  | ~100,000                        |

The larger your cluster, the bigger the advantage.

---

## Variations and Improvements

### Jump Consistent Hashing

Google published jump consistent hashing in 2014. It uses no memory (zero ring storage), runs in O(ln N) time, and produces near-perfect load balance. The entire algorithm is about 7 lines of code:

```python
def jump_hash(key, num_buckets):
    b, j = -1, 0
    while j < num_buckets:
        b = j
        key = ((key * 2862933555777941757) + 1) & 0xFFFFFFFFFFFFFFFF
        j = int((b + 1) * (1 << 31) / ((key >> 33) + 1))
    return b
```

**Tradeoff:** Jump hashing only works when nodes are numbered 0 to N-1. You can add nodes at the end, but you can't remove an arbitrary node without renumbering. This makes it great for systems with a fixed set of nodes (like sharded databases) but poor for dynamic clusters where nodes come and go unpredictably.

### Bounded-Load Consistent Hashing

Standard consistent hashing has a known issue: even with vnodes, some servers can get unlucky with hot keys. Google's 2017 paper on bounded-load consistent hashing adds a simple rule:

**No server can hold more than (1 + epsilon) * (average load) keys.**

When a key hashes to an overloaded server, it slides clockwise to the next server with capacity. Setting epsilon to 0.25 means no server exceeds 125% of the average load. The tradeoff is slightly more key movement during rebalancing, but the worst-case load imbalance drops dramatically.

### Rendezvous Hashing (Highest Random Weight)

Not a ring-based approach, but solves the same problem. For each key, compute a score for every server and pick the highest:

```python
def find_server(key, servers):
    return max(servers, key=lambda s: hash(f"{key}:{s}"))
```

**Pros:** Simple, no ring data structure, perfect balance with enough keys.
**Cons:** O(N) lookup per key since you check every server. Fine for small clusters, not viable for thousands of nodes.

---

## Real-World Applications

### CDN Request Routing

Content delivery networks use consistent hashing to decide which edge server caches a piece of content. When a user requests `video-12345.mp4`, the CDN hashes the URL to find the edge server. If that server has the file cached, great. If not, it fetches from origin and caches it.

Without consistent hashing, adding a new edge PoP would invalidate caches across the entire network - millions of objects re-fetched from origin simultaneously.

### Distributed Caching (Memcached, Redis Cluster)

The original motivation for consistent hashing. When you have 20 Memcached instances and you lose one, only 1/20th of your cache goes cold. The rest keeps serving hits. With modulo hashing, you'd lose nearly everything.

### Database Sharding

Systems like DynamoDB and Cassandra use consistent hashing to assign data partitions to nodes. When you add a node to a Cassandra cluster, it takes over a portion of the token range from existing nodes. Data streams from neighbors without disrupting the rest of the cluster.

### Load Balancing

Consistent hashing load balancers (like Envoy's ring hash policy or HAProxy's consistent hashing mode) ensure that the same client always reaches the same backend. This is critical for stateful protocols or when you need sticky sessions without a session store.

### Distributed Hash Tables (DHTs)

Peer-to-peer systems like Chord and Amazon's original Dynamo paper use consistent hashing as the backbone for key routing. Each peer owns a section of the hash ring, and lookups are forwarded around the ring until they reach the responsible peer.

---

## Production Examples

### Amazon DynamoDB

DynamoDB uses consistent hashing to distribute data across storage nodes. Each table's items are partitioned by their primary key hash, and the hash ring determines which storage node group is responsible. When the cluster scales, partitions are split and migrated - not reshuffled entirely.

### Apache Cassandra

Cassandra assigns each node a set of tokens (vnodes) on a consistent hash ring. The default is 256 tokens per node. When a new node joins, it takes over roughly `1/N` of the token ranges from existing nodes. The `nodetool status` command shows you each node's ownership percentage of the ring.

### Akamai CDN

Consistent hashing was literally invented for Akamai's use case. Their 1997 paper described using it to distribute web content across cache servers. Today, Akamai's network of 300,000+ servers still relies on consistent hashing variants to route requests to the right edge cache.

### Envoy Proxy

Envoy's ring hash load balancer implements consistent hashing with configurable vnodes (default: 1024 per host). It's used when you need session affinity - the same client consistently reaches the same backend without centralized session state.

---

## Common Pitfalls

### 1. Too Few Virtual Nodes

Using 1-5 vnodes per server gives you terrible distribution. One server might handle 3x the load of another. Start with at least 100-150 vnodes per physical node. Test the actual distribution before going to production.

### 2. Poor Hash Function Choice

Don't use CRC32 or simple string hashing for ring placement. These have known clustering issues. Use SHA-1, MD5 (fine here since you don't need cryptographic security), or xxHash. The hash function needs good avalanche properties - small input changes should produce wildly different outputs.

### 3. Ignoring Hot Keys

Consistent hashing distributes keys evenly, not load evenly. If one key gets 1000x more reads than others, the server owning that key still melts. You need a separate strategy for hot keys - replication, caching tiers, or key splitting.

### 4. No Replication Strategy

Consistent hashing tells you which node owns a key. It doesn't give you fault tolerance. If that node dies, the data is gone. You need to replicate to the next N nodes on the ring (Dynamo-style) or use a separate replication mechanism.

### 5. Ring Membership Disagreements

Every client needs the same view of the ring. If client A thinks there are 5 servers and client B thinks there are 6, they'll disagree on key ownership. Use a consensus system (ZooKeeper, etcd, Consul) to manage ring membership, or accept eventual consistency in the ring view.

### 6. Cascade Failure on Node Removal

When a node dies, its keys move to the next server clockwise. That server now handles its own load plus the dead node's load. If this pushes it over capacity, it fails too, cascading further. Bounded-load consistent hashing or capacity-aware placement helps prevent this.

---

## Quick Reference

### When to Use Consistent Hashing

| Scenario                              | Use Consistent Hashing? | Why                                        |
|---------------------------------------|-------------------------|--------------------------------------------|
| Fixed number of shards, no changes    | No                      | Modulo hashing is simpler and works fine   |
| Dynamic cluster, nodes join/leave     | Yes                     | Minimal key redistribution                 |
| Need sticky sessions                  | Yes                     | Same key always maps to same server        |
| Small cluster (<5 nodes)              | Maybe                   | Benefits are smaller, but still valid      |
| Need perfect balance                  | Use bounded-load variant| Standard consistent hashing isn't perfect  |
| Peer-to-peer / decentralized         | Yes                     | No central coordinator needed for routing  |

### Complexity

| Operation              | Time         | Notes                                    |
|------------------------|--------------|------------------------------------------|
| Key lookup             | O(log N)     | Binary search on sorted ring positions   |
| Add node               | O(K/N + log N) | Move K/N keys, insert into ring        |
| Remove node            | O(K/N + log N) | Move K/N keys, remove from ring        |
| Ring memory            | O(N * V)     | N nodes times V virtual nodes each       |

Where N = number of nodes, K = number of keys, V = virtual nodes per server.

### Algorithm Comparison

| Algorithm              | Lookup   | Memory  | Balance    | Arbitrary Removal |
|------------------------|----------|---------|------------|-------------------|
| Modulo hashing         | O(1)     | O(1)    | Good       | Catastrophic      |
| Consistent hashing     | O(log N) | O(N*V)  | Good w/ vnodes | Minimal impact |
| Jump hashing           | O(ln N)  | O(1)    | Excellent  | Not supported     |
| Rendezvous hashing     | O(N)     | O(N)    | Excellent  | Minimal impact    |
| Bounded-load CH        | O(log N) | O(N*V)  | Excellent  | Minimal impact    |

---

## Hands-On Code Labs

The `code/` directory contains runnable Python demos:

| File                      | What It Demonstrates                                         |
|---------------------------|--------------------------------------------------------------|
| `naive_vs_consistent.py`  | Side-by-side comparison of modulo vs consistent hashing      |
| `hash_ring.py`            | Full consistent hash ring with vnodes and weighted nodes     |
| `virtual_nodes.py`        | How vnode count affects distribution uniformity              |
| `distributed_cache.py`    | Working distributed cache with node add/remove              |

Run any lab:

```bash
cd code/
python naive_vs_consistent.py
python hash_ring.py
python virtual_nodes.py
python distributed_cache.py
```

---

## What's Next?

- **Chapter 21:** [Bloom Filters & Probabilistic Data Structures](../21-bloom-filters/)
- **Chapter 22:** [Merkle Trees & Anti-Entropy](../22-merkle-trees/)
- **Chapter 23:** [Conflict Resolution & CRDTs](../23-conflict-resolution/)

---

*Consistent hashing is one of those algorithms that shows up everywhere once you know what to look for. From your CDN to your database to your cache layer - it's the reason adding a server doesn't set the building on fire.*
