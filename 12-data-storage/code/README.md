# Chapter 12 - Code Lab: Data Storage & Object Stores

Hands-on labs exploring block, file, and object storage models, automatic
tiering, and erasure coding for fault tolerance.

---

## Prerequisites

```bash
pip install flask requests
```

No external services needed - everything runs locally with in-memory simulation.

---

## Lab 1: Storage Types Comparison

**File:** `storage_types.py`

Simulates the three fundamental storage models - block, file, and object - and
compares their performance characteristics. You'll see how each model handles
writes and reads differently, and understand the tradeoffs between raw speed,
structure, and metadata richness.

```bash
python storage_types.py
```

**What to observe:**
- Block storage is fastest but has no metadata or naming
- File storage provides hierarchical structure with moderate overhead
- Object storage adds rich metadata but replaces objects entirely (no partial writes)

---

## Lab 2: S3-Like Object Store

**File:** `object_store.py`

A Flask-based object store that mimics the S3 API. Create buckets, store objects
with custom metadata, and retrieve them via HTTP. This demonstrates the REST
interface that makes object storage so portable.

```bash
python object_store.py
```

In a second terminal, run the built-in test client:

```bash
python object_store.py --test
```

**API endpoints:**

| Method | Path | Description |
|---|---|---|
| PUT | `/buckets/<name>` | Create a bucket |
| PUT | `/buckets/<bucket>/<key>` | Store an object |
| GET | `/buckets/<bucket>/<key>` | Retrieve an object |
| DELETE | `/buckets/<bucket>/<key>` | Delete an object |
| GET | `/buckets/<bucket>` | List objects in a bucket |
| HEAD | `/buckets/<bucket>/<key>` | Get object metadata |

---

## Lab 3: Storage Tiering

**File:** `storage_tiering.py`

Demonstrates automatic data migration between hot, warm, and cold tiers based on
access patterns. Objects that haven't been accessed recently get moved to cheaper
tiers. Objects that are accessed again get promoted back to hot storage.

```bash
python storage_tiering.py
```

**What to observe:**
- Objects start in the hot tier on creation
- Simulated time passing triggers demotion to warm, then cold
- Accessing a cold object promotes it back to hot
- Cost savings are calculated for each tier configuration

---

## Lab 4: Erasure Coding

**File:** `erasure_coding.py`

A simplified erasure coding implementation showing how data can survive multiple
disk failures without the 200% overhead of triple replication. Uses XOR-based
parity for clarity (production systems use Reed-Solomon codes).

```bash
python erasure_coding.py
```

**What to observe:**
- Data is split into chunks and parity chunks are computed
- Destroying up to the number of parity chunks still allows full reconstruction
- Storage overhead is far lower than replication
- The tradeoff: reconstruction requires computation

---

## Key Takeaways

1. Block storage gives raw performance; object storage gives scale and cost efficiency
2. Object stores use a flat namespace and HTTP - no filesystem semantics
3. Tiering is the easiest way to cut storage costs by 40-60%
4. Erasure coding trades CPU for storage efficiency - use it for cold data
