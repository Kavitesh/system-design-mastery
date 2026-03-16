# Chapter 21 - Bloom Filters & Probabilistic Data Structures

> Every exact answer has a cost. Probabilistic data structures let you trade a sliver of accuracy for massive savings in memory and speed - and in distributed systems, that trade is almost always worth it.

📖 **Article:** [Medium - Bloom Filters & Probabilistic Data Structures](#)
🎬 **Video:** [YouTube - Bloom Filters & Probabilistic Data Structures](#)

---

## Why Exact Answers Are Overrated

Here's a question that comes up constantly in system design: "Has this user seen this URL before?" You could store every URL in a hash set. For 1 billion URLs averaging 80 bytes each, that's 80 GB of memory. For a single membership check.

Now ask yourself - do you actually need a perfect answer? If you're filtering spam URLs, a 1% false positive rate means 1 in 100 clean URLs gets an extra check. That's fine. And instead of 80 GB, you need about 1.2 GB. That's the core bargain of probabilistic data structures.

Three structures dominate system design interviews and real production systems:

| Structure | Question It Answers | Error Type | Space |
|-----------|-------------------|------------|-------|
| **Bloom Filter** | "Is X in the set?" | False positives only | ~10 bits/element |
| **Count-Min Sketch** | "How many times has X appeared?" | Over-counts only | Fixed, small |
| **HyperLogLog** | "How many distinct elements?" | +/- ~0.8% typical | ~12 KB fixed |

The common thread: they all use hashing to compress information, they all have one-sided errors (never false negatives for Bloom filters, never under-counts for Count-Min Sketch), and they all use dramatically less memory than exact alternatives.

---

## Bloom Filters - The Workhorse

Burton Howard Bloom published this in 1970. Fifty-five years later, it's everywhere - from database engines to CDNs to your browser.

### How It Works

A Bloom filter is a bit array of `m` bits, initially all zeros, combined with `k` independent hash functions.

**Insert an element:**
1. Hash the element with each of the `k` hash functions
2. Set the resulting `k` bit positions to 1

**Query an element:**
1. Hash the element with each of the `k` hash functions
2. If ALL `k` positions are 1, answer "probably yes"
3. If ANY position is 0, answer "definitely no"

That asymmetry is the key insight. A zero bit is proof of absence - nothing that was inserted could have left that bit at zero. But all-ones could be a coincidence from other insertions.

### A Concrete Example

Bit array of 16 bits, 3 hash functions:

```
Insert "apple":  h1=2, h2=7, h3=11
[0,0,1,0,0,0,0,1,0,0,0,1,0,0,0,0]

Insert "banana": h1=3, h2=7, h3=14
[0,0,1,1,0,0,0,1,0,0,0,1,0,0,1,0]

Query "cherry":  h1=2, h2=3, h3=14
All bits are 1 -> "probably yes" (FALSE POSITIVE - cherry was never added)

Query "date":    h1=0, h2=5, h3=11
Bit 0 is 0 -> "definitely no" (CORRECT)
```

Notice position 7 got set by both "apple" and "banana." As the filter fills up, more collisions happen and false positive rates climb.

### The Math That Matters

After inserting `n` elements into a bit array of `m` bits using `k` hash functions, the false positive probability is approximately:

```
p = (1 - e^(-kn/m))^k
```

Three relationships you should internalize:

1. **More bits per element (m/n) = lower false positive rate.** At 10 bits/element with optimal k, you get roughly 1% false positives.
2. **Optimal number of hash functions: k = (m/n) * ln(2) ~ 0.693 * (m/n).** Too few hash functions waste bits. Too many set too many bits.
3. **Doubling bits per element squares the false positive rate.** Going from 10 to 20 bits/element drops you from 1% to 0.01%.

| Bits per element (m/n) | Optimal k | False Positive Rate |
|------------------------|-----------|-------------------|
| 5 | 3 | 9.2% |
| 8 | 6 | 2.2% |
| 10 | 7 | 0.82% |
| 15 | 10 | 0.07% |
| 20 | 14 | 0.006% |

### What You Can't Do

Standard Bloom filters don't support deletion. Setting a bit to 0 might erase evidence of other elements that hash to that position. This is a hard constraint, not a minor inconvenience - if your use case needs deletion, you need a different structure.

You also can't enumerate what's in the filter. A Bloom filter answers "is X a member?" but it can't tell you "give me all members." The original items are gone - only their hash footprints remain.

And you can't resize. Once you pick `m` bits, that's it. If you underestimated, you either live with a higher false positive rate or rebuild from scratch with a larger filter. This is why capacity planning matters so much upfront.

### The Kirsch-Mitzenmacher Optimization

Computing `k` independent hash functions sounds expensive. In practice, you don't need to. Kirsch and Mitzenmacher proved in 2006 that you can derive all `k` hashes from just two base hashes:

```
h_i(x) = h1(x) + i * h2(x)    for i = 0, 1, ..., k-1
```

This produces the same false positive guarantees as `k` truly independent hash functions. It's why real implementations use just two hash computations (often MD5 + SHA1, or two seeds of MurmurHash) regardless of how large `k` is.

---

## Counting Bloom Filters

The fix for deletion: replace each bit with a counter (typically 4 bits). Insert increments the counters; delete decrements them. Now you can remove elements without corrupting the filter.

The trade-off is real: 4x the memory. A standard Bloom filter using 10 bits/element becomes 40 bits/element as a counting variant. That's still far less than storing actual elements, but it's worth knowing the cost.

**When to use counting Bloom filters:**
- Session tracking where sessions expire and need removal
- Cache invalidation lists that change over time
- Routing tables with dynamic entries

**When to stick with standard Bloom filters:**
- Write-once scenarios (URL deduplication, one-time password checks)
- Append-only data (log processing, event deduplication)
- When you can rebuild the filter periodically instead of deleting

### Counter Overflow

With 4-bit counters, the maximum value is 15. If any counter would exceed 15, you stop incrementing it (saturating arithmetic). In practice, this rarely happens because hash functions spread elements across the array. But if it does happen, that counter is permanently stuck at 15 and you can't safely delete elements that hash to it. Some implementations use 8-bit or 16-bit counters to push this limit further at the cost of more memory.

---

## Scalable Bloom Filters

Standard Bloom filters need a capacity estimate upfront. Get it wrong and your false positive rate degrades. Scalable Bloom filters solve this by chaining multiple filters together:

1. Start with a small Bloom filter (BF_0) for the initial capacity
2. When it fills up past a threshold, create a new filter (BF_1) with tighter false positive rate
3. New inserts go to the latest filter; queries check all filters

The false positive rates are set so they form a geometric series (e.g., p, p*r, p*r^2, ...) where r < 1. The total false positive rate converges to a bounded value even as you add more filters.

The downside: queries get slower as you add more filter layers, since you have to check each one. In practice, you rarely exceed 3-4 layers before rebuilding. PostgreSQL's `bloom` extension and Apache Spark both use variants of this approach.

---

## Count-Min Sketch - Frequency Estimation

A Count-Min Sketch answers "how many times has X appeared?" It's like a 2D version of a Bloom filter - a grid of counters instead of a row of bits.

### Structure

- `d` rows (each with its own hash function)
- `w` columns (width of each row)
- Total space: `d * w` counters

### Operations

**Increment(x):**
For each row `i`, hash `x` to get column `j = h_i(x)`, then increment `counter[i][j]`.

**Query(x):**
For each row `i`, hash `x` to get column `j = h_i(x)`, read `counter[i][j]`. Return the **minimum** across all rows.

### Why the Minimum?

Collisions only inflate counts, never deflate them. If element Y collides with X in row 1, that row's counter is too high. But in row 2, different hash function, probably no collision. Taking the minimum across rows gives you the least-inflated estimate.

The error guarantee: with width `w = ceil(e/epsilon)` and depth `d = ceil(ln(1/delta))`, the estimate exceeds the true count by at most `epsilon * N` with probability at least `1 - delta`, where `N` is the total count of all elements.

### Practical Sizing

For a stream of 1 million events where you want estimates within 0.1% of total count with 99.9% confidence:

- Width: `ceil(e / 0.001)` = 2,719
- Depth: `ceil(ln(1000))` = 7
- Total counters: 19,033
- Memory: ~76 KB (4-byte counters)

Compare that to storing exact counts for potentially millions of distinct elements.

### Use Cases

| Application | Why Count-Min Sketch? |
|-------------|---------------------|
| Network traffic monitoring | Track packet frequencies per source IP without storing every IP |
| Trending topics | Find heavy hitters in a tweet stream |
| Database query optimization | Estimate join sizes without materializing |
| Ad click fraud | Flag IPs with suspiciously high click counts |

---

## HyperLogLog - Counting Distinct Elements

"How many unique visitors hit our site today?" The exact answer requires storing every visitor ID - potentially gigabytes. HyperLogLog answers this with about 12 KB of memory and typical error around 0.8%.

### The Core Insight

Hash each element and look at the binary representation. The probability of seeing a hash that starts with `k` leading zeros is `1/2^k`. So if the longest run of leading zeros you've seen is 17, you've probably seen around `2^17 = 131,072` distinct elements.

One observation is noisy. HyperLogLog reduces variance by splitting elements into `m` buckets (typically 2^14 = 16,384) using the first few bits of the hash, then tracking the maximum leading-zeros-plus-one in each bucket. The final estimate is a harmonic mean across all buckets, with bias corrections.

### The Formula

```
E = alpha_m * m^2 * (sum of 2^(-M[j]) for j=1..m)^(-1)
```

Where `alpha_m` is a bias correction constant (~0.7213 for large m) and `M[j]` is the maximum observed value in bucket `j`.

### Why 12 KB?

With 2^14 = 16,384 buckets and 6 bits per bucket (enough to track up to 2^63 distinct elements), you need 16,384 * 6 / 8 = 12,288 bytes. That's it. Twelve kilobytes to estimate cardinalities in the billions with sub-1% error.

### Sparse vs. Dense Representation

Real implementations (like Redis) don't allocate all 16,384 buckets upfront. They start with a sparse representation - only storing buckets that have been written to. When enough buckets fill, they switch to the dense 12 KB representation. This optimization means a HyperLogLog tracking a few hundred elements uses just a few hundred bytes instead of 12 KB.

### Redis Knows This

Redis has HyperLogLog as a native data type. `PFADD`, `PFCOUNT`, `PFMERGE`. The PF stands for Philippe Flajolet, who invented the algorithm. It uses exactly 12 KB per key (in dense mode), and you can merge multiple HyperLogLogs together - perfect for counting unique visitors across multiple servers.

```
PFADD visitors:page1 "user123" "user456" "user789"
PFADD visitors:page2 "user456" "user999"
PFMERGE visitors:total visitors:page1 visitors:page2
PFCOUNT visitors:total  -> approximately 4
```

Mergeability is a killer feature. You can count uniques per server, per time window, per page - then merge them to get totals without double-counting.

---

## Comparison - Exact vs. Probabilistic

| Operation | Exact Structure | Memory (1B elements) | Probabilistic | Memory | Error |
|-----------|----------------|---------------------|---------------|--------|-------|
| Membership | HashSet | ~80 GB | Bloom Filter | ~1.2 GB | 1% FP |
| Frequency | HashMap | ~80 GB | Count-Min Sketch | ~76 KB | Configurable |
| Cardinality | HashSet | ~80 GB | HyperLogLog | ~12 KB | ~0.8% |

The memory ratios are staggering. HyperLogLog uses roughly 6.7 million times less memory than an exact count. Even Bloom filters - the least dramatic improvement - still deliver a 60x reduction.

---

## Real-World Deployments

### Google Chrome Safe Browsing

Your browser checks every URL you visit against a list of known malicious sites. Google maintains millions of dangerous URLs. Chrome doesn't download the full list - it downloads a Bloom filter. When you visit a URL, Chrome checks the local Bloom filter first. Only on a positive match does it make a network request to Google's servers for confirmation. This keeps browsing fast and private.

### Apache Cassandra

Cassandra uses Bloom filters to avoid unnecessary disk reads. Each SSTable (on-disk data file) has an associated Bloom filter. Before reading a potentially large file from disk, Cassandra checks the Bloom filter. If it says "definitely not here," Cassandra skips that file entirely. With thousands of SSTables, this prevents enormous amounts of wasted I/O.

### Akamai CDN

Akamai found that roughly 75% of web objects are "one-hit wonders" - requested exactly once. Caching these wastes memory. They use a Bloom filter as a gatekeeper: an object only gets cached on its second request. The first request adds the URL to the Bloom filter; the second request finds it there and triggers caching. This simple optimization eliminated a huge fraction of cache churn.

### Medium's Recommendation Engine

Medium uses Bloom filters to track which articles each user has already seen, preventing repeated recommendations. The per-user Bloom filter is tiny compared to storing a full set of article IDs.

### Bitcoin SPV Nodes

Lightweight Bitcoin clients (SPV nodes) use Bloom filters to request only relevant transactions from full nodes. Instead of downloading every block, an SPV client sends a Bloom filter describing the addresses it cares about. The full node filters transactions against it and sends only matches. This makes mobile Bitcoin wallets practical.

### PostgreSQL and LevelDB

PostgreSQL uses Bloom filters in its `bloom` index type for multi-column approximate indexing. LevelDB and RocksDB use Bloom filters on each SSTable to skip files during point lookups - the same pattern as Cassandra. Google's Bigtable paper (2006) explicitly recommends Bloom filters for this purpose, and virtually every LSM-tree database has adopted them since.

---

## Beyond the Big Three

A few other probabilistic structures worth knowing about:

| Structure | Purpose | Key Property |
|-----------|---------|-------------|
| **Cuckoo Filter** | Membership (like Bloom) | Supports deletion, better space for low FP rates |
| **Quotient Filter** | Membership | Cache-friendly, mergeable, supports deletion |
| **MinHash** | Set similarity (Jaccard index) | Estimates how similar two sets are |
| **SimHash** | Document similarity | Locality-sensitive hashing for near-duplicate detection |
| **t-digest** | Quantile estimation | Accurate tail percentiles (p99, p999) in streaming data |

Cuckoo filters are increasingly popular as a Bloom filter replacement. They use cuckoo hashing to store fingerprints of elements, which means you can delete elements by removing their fingerprint. For false positive rates below about 3%, cuckoo filters actually use less space than Bloom filters. Redis's RedisBloom module supports both.

---

## Design Patterns

### Pattern 1 - The Cheap Pre-Filter

Put a Bloom filter in front of an expensive lookup. Most negatives get caught cheaply; only positives (true and false) hit the slow path.

```
Request -> Bloom Filter -> "definitely not" -> return miss
                        -> "maybe yes" -> check database -> return result
```

This works because most lookups are misses. If 99% of queries are for non-existent keys, and your Bloom filter has a 1% false positive rate, you eliminate 98% of database lookups.

### Pattern 2 - The Deduplication Gate

For stream processing, check each incoming element against a Bloom filter before processing:

```
New event -> Bloom Filter -> "probably seen" -> drop (accept rare duplicates)
                          -> "definitely new" -> process + add to filter
```

You'll never accidentally drop a truly new event (no false negatives). You might occasionally reprocess a duplicate (false positive leading to not-dropping), but that's usually harmless.

### Pattern 3 - The Distributed Counter

Deploy HyperLogLog instances on each server. Periodically merge them for global counts:

```
Server A: HLL_a (local uniques)
Server B: HLL_b (local uniques)
Server C: HLL_c (local uniques)

Global uniques = merge(HLL_a, HLL_b, HLL_c)
```

No coordination needed during writes. Merge is cheap and accurate. This is how you count unique visitors across a fleet of web servers without a centralized counter.

### Pattern 4 - The Frequency Cap

Use a Count-Min Sketch to enforce rate limits without per-user state:

```
Incoming request -> CMS.estimate(user_id) -> above limit? -> reject (429)
                                           -> below limit? -> CMS.increment(user_id) -> serve
```

This won't perfectly enforce limits (it over-counts, so some users get rate-limited slightly early), but it's vastly cheaper than maintaining exact counters for millions of users. Good enough for soft limits like "show this ad at most 5 times per user per day."

---

## Choosing the Right Structure

```
Do you need to track membership?
├── Yes -> Can you tolerate false positives?
│   ├── Yes -> Do elements need to be deleted?
│   │   ├── Yes -> Counting Bloom Filter
│   │   └── No  -> Standard Bloom Filter
│   └── No  -> Hash Set (pay the memory cost)
│
├── Need frequency counts?
│   ├── Approximate OK? -> Count-Min Sketch
│   └── Exact needed?   -> Hash Map
│
└── Need cardinality (count of distinct elements)?
    ├── Approximate OK? -> HyperLogLog
    └── Exact needed?   -> Hash Set
```

---

## Common Pitfalls

### 1. Forgetting to Size Your Bloom Filter

A Bloom filter sized for 1 million elements will degrade badly at 10 million. The false positive rate isn't linear - it gets dramatically worse as the filter fills. Always size for your expected maximum, with headroom.

### 2. Using Weak Hash Functions

You don't need cryptographic hashes. MurmurHash3, xxHash, or FNV work great and are much faster. For multiple hash functions, use the Kirsch-Mitzenmacher trick: generate two hashes `h1` and `h2`, then derive `k` hashes as `h_i(x) = h1(x) + i * h2(x)`. This is mathematically sound and faster than computing `k` independent hashes.

### 3. Ignoring the Base Rate

A 1% false positive rate sounds great until your query workload is 99.99% negatives. If you're checking 10 million lookups and 9,999,000 are for non-existent keys, you'll get ~99,990 false positives hitting your database. That might still be too many. Size accordingly.

### 4. Not Monitoring Fill Rate

Track how full your Bloom filter is. When the ratio of set bits exceeds about 50%, false positive rates start climbing steeply. Plan for periodic rebuilds or capacity increases.

### 5. Assuming Count-Min Sketch Errors Are Symmetric

Count-Min Sketch only over-estimates, never under-estimates. If your application penalizes over-counting differently from under-counting, this matters. For fraud detection (over-counting means more false alarms), it's usually fine. For billing (over-counting means overcharging), it's not.

---

## Interview Tips

When a system design question involves any of these keywords, consider probabilistic data structures:

- "Deduplicate" or "seen before" - Bloom filter
- "How many unique" or "count distinct" - HyperLogLog
- "Top-K" or "most frequent" or "heavy hitters" - Count-Min Sketch
- "At scale" with membership checks - Bloom filter pre-filter pattern
- "Limited memory" with counting - Count-Min Sketch or HyperLogLog

The strongest answer isn't "use a Bloom filter." It's "use a Bloom filter sized for N elements at P% false positive rate, which requires M bits - about X megabytes - and reduces database load by Y%." Show you understand the math and the trade-offs.

---

## Hands-On Labs

| Lab | Focus | File |
|-----|-------|------|
| Bloom Filter | Membership testing with configurable false positive rate | [`code/bloom_filter.py`](code/bloom_filter.py) |
| Count-Min Sketch | Frequency estimation on streaming data | [`code/count_min_sketch.py`](code/count_min_sketch.py) |
| HyperLogLog | Cardinality estimation with accuracy analysis | [`code/hyperloglog.py`](code/hyperloglog.py) |
| Practical Bloom | URL deduplication and cache miss prevention | [`code/practical_bloom.py`](code/practical_bloom.py) |

---

## What's Next?

- **Chapter 22:** [Clocks & Ordering](../22-clocks-ordering/)
- **Chapter 23:** [CRDTs & Eventual Consistency](../23-crdts/)
