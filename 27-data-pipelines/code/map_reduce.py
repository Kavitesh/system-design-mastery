"""
MapReduce Word Count
====================
Demonstrates the three phases of MapReduce: map, shuffle, and reduce.
Splits input text across multiple mappers to show parallelism.
"""

# ---------------------------------------------------------------------------
#   Map phase - each mapper processes one chunk independently
# ---------------------------------------------------------------------------

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import time


def mapper(chunk_id, text):
    """Emit (word, 1) for every word in the chunk."""
    pairs = []
    for word in text.lower().split():
        cleaned = "".join(c for c in word if c.isalnum())
        if cleaned:
            pairs.append((cleaned, 1))
    print(f"  Mapper {chunk_id}: emitted {len(pairs)} pairs")
    return pairs


# ---------------------------------------------------------------------------
#   Shuffle phase - group all values by key
# ---------------------------------------------------------------------------

def shuffle(mapped_results):
    """Group values by key across all mapper outputs."""
    groups = defaultdict(list)
    total_pairs = 0
    for pairs in mapped_results:
        for key, value in pairs:
            groups[key].append(value)
            total_pairs += 1
    print(f"  Shuffle: grouped {total_pairs} pairs into {len(groups)} keys")
    return dict(groups)


# ---------------------------------------------------------------------------
#   Reduce phase - aggregate values for each key
# ---------------------------------------------------------------------------

def reducer(key, values):
    """Sum all values for a single key."""
    return key, sum(values)


# ---------------------------------------------------------------------------
#   MapReduce coordinator
# ---------------------------------------------------------------------------

def map_reduce(text, num_mappers=3):
    """Run a full MapReduce word count job."""
    words = text.split()
    chunk_size = max(1, len(words) // num_mappers)
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunks.append(" ".join(words[i:i + chunk_size]))

    print(f"\n{'='*60}")
    print(f"MapReduce Job - {len(words)} words, {len(chunks)} mappers")
    print(f"{'='*60}")

    # MAP
    print(f"\n[Phase 1] MAP")
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=len(chunks)) as pool:
        futures = [pool.submit(mapper, i, chunk) for i, chunk in enumerate(chunks)]
        mapped = [f.result() for f in futures]
    map_time = time.perf_counter() - start
    print(f"  Map completed in {map_time:.4f}s")

    # SHUFFLE
    print(f"\n[Phase 2] SHUFFLE")
    start = time.perf_counter()
    grouped = shuffle(mapped)
    shuffle_time = time.perf_counter() - start
    print(f"  Shuffle completed in {shuffle_time:.4f}s")

    # REDUCE
    print(f"\n[Phase 3] REDUCE")
    start = time.perf_counter()
    results = {}
    for key, values in grouped.items():
        word, count = reducer(key, values)
        results[word] = count
    reduce_time = time.perf_counter() - start
    print(f"  Reduced {len(grouped)} keys in {reduce_time:.4f}s")

    return results


# ---------------------------------------------------------------------------
#   Demo
# ---------------------------------------------------------------------------

def main():
    print("MapReduce Word Count Demo")

    sample_text = """
    The quick brown fox jumps over the lazy dog.
    The dog barked at the fox. The fox ran away.
    A quick brown dog chased the quick fox through the park.
    The lazy fox slept under the old brown tree.
    The dog and the fox became friends in the end.
    """

    results = map_reduce(sample_text, num_mappers=3)

    sorted_results = sorted(results.items(), key=lambda x: -x[1])

    print(f"\n{'='*60}")
    print(f"{'WORD':<20} {'COUNT':>5}")
    print(f"{'-'*20} {'-'*5}")
    for word, count in sorted_results:
        bar = "#" * count
        print(f"  {word:<18} {count:>5}  {bar}")

    print(f"\nTotal unique words: {len(results)}")
    print(f"Total word count:   {sum(results.values())}")

    # Second run - larger text to show scaling
    print("\n\n--- Scaling test: 10x more data ---")
    big_text = (sample_text + " ") * 10
    results2 = map_reduce(big_text, num_mappers=5)
    print(f"\nProcessed {sum(results2.values())} total words, "
          f"{len(results2)} unique")


if __name__ == "__main__":
    main()
