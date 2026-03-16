# Databases - Code Lab

Hands-on demos showing relational vs NoSQL data models, ACID guarantees, performance trade-offs, and schema evolution strategies.

## What's Included

| File | Description |
|------|-------------|
| `sql_demo.py` | SQLite CRUD with joins, GROUP BY, and ACID transaction rollback |
| `nosql_comparison.py` | Document, key-value, and column-family stores side by side |
| `db_performance.py` | Benchmarks comparing read/write speed across data models |
| `schema_evolution.py` | How SQL and document stores handle schema changes differently |

## Prerequisites

Python 3.7+ is all you need. Every demo uses only the standard library (`sqlite3`, `json`, `time`). No external databases to install, no pip packages required.

## Running the Demos

### 1. SQL Demo - Relational Data with ACID

Builds an e-commerce schema, runs multi-table JOINs, and shows how transactions commit atomically or roll back entirely:

```bash
python sql_demo.py
```

### 2. NoSQL Comparison - Three Data Models

Simulates document, key-value, and column-family stores to show how each organizes data and what queries each supports:

```bash
python nosql_comparison.py
```

### 3. Performance Benchmarks

Inserts 10,000 records into each model, then compares lookup speed for point reads, key-based access, and full scans:

```bash
python db_performance.py
```

### 4. Schema Evolution

Adds columns to a SQL table (ALTER TABLE) vs inserting new document shapes - demonstrates the trade-off between enforced consistency and deployment flexibility:

```bash
python schema_evolution.py
```
