# Chapter 21 - Code Labs: Bloom Filters & Probabilistic Data Structures

Hands-on implementations of probabilistic data structures for system design.

## Labs

| # | File | What You'll Learn |
|---|------|-------------------|
| 1 | [`bloom_filter.py`](bloom_filter.py) | Bloom filter with configurable false positive rate, optimal hash count, and fill rate monitoring |
| 2 | [`count_min_sketch.py`](count_min_sketch.py) | Count-Min Sketch for frequency estimation with error analysis on stream data |
| 3 | [`hyperloglog.py`](hyperloglog.py) | HyperLogLog for cardinality estimation with accuracy comparison against exact counting |
| 4 | [`practical_bloom.py`](practical_bloom.py) | Real-world URL deduplication and cache miss prevention using Bloom filters |

## Running the Labs

Each file is standalone - no dependencies beyond Python 3.7+ standard library:

```bash
python bloom_filter.py
python count_min_sketch.py
python hyperloglog.py
python practical_bloom.py
```

## Key Takeaways

- **Bloom filters** give definite negatives and probable positives - never the reverse
- **Count-Min Sketch** only over-estimates frequencies, never under-estimates
- **HyperLogLog** estimates cardinality in ~12 KB regardless of dataset size
- All three trade a small, bounded error for massive memory savings
