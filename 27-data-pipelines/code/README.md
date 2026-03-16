# Chapter 27 - Code Labs: Data Pipelines & ETL

Hands-on Python implementations of core data pipeline concepts.

## Prerequisites

- Python 3.8+
- No external dependencies (all labs use the standard library)

## Labs

| # | File | Description | Key Concepts |
|---|------|-------------|--------------|
| 1 | `map_reduce.py` | MapReduce word count | Map, shuffle, reduce phases; parallel mappers |
| 2 | `batch_pipeline.py` | Multi-stage batch ETL pipeline | Extract, transform, load; validation gates; pipeline metrics |
| 3 | `stream_processor.py` | Real-time stream processor | Tumbling windows, sliding windows, event time processing |
| 4 | `dag_executor.py` | DAG-based pipeline executor | Dependency resolution, topological sort, parallel task execution |

## Running the Labs

Each lab is standalone - just run it directly:

```bash
python map_reduce.py
python batch_pipeline.py
python stream_processor.py
python dag_executor.py
```

## What to Look For

- **map_reduce.py** - Watch how the shuffle phase groups intermediate results by key. Notice how multiple mappers can work on different chunks independently.
- **batch_pipeline.py** - Pay attention to the validation step between stages. One bad record shouldn't tank the whole pipeline.
- **stream_processor.py** - Compare tumbling vs sliding window output. Same data, different groupings, different results.
- **dag_executor.py** - Notice which tasks run in parallel vs sequentially. The executor figures this out from the dependency graph alone.
