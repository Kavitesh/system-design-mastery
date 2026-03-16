# Chapter 13 - Code Lab: Search & Indexing

Hands-on demos for the three major indexing strategies - B-trees, LSM
trees, and inverted indexes - plus a Flask search API that ties them
together.

---

## Files

| File | What It Demonstrates |
|---|---|
| `btree_demo.py` | B-tree insert, search, and range queries with performance comparison against linear scan |
| `inverted_index.py` | Full-text search engine with tokenization, stop word removal, and TF-IDF ranking |
| `lsm_tree.py` | LSM tree simulation with in-memory memtable, SSTable flushes, and compaction |
| `search_engine.py` | Flask REST API wrapping the inverted index for HTTP-based search |

---

## Prerequisites

```bash
pip install flask
```

No other dependencies - the B-tree, inverted index, and LSM tree
implementations are pure Python.

---

## Running the Demos

### 1. B-Tree Demo

```bash
python btree_demo.py
```

Inserts 10,000 keys into a B-tree, then compares search and range query
performance against a naive linear scan. You'll see the difference
between O(log n) and O(n) directly in the timing output.

### 2. Inverted Index

```bash
python inverted_index.py
```

Builds an inverted index from a small document corpus, then runs search
queries with TF-IDF ranked results. Shows how tokenization, stop word
removal, and scoring work together.

### 3. LSM Tree

```bash
python lsm_tree.py
```

Simulates the LSM tree write path: writes go to a memtable, the
memtable flushes to SSTables when full, and background compaction merges
SSTables. Watch the levels fill and compact in real time.

### 4. Search Engine API

```bash
python search_engine.py
```

Starts a Flask server on port 5000 with these endpoints:

| Method | Endpoint | Description |
|---|---|---|
| POST | `/index` | Add a document (`{"id": "...", "text": "..."}`) |
| GET | `/search?q=...` | Search with TF-IDF ranked results |
| GET | `/stats` | Index statistics (document count, vocabulary size) |

Example usage with curl:

```bash
# Index documents
curl -X POST http://localhost:5000/index \
  -H "Content-Type: application/json" \
  -d '{"id": "1", "text": "B-trees are the default index in PostgreSQL"}'

curl -X POST http://localhost:5000/index \
  -H "Content-Type: application/json" \
  -d '{"id": "2", "text": "LSM trees optimize for write-heavy workloads"}'

curl -X POST http://localhost:5000/index \
  -H "Content-Type: application/json" \
  -d '{"id": "3", "text": "PostgreSQL supports both B-tree and GIN indexes"}'

# Search
curl "http://localhost:5000/search?q=PostgreSQL+index"

# Stats
curl http://localhost:5000/stats
```

---

## Key Observations

- The B-tree demo shows that indexed lookups are orders of magnitude
  faster than scanning, even at modest data sizes.
- The inverted index demo shows that TF-IDF naturally ranks more
  specific terms higher - a search for "PostgreSQL B-tree" will weight
  "B-tree" appropriately based on how rare it is in the corpus.
- The LSM tree demo shows the write path clearly: fast memtable inserts,
  periodic flushes, and background compaction. Notice how reads must
  check multiple levels.
- The search API shows how these building blocks compose into a real
  service.
