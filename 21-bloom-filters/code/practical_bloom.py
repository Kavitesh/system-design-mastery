"""
Practical Bloom Filter Applications
=====================================
Real-world use cases: URL deduplication for a web crawler,
cache miss prevention, and CDN one-hit-wonder filtering.

Run: python practical_bloom.py
"""

import math
import hashlib
import random
import sys

# ---------------------------------------------------------------------------
#  Bloom Filter (compact version for practical use)
# ---------------------------------------------------------------------------

class BloomFilter:
    def __init__(self, expected_items, fp_rate=0.01):
        self.size = int(-expected_items * math.log(fp_rate) / (math.log(2) ** 2))
        self.num_hashes = max(1, int((self.size / expected_items) * math.log(2)))
        self.bit_array = bytearray(math.ceil(self.size / 8))

    def _positions(self, item):
        raw = str(item).encode("utf-8")
        h1 = int(hashlib.md5(raw).hexdigest(), 16)
        h2 = int(hashlib.sha1(raw).hexdigest(), 16)
        return [(h1 + i * h2) % self.size for i in range(self.num_hashes)]

    def add(self, item):
        for pos in self._positions(item):
            self.bit_array[pos // 8] |= 1 << (pos % 8)

    def __contains__(self, item):
        return all(self.bit_array[pos // 8] & (1 << (pos % 8)) for pos in self._positions(item))

    def memory_kb(self):
        return len(self.bit_array) / 1024


# ---------------------------------------------------------------------------
#  Use Case 1: Web Crawler URL Deduplication
# ---------------------------------------------------------------------------

def demo_url_dedup():
    print("=== URL Deduplication for Web Crawler ===\n")
    total_urls, dup_rate = 200_000, 0.40
    unique_urls = [f"https://example.com/page/{i}?ref={i%100}" for i in range(total_urls)]
    num_unique = int(total_urls * (1 - dup_rate))
    crawl_stream = unique_urls[:num_unique]
    crawl_stream.extend([unique_urls[random.randint(0, num_unique - 1)] for _ in range(total_urls - num_unique)])
    random.shuffle(crawl_stream)

    exact_seen = set()
    for url in crawl_stream:
        exact_seen.add(url)

    bf = BloomFilter(expected_items=num_unique, fp_rate=0.01)
    bf_crawled, bf_false_skips, seen = 0, 0, set()
    for url in crawl_stream:
        if url in bf:
            if url not in seen:
                bf_false_skips += 1
        else:
            bf.add(url)
            seen.add(url)
            bf_crawled += 1

    set_mem = sys.getsizeof(exact_seen)
    print(f"Stream: {total_urls:,} URLs ({dup_rate:.0%} duplicates), {num_unique:,} unique\n")
    print(f"{'Metric':<28} {'Exact Set':>12} {'Bloom':>12}")
    print("-" * 54)
    print(f"{'URLs crawled':<28} {len(exact_seen):>12,} {bf_crawled:>12,}")
    print(f"{'False skips (missed URLs)':<28} {'0':>12} {bf_false_skips:>12,}")
    print(f"{'Memory':<28} {set_mem/1024:>10.1f} KB {bf.memory_kb():>10.1f} KB")
    print(f"{'Memory savings':<28} {'':>12} {set_mem/(bf.memory_kb()*1024):>11.0f}x")


# ---------------------------------------------------------------------------
#  Use Case 2: Cache Miss Prevention
# ---------------------------------------------------------------------------

def demo_cache_filter():
    print("\n\n=== Cache Miss Prevention (Database Shield) ===\n")
    db_keys = {f"product:{i}" for i in range(50_000)}
    bf = BloomFilter(expected_items=len(db_keys), fp_rate=0.01)
    for key in db_keys:
        bf.add(key)

    random.seed(42)
    queries = [f"product:{random.randint(50_000, 200_000)}" if random.random() < 0.70
               else f"product:{random.randint(0, 49_999)}" for _ in range(100_000)]

    db_no_bloom, cache = 0, {}
    for key in queries:
        if key not in cache:
            db_no_bloom += 1
            if key in db_keys: cache[key] = True
    cache.clear()

    db_bloom, bloom_saved, fp_reads = 0, 0, 0
    for key in queries:
        if key not in cache:
            if key not in bf:
                bloom_saved += 1
            else:
                db_bloom += 1
                if key in db_keys: cache[key] = True
                else: fp_reads += 1

    print(f"Database: {len(db_keys):,} keys | Queries: {len(queries):,} (70% non-existent)\n")
    print(f"{'Metric':<32} {'No Bloom':>10} {'With Bloom':>10}")
    print("-" * 55)
    print(f"{'Database reads':<32} {db_no_bloom:>10,} {db_bloom:>10,}")
    print(f"{'Bloom rejections (saved)':<32} {'n/a':>10} {bloom_saved:>10,}")
    print(f"{'False positive reads (wasted)':<32} {'n/a':>10} {fp_reads:>10,}")
    print(f"{'DB load reduction':<32} {'':>10} {(1-db_bloom/db_no_bloom)*100:>9.1f}%")


# ---------------------------------------------------------------------------
#  Use Case 3: CDN One-Hit-Wonder Filter
# ---------------------------------------------------------------------------

def demo_one_hit_wonder():
    print("\n\n=== One-Hit-Wonder Filter (CDN Optimization) ===\n")
    random.seed(123)
    pop = {}
    for i in range(100_000):
        r = random.random()
        pop[f"obj-{i}"] = 1 if r < 0.75 else (random.randint(2, 5) if r < 0.90 else random.randint(10, 100))

    stream = [obj for obj, c in pop.items() for _ in range(c)]
    random.shuffle(stream)
    one_hit = sum(1 for c in pop.values() if c == 1)

    naive = set()
    for obj in stream: naive.add(obj)

    bf = BloomFilter(expected_items=len(pop), fp_rate=0.01)
    smart = set()
    for obj in stream:
        if obj in bf: smart.add(obj)
        else: bf.add(obj)

    print(f"Objects: {len(pop):,} ({one_hit:,} one-hit wonders) | Requests: {len(stream):,}\n")
    print(f"{'Metric':<28} {'Naive':>10} {'Bloom-Gated':>12}")
    print("-" * 53)
    print(f"{'Objects cached':<28} {len(naive):>10,} {len(smart):>12,}")
    print(f"{'Cache size reduction':<28} {'':>10} {(1-len(smart)/len(naive))*100:>11.1f}%")
    print(f"{'Bloom overhead':<28} {'':>10} {bf.memory_kb():>10.1f} KB")
    print(f"\n~{one_hit:,} one-hit wonders filtered out, saving cache space for objects that matter.")


if __name__ == "__main__":
    print("Practical Bloom Filter Applications\n")
    demo_url_dedup()
    demo_cache_filter()
    demo_one_hit_wonder()
