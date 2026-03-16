# Search Autocomplete - Code Lab

Hands-on implementations of trie-based autocomplete, a Flask API, query aggregation, and performance benchmarking.

## What's Included

| File | Description |
|------|-------------|
| `trie.py` | Trie with insert, prefix search, and top-k ranking |
| `autocomplete_server.py` | Flask API serving autocomplete suggestions |
| `query_aggregator.py` | Aggregates search queries with frequency counting and time decay |
| `autocomplete_benchmark.py` | Performance test measuring lookup times across large datasets |

## Prerequisites

```bash
pip install flask requests
```

## Running the Demos

### 1. Trie Data Structure

Builds a trie from sample queries, runs prefix searches, and shows top-k results:

```bash
python trie.py
```

### 2. Autocomplete API Server

Starts a Flask server with autocomplete endpoints. Try it with curl or a browser:

```bash
python autocomplete_server.py

# In another terminal:
curl "http://localhost:5000/autocomplete?q=wea"
curl "http://localhost:5000/autocomplete?q=pyt&k=5"
curl http://localhost:5000/stats
```

### 3. Query Aggregator

Simulates collecting raw search logs, aggregating frequencies, and applying time-weighted decay:

```bash
python query_aggregator.py
```

### 4. Performance Benchmark

Generates a large dataset of queries, builds a trie, and measures lookup performance:

```bash
python autocomplete_benchmark.py
```
