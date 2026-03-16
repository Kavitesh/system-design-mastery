# Chapter 27 - Data Pipelines & ETL

> Every company thinks they need real-time streaming. Most of them actually need a cron job that runs every 15 minutes.

📖 [Read the full article on Medium](#) / 🎬 [Watch on YouTube](#)

---

## Table of Contents

- [Why Data Pipelines Matter](#why-data-pipelines-matter)
- [ETL vs ELT - The Order Matters](#etl-vs-elt---the-order-matters)
- [Batch Processing vs Stream Processing](#batch-processing-vs-stream-processing)
- [MapReduce - The Grandfather of Big Data](#mapreduce---the-grandfather-of-big-data)
- [Apache Spark - MapReduce's Faster Successor](#apache-spark---mapreduces-faster-successor)
- [Stream Processing with Apache Flink](#stream-processing-with-apache-flink)
- [DAGs - Pipelines as Graphs](#dags---pipelines-as-graphs)
- [Apache Airflow - The Pipeline Orchestrator](#apache-airflow---the-pipeline-orchestrator)
- [Data Quality and Validation](#data-quality-and-validation)
- [Backfill and Reprocessing](#backfill-and-reprocessing)
- [Exactly-Once Processing](#exactly-once-processing)
- [Lambda Architecture](#lambda-architecture)
- [Kappa Architecture](#kappa-architecture)
- [Batch vs Stream - The Full Comparison](#batch-vs-stream---the-full-comparison)
- [Real-World Examples](#real-world-examples)
- [Common Pitfalls](#common-pitfalls)
- [Code Lab](#code-lab)
- [What's Next?](#whats-next)

---

## Why Data Pipelines Matter

Raw data is useless. A database full of click events, server logs, and transaction records doesn't answer any questions by itself. You need pipelines to turn that raw material into something actionable - dashboards, recommendations, fraud scores, search indexes.

A **data pipeline** is a series of processing steps that moves data from one system to another, transforming it along the way. It's plumbing. Unsexy, critical plumbing.

Here's the thing most tutorials won't tell you: the hard part of data pipelines isn't the processing logic. It's handling failures, managing state, dealing with late-arriving data, and figuring out what went wrong at 3 AM when your pipeline silently produced garbage results for the last six hours.

---

## ETL vs ELT - The Order Matters

**ETL** (Extract, Transform, Load) and **ELT** (Extract, Load, Transform) sound like a trivial reordering. They're not. They represent fundamentally different philosophies about where computation should happen.

### ETL - Transform Before Loading

```
Source DB --> [Extract] --> [Transform] --> [Load] --> Data Warehouse
```

The traditional approach. You pull data out, clean it up, reshape it, then load it into your destination. This made sense when storage was expensive and warehouses were slow - you wanted to load only clean, processed data.

**When to use ETL:**
- Destination storage is expensive (you're paying per GB)
- You need strict data quality before anything hits the warehouse
- Compliance requires you to filter sensitive data before it lands anywhere
- Your transformations reduce data volume significantly

### ELT - Load First, Transform Later

```
Source DB --> [Extract] --> [Load] --> Data Lake --> [Transform] --> Analytics
```

The modern approach. Dump everything raw into cheap storage (S3, GCS, a data lake), then transform it using the compute power of your warehouse (BigQuery, Snowflake, Redshift).

**When to use ELT:**
- Storage is cheap (cloud object storage costs pennies per GB)
- Your warehouse has serious compute power
- You don't know all the questions you'll want to ask yet
- Multiple teams need the same raw data transformed differently

### The Honest Take

ELT has won for most use cases. Storage got cheap, warehouses got powerful, and keeping raw data around means you can reprocess it when requirements change. ETL still makes sense when you're dealing with PII regulations or when your source data is orders of magnitude larger than what you actually need.

---

## Batch Processing vs Stream Processing

This is the most important architectural decision in pipeline design, and teams get it wrong constantly.

**Batch processing** collects data over a period, then processes it all at once. Think: "every night at 2 AM, crunch yesterday's numbers."

**Stream processing** handles data record by record as it arrives. Think: "every time a user clicks, update the count immediately."

| Aspect | Batch | Stream |
|--------|-------|--------|
| Latency | Minutes to hours | Milliseconds to seconds |
| Throughput | Very high (optimized for bulk) | Lower per-record, but continuous |
| Complexity | Simpler to reason about | Significantly harder |
| Error recovery | Rerun the whole batch | Complex checkpointing needed |
| Cost | Cheaper (use spot instances) | More expensive (always running) |
| Data completeness | All data present at processing time | Must handle late/out-of-order data |

**The rule of thumb:** start with batch. Move to streaming only when batch latency is genuinely unacceptable for your use case. "It would be cool to have real-time" is not a valid reason to triple your infrastructure complexity.

---

## MapReduce - The Grandfather of Big Data

Google published the MapReduce paper in 2004 and changed everything. The idea is simple but powerful: break a massive computation into two phases that can be parallelized across thousands of machines.

### The Three Phases

**Map** - Take each input record and emit zero or more key-value pairs.

**Shuffle** - Group all values by key. This is the expensive network operation where data moves between machines.

**Reduce** - For each key, combine all its values into a final result.

### Classic Example: Word Count

```
Input:  "the cat sat on the mat"

Map phase:
  "the" -> 1, "cat" -> 1, "sat" -> 1, "on" -> 1, "the" -> 1, "mat" -> 1

Shuffle phase:
  "the" -> [1, 1], "cat" -> [1], "sat" -> [1], "on" -> [1], "mat" -> [1]

Reduce phase:
  "the" -> 2, "cat" -> 1, "sat" -> 1, "on" -> 1, "mat" -> 1
```

### Why MapReduce Works at Scale

The key insight is that Map and Reduce are both **embarrassingly parallel**. If you have 1 TB of text, split it into 1,000 chunks of 1 GB each. Run Map on 1,000 machines simultaneously. Shuffle groups things by key. Run Reduce on each key group independently. You've just processed 1 TB using 1,000 commodity machines.

### Why Nobody Uses Raw MapReduce Anymore

MapReduce has real problems:
- Everything goes through disk between stages (slow)
- Only two stages means you chain multiple MapReduce jobs for complex logic
- Writing raw Map and Reduce functions is tedious for SQL-like operations
- No support for iterative algorithms (machine learning needs many passes)

This is why Spark ate Hadoop's lunch.

---

## Apache Spark - MapReduce's Faster Successor

Spark kept MapReduce's distributed computing model but fixed its biggest flaws:

1. **In-memory processing** - Intermediate results stay in RAM instead of hitting disk. This makes Spark 10-100x faster for iterative workloads.

2. **Rich API** - Instead of just Map and Reduce, Spark gives you `filter`, `join`, `groupBy`, `window`, and dozens of other operations. You write transformations in Python, Scala, or SQL.

3. **Lazy evaluation** - Spark builds a DAG of transformations and optimizes the execution plan before running anything.

4. **Unified engine** - Batch, streaming (Spark Structured Streaming), SQL, machine learning, and graph processing all in one framework.

### Spark Core Concepts

```
Driver Program
  |
  v
SparkContext --> Cluster Manager --> Worker Nodes
                                      |
                                      v
                                    Executors --> Tasks
```

- **RDD (Resilient Distributed Dataset)** - An immutable, partitioned collection of records. The original Spark abstraction.
- **DataFrame** - A distributed table with named columns. Think pandas but spread across a cluster. This is what you should use.
- **Transformation** - A lazy operation that defines a new dataset (map, filter, join).
- **Action** - An operation that triggers computation and returns a result (count, collect, save).

### When to Use Spark

Spark is the right call when your data doesn't fit on a single machine. If your dataset fits in memory on one box, just use pandas. Seriously. Spark's overhead isn't worth it for small data, and "small" these days means anything under ~50 GB.

---

## Stream Processing with Apache Flink

Flink treats streaming as the primary abstraction. Batch is just a special case of streaming where the input happens to be bounded. This sounds academic, but it means Flink handles time and state better than anything else.

### Core Concepts

**Event Time vs Processing Time** - Event time is when something actually happened. Processing time is when your system sees it. These can differ by seconds, minutes, or even hours. Flink lets you process based on event time, which is almost always what you want.

**Windows** - Grouping unbounded streams into finite chunks for aggregation.

| Window Type | Description | Use Case |
|-------------|-------------|----------|
| Tumbling | Fixed-size, non-overlapping | "Count clicks per minute" |
| Sliding | Fixed-size, overlapping | "Average over last 5 min, updated every 1 min" |
| Session | Gap-based, variable size | "Group user activity with 30-min idle timeout" |

**Watermarks** - Flink's mechanism for handling late data. A watermark says "I believe all events with timestamp <= T have arrived." Events arriving after the watermark are considered late and can be handled separately.

**Checkpointing** - Flink periodically snapshots the state of all operators. If a failure occurs, it restores from the last checkpoint. This is how Flink achieves exactly-once semantics.

---

## DAGs - Pipelines as Graphs

Most real pipelines aren't linear. They're **Directed Acyclic Graphs** - sets of tasks with dependencies between them.

```
        [Extract Users] --> [Clean Users] --\
                                             \
                                              --> [Join] --> [Load to Warehouse]
                                             /
[Extract Orders] --> [Clean Orders] --------/
                  \
                   --> [Compute Metrics] --> [Load to Dashboard]
```

DAG properties:
- **Directed** - Edges have a direction (task A must finish before task B starts)
- **Acyclic** - No circular dependencies (if A depends on B, B can't depend on A)
- **Nodes** - Individual processing tasks
- **Edges** - Dependencies between tasks

DAGs let a scheduler figure out what can run in parallel. In the example above, "Extract Users" and "Extract Orders" have no dependencies on each other - they can run simultaneously. "Join" has to wait for both cleaning steps to finish.

---

## Apache Airflow - The Pipeline Orchestrator

Airflow is the de facto standard for orchestrating batch data pipelines. It doesn't process data itself - it tells other systems when and in what order to process data.

### Core Concepts

- **DAG** - A Python file defining tasks and their dependencies
- **Operator** - A template for a task (BashOperator, PythonOperator, PostgresOperator)
- **Task** - A specific instance of an operator within a DAG
- **Task Instance** - A specific run of a task for a particular execution date
- **Scheduler** - Determines when DAGs and tasks should run
- **Executor** - Determines how tasks run (locally, on Celery, on Kubernetes)

### What Airflow is Good At

- Scheduling complex DAGs with dependencies
- Retrying failed tasks automatically
- Backfilling historical data
- Providing visibility into pipeline status
- Alerting on failures

### What Airflow is Bad At

- Real-time / streaming workloads (it's batch-oriented)
- Sub-minute scheduling (its scheduler checks every few seconds)
- Data processing itself (use it to orchestrate, not to crunch numbers)
- Passing large amounts of data between tasks (use external storage)

---

## Data Quality and Validation

Data quality issues are the #1 cause of pipeline failures that nobody notices until it's too late. Bad data doesn't throw errors - it just silently corrupts your downstream analyses.

### Validation Strategies

**Schema validation** - Does the data match the expected structure? Are all required fields present? Are types correct?

**Range checks** - Is this value within expected bounds? A user age of 350 is probably wrong.

**Null checks** - Which fields should never be null? Which fields are nullable but suspicious if null rates exceed a threshold?

**Volume checks** - Did we receive roughly the expected number of records? Getting 100 rows when you normally get 100,000 is a red flag.

**Freshness checks** - Is the most recent record timestamp within the expected window? If your "real-time" data is 4 hours stale, something is broken.

**Cross-dataset consistency** - Do row counts match between related tables? Do foreign key relationships hold?

### The Golden Rule

Never trust data from upstream systems. Validate at every stage boundary. The source system's developers will change their schema without telling you. It's not a matter of if, it's when.

---

## Backfill and Reprocessing

Your business logic will change. Your data schema will evolve. Bugs will be discovered. You will need to reprocess historical data. This is called **backfilling**, and if you didn't plan for it, you're going to have a bad time.

### Making Pipelines Backfill-Friendly

1. **Idempotency** - Running the same pipeline twice with the same input should produce the same output. No duplicates, no side effects.

2. **Partitioning by time** - Process data in time-bounded chunks (daily, hourly). This lets you reprocess specific time ranges without reprocessing everything.

3. **Immutable inputs** - Don't modify source data. Write results to a new partition or table. This lets you compare old and new results.

4. **Parameterized dates** - Never hardcode dates. Every pipeline should accept the processing date as a parameter.

5. **Keep raw data** - Always keep the raw, unprocessed data. If you only keep the transformed output, you can't reprocess when your transformation logic changes.

---

## Exactly-Once Processing

This is the holy grail of data pipelines and one of the most misunderstood concepts in distributed systems.

**At-most-once** - Process each record zero or one times. Fast but you might lose data. Never acceptable for financial data.

**At-least-once** - Process each record one or more times. Simple to implement but you get duplicates.

**Exactly-once** - Process each record exactly one time. What everyone wants. Much harder than it sounds.

### How Exactly-Once Actually Works

True exactly-once processing across distributed systems is technically impossible (thanks, network partitions). What systems actually implement is **effectively exactly-once** through one of two approaches:

1. **Idempotent writes** - Process at-least-once, but make your writes idempotent so duplicates have no effect. Use upserts instead of inserts. Use deterministic IDs.

2. **Transactional processing** - Atomically commit the processing result and the offset/checkpoint together. If either fails, both roll back. This is what Flink and Kafka Streams do with their exactly-once guarantees.

---

## Lambda Architecture

Lambda architecture runs batch and stream processing in parallel to get both accuracy and low latency.

```
                    [Batch Layer]
                   /  (accurate,     \
Raw Data ---------     slow)          --> [Serving Layer] --> Queries
                   \                  /
                    [Speed Layer]
                     (approximate,
                      fast)
```

**Batch layer** - Processes all historical data periodically. Produces accurate, complete results. Runs every few hours.

**Speed layer** - Processes real-time data as it arrives. Produces approximate results that fill the gap since the last batch run.

**Serving layer** - Merges results from both layers to answer queries. Uses batch results as the base, overlays speed layer results for recent data.

### The Problem with Lambda

You're maintaining two codebases that do the same thing - one for batch, one for streaming. Every business logic change needs to be implemented twice. Testing is painful. Debugging discrepancies between the two layers is a nightmare. The operational cost is significant.

---

## Kappa Architecture

Kappa architecture says: what if we just used streaming for everything?

```
Raw Data --> [Log / Event Stream] --> [Stream Processor] --> [Serving Layer] --> Queries
```

Instead of maintaining separate batch and speed layers, you keep all raw data in a replayable log (like Kafka) and process everything through a single stream processing engine. Need to reprocess? Replay the log through an updated version of your stream processor.

### Kappa vs Lambda

| Aspect | Lambda | Kappa |
|--------|--------|-------|
| Codebases to maintain | Two (batch + stream) | One |
| Operational complexity | High | Lower |
| Reprocessing | Run batch job | Replay from log |
| Storage cost | Moderate | Higher (must retain full log) |
| Maturity | Well-established | Newer, less battle-tested |
| Best for | Mixed latency requirements | Stream-first organizations |

### The Honest Take

Lambda architecture is being phased out. If you're starting a new project, Kappa is usually the better choice. But plenty of companies run Lambda successfully - if it works and the operational cost is manageable, don't rewrite it just because a blog post told you Kappa is cooler.

---

## Batch vs Stream - The Full Comparison

| Dimension | Batch Processing | Stream Processing |
|-----------|-----------------|-------------------|
| Latency | Minutes to hours | Milliseconds to seconds |
| Data completeness | All data available | Must handle incomplete data |
| Throughput | Optimized for bulk | Continuous but lower per-record |
| Error handling | Rerun entire batch | Checkpoint and replay |
| Windowing | Natural (process one day at a time) | Explicit (define window boundaries) |
| Resource usage | Burst (use resources, then release) | Constant (always running) |
| Cost model | Pay for compute time | Pay for always-on infrastructure |
| Late data | Not an issue (data already complete) | Major concern (watermarks needed) |
| State management | Stateless (read input, write output) | Stateful (maintain aggregations) |
| Debugging | Examine input and output files | Inspect checkpoints and state stores |
| Testing | Run on sample files | Simulate time progression |
| Complexity | Lower | Significantly higher |

---

## Real-World Examples

### Netflix - Content Recommendations

Netflix processes over 1 trillion events per day. Their pipeline:
- **Batch layer** - Spark jobs process viewing history nightly to update recommendation models
- **Stream layer** - Flink processes real-time viewing activity to adjust recommendations mid-session
- **Key challenge** - Joining streaming user activity with batch-computed model scores

### Spotify - Discover Weekly

Your Discover Weekly playlist is a pure batch pipeline:
- **Monday morning** - A massive Spark job processes the previous week's listening data for all users
- **Collaborative filtering** - "Users who listened to X also listened to Y"
- **Processing time** - The full pipeline takes several hours for 500+ million users
- **Why batch works** - Weekly playlists don't need real-time updates. Batch is the perfect fit.

### Uber - Dynamic Pricing

Uber's surge pricing is a stream processing pipeline:
- **Input** - Real-time rider requests and driver locations
- **Processing** - Flink computes supply/demand ratios per geographic cell
- **Output** - Updated price multipliers pushed to the app within seconds
- **Why streaming is required** - A 5-minute-old surge price is useless. Demand shifts fast.

---

## Common Pitfalls

### 1. Choosing Streaming When Batch Would Work

The most common mistake. Streaming is 3-5x more complex to build, test, debug, and operate. If your users can tolerate 15-minute-old data, use batch.

### 2. Not Planning for Schema Evolution

Your upstream data sources will change their schemas. Fields get added, renamed, or removed. If your pipeline breaks on any unexpected field, you'll be fighting fires constantly. Use schema registries and build pipelines that handle schema changes gracefully.

### 3. Ignoring Data Quality

"The pipeline ran successfully" doesn't mean "the pipeline produced correct results." A pipeline that loads 0 rows without error is worse than one that crashes - at least crashes get noticed.

### 4. Tightly Coupling Pipeline Stages

If Stage B reads directly from Stage A's output directory, you can't change Stage A's output format without breaking Stage B. Use schemas, contracts, or intermediate storage layers.

### 5. No Monitoring or Alerting

You need alerts on:
- Pipeline failures (obvious)
- Pipeline taking longer than usual (less obvious)
- Output data volume anomalies (critical)
- Data freshness violations (critical)
- Null rate spikes in key fields (subtle but dangerous)

### 6. Not Making Pipelines Idempotent

If you can't safely rerun your pipeline, you can't recover from failures. Use upserts, partition overwrites, or transactional writes.

### 7. Ignoring Backpressure

When a streaming pipeline can't keep up with input volume, what happens? Without backpressure handling, it either drops data or runs out of memory. Neither is acceptable.

---

## Code Lab

Hands-on implementations to solidify these concepts:

| Lab | File | What You'll Learn |
|-----|------|-------------------|
| 1 | `map_reduce.py` | MapReduce word count with map, shuffle, and reduce phases |
| 2 | `batch_pipeline.py` | Multi-stage batch ETL with extract, transform, load, and validation |
| 3 | `stream_processor.py` | Real-time stream processor with tumbling and sliding windows |
| 4 | `dag_executor.py` | DAG-based pipeline executor with dependency resolution and parallel execution |

See the [code/README.md](code/README.md) for setup and usage instructions.

---

## What's Next?

- **Chapter 28:** [Authentication & Authorization](../28-auth/) - OAuth, JWT, RBAC, and securing your systems
- **Chapter 29:** [Search Systems](../29-search/) - Full-text search, inverted indexes, and ranking algorithms
