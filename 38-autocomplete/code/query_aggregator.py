"""
Query Aggregator
=================
Simulates the data gathering pipeline for autocomplete. Collects raw search
queries, aggregates them by frequency, applies time-weighted decay so recent
queries rank higher than stale ones, and filters low-frequency noise.

Run: python query_aggregator.py
"""

import time
import random
import math
from collections import defaultdict

# ---------------------------------------------------------------------------
# Query log simulator
# ---------------------------------------------------------------------------

QUERY_POOL = [
    "weather", "weather tomorrow", "weather radar", "weather forecast",
    "python tutorial", "python download", "python flask", "python pandas",
    "pizza near me", "pizza recipe", "pizza hut", "pizza delivery",
    "how to tie a tie", "how to lose weight", "how to cook rice",
    "machine learning", "machine learning course",
    "chatgpt", "chatgpt login", "netflix login", "netflix shows",
    "amazon prime", "best laptop 2026", "bitcoin price",
    "javascript tutorial", "java vs python", "react hooks",
]

TRENDING = ["election results 2026", "earthquake today", "super bowl 2026"]
OFFENSIVE = ["bad word query", "spam spam spam"]


def generate_raw_logs(n: int, trending_boost: float = 0.0) -> list[dict]:
    """Simulate n raw search log entries with timestamps."""
    logs = []
    now = time.time()
    for i in range(n):
        ts = now - random.uniform(0, 7 * 86400)

        roll = random.random()
        if roll < 0.02:
            query = random.choice(OFFENSIVE)
        elif roll < 0.02 + trending_boost:
            query = random.choice(TRENDING)
        else:
            weights = [1.0 / (idx + 1) for idx in range(len(QUERY_POOL))]
            query = random.choices(QUERY_POOL, weights=weights, k=1)[0]

        logs.append({"query": query.lower().strip(), "timestamp": ts})
    return logs


# ---------------------------------------------------------------------------
# Aggregation pipeline
# ---------------------------------------------------------------------------

class QueryAggregator:
    """Three-stage pipeline: filter, aggregate, decay."""

    def __init__(self, min_frequency: int = 3, decay_rate: float = 0.9,
                 decay_period_days: float = 7.0):
        self.min_frequency = min_frequency
        self.decay_rate = decay_rate
        self.decay_period_seconds = decay_period_days * 86400
        self.blocklist = set(OFFENSIVE)

    def filter_logs(self, logs: list[dict]) -> list[dict]:
        """Remove offensive queries and bot-like patterns."""
        filtered = []
        blocked = 0
        for entry in logs:
            if entry["query"] in self.blocklist:
                blocked += 1
                continue
            if len(entry["query"]) < 2 or len(entry["query"]) > 200:
                blocked += 1
                continue
            filtered.append(entry)
        return filtered, blocked

    def aggregate_raw(self, logs: list[dict]) -> dict[str, int]:
        """Simple frequency count without decay."""
        freq = defaultdict(int)
        for entry in logs:
            freq[entry["query"]] += 1
        return dict(freq)

    def aggregate_with_decay(self, logs: list[dict]) -> dict[str, float]:
        """Frequency with exponential time decay. Recent queries score higher."""
        now = max(e["timestamp"] for e in logs) if logs else time.time()
        scores = defaultdict(float)
        for entry in logs:
            age_seconds = now - entry["timestamp"]
            periods_elapsed = age_seconds / self.decay_period_seconds
            weight = self.decay_rate ** periods_elapsed
            scores[entry["query"]] += weight
        return dict(scores)

    def apply_threshold(self, scores: dict[str, float]) -> dict[str, float]:
        """Drop queries below the minimum frequency threshold."""
        return {q: s for q, s in scores.items() if s >= self.min_frequency}

    def run_pipeline(self, logs: list[dict]) -> list[tuple[str, float]]:
        """Full pipeline: filter -> decay-aggregate -> threshold -> sort."""
        filtered, blocked = self.filter_logs(logs)
        scores = self.aggregate_with_decay(filtered)
        above_threshold = self.apply_threshold(scores)
        ranked = sorted(above_threshold.items(), key=lambda x: x[1], reverse=True)
        return ranked, len(filtered), blocked


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def main():
    random.seed(42)

    print("=" * 60)
    print("QUERY AGGREGATION PIPELINE")
    print("=" * 60)

    raw_logs = generate_raw_logs(5000, trending_boost=0.15)
    print(f"\nGenerated {len(raw_logs)} raw log entries (7-day window)")

    agg = QueryAggregator(min_frequency=3, decay_rate=0.9, decay_period_days=7.0)

    print("\n--- Stage 1: Filter ---")
    filtered, blocked = agg.filter_logs(raw_logs)
    print(f"  Kept: {len(filtered)}  |  Blocked: {blocked}")

    print("\n--- Stage 2: Raw frequency (no decay) ---")
    raw_freq = agg.aggregate_raw(filtered)
    top_raw = sorted(raw_freq.items(), key=lambda x: x[1], reverse=True)[:10]
    print(f"  {'Query':<35} {'Raw Count':>10}")
    print(f"  {'-' * 47}")
    for query, count in top_raw:
        print(f"  {query:<35} {count:>10}")

    print("\n--- Stage 3: Time-weighted scores (decay=0.9/week) ---")
    decayed = agg.aggregate_with_decay(filtered)
    top_decayed = sorted(decayed.items(), key=lambda x: x[1], reverse=True)[:10]
    print(f"  {'Query':<35} {'Weighted Score':>14}")
    print(f"  {'-' * 51}")
    for query, score in top_decayed:
        print(f"  {query:<35} {score:>14.1f}")

    print("\n--- Stage 4: After threshold filter (min_freq=3) ---")
    ranked, kept, _ = agg.run_pipeline(raw_logs)
    print(f"  Queries above threshold: {len(ranked)}")
    print(f"\n  {'Rank':<6} {'Query':<35} {'Score':>10}")
    print(f"  {'-' * 53}")
    for i, (query, score) in enumerate(ranked[:15], 1):
        print(f"  {i:<6} {query:<35} {score:>10.1f}")

    print("\n--- Decay effect comparison ---")
    print("  Same query, different ages:")
    now = time.time()
    for days_ago in [0, 1, 3, 7, 14, 30]:
        periods = days_ago / 7.0
        weight = 0.9 ** periods
        print(f"  {days_ago:>3} days ago  ->  weight = {weight:.4f}")


if __name__ == "__main__":
    main()
