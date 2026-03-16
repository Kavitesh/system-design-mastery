"""
Cold Start Benchmark
=====================
Measures and visualizes the performance impact of cold starts vs warm starts
across simulated runtimes. Prints ASCII charts comparing latency distributions.

Usage:
    python cold_start_benchmark.py
"""

import time
import random
import statistics

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

NUM_INVOCATIONS = 50
CONTAINER_RECYCLE_PROBABILITY = 0.15

RUNTIME_PROFILES = {
    "Python 3.11": {"cold_min": 150, "cold_max": 450, "warm_min": 1, "warm_max": 8},
    "Node.js 18":  {"cold_min": 120, "cold_max": 380, "warm_min": 1, "warm_max": 6},
    "Go 1.21":     {"cold_min": 40,  "cold_max": 160, "warm_min": 0.5, "warm_max": 3},
    "Java 17":     {"cold_min": 600, "cold_max": 3500, "warm_min": 2, "warm_max": 12},
    ".NET 8":      {"cold_min": 250, "cold_max": 1800, "warm_min": 1, "warm_max": 10},
}

# ---------------------------------------------------------------------------
# Benchmark Engine
# ---------------------------------------------------------------------------

def simulate_invocations(profile, n=NUM_INVOCATIONS, recycle_prob=CONTAINER_RECYCLE_PROBABILITY):
    results = []
    container_warm = False

    for i in range(n):
        if not container_warm or random.random() < recycle_prob:
            latency = random.uniform(profile["cold_min"], profile["cold_max"])
            latency += random.uniform(profile["warm_min"], profile["warm_max"])
            results.append({"latency_ms": latency, "type": "cold"})
            container_warm = True
        else:
            latency = random.uniform(profile["warm_min"], profile["warm_max"])
            results.append({"latency_ms": latency, "type": "warm"})

    return results


def compute_stats(results):
    all_latencies = [r["latency_ms"] for r in results]
    cold_latencies = [r["latency_ms"] for r in results if r["type"] == "cold"]
    warm_latencies = [r["latency_ms"] for r in results if r["type"] == "warm"]

    sorted_all = sorted(all_latencies)
    p50_idx = int(len(sorted_all) * 0.50)
    p95_idx = int(len(sorted_all) * 0.95)
    p99_idx = min(int(len(sorted_all) * 0.99), len(sorted_all) - 1)

    return {
        "total": len(results),
        "cold_count": len(cold_latencies),
        "warm_count": len(warm_latencies),
        "cold_pct": 100 * len(cold_latencies) / len(results),
        "avg_all": statistics.mean(all_latencies),
        "avg_cold": statistics.mean(cold_latencies) if cold_latencies else 0,
        "avg_warm": statistics.mean(warm_latencies) if warm_latencies else 0,
        "p50": sorted_all[p50_idx],
        "p95": sorted_all[p95_idx],
        "p99": sorted_all[p99_idx],
        "min": min(all_latencies),
        "max": max(all_latencies),
    }


# ---------------------------------------------------------------------------
# ASCII Visualization
# ---------------------------------------------------------------------------

def draw_bar(label, value, max_value, width=40, unit="ms"):
    bar_len = int((value / max_value) * width) if max_value > 0 else 0
    bar = "#" * bar_len + "." * (width - bar_len)
    return f"  {label:<14} [{bar}] {value:>8.1f} {unit}"


def draw_histogram(latencies, title, bucket_count=12):
    if not latencies:
        return

    min_val = min(latencies)
    max_val = max(latencies)
    bucket_size = (max_val - min_val) / bucket_count if max_val > min_val else 1

    buckets = [0] * bucket_count
    for v in latencies:
        idx = min(int((v - min_val) / bucket_size), bucket_count - 1)
        buckets[idx] += 1

    max_count = max(buckets)
    print(f"\n  {title}")
    print(f"  {'='*55}")

    for i, count in enumerate(buckets):
        lo = min_val + i * bucket_size
        hi = lo + bucket_size
        bar_len = int((count / max_count) * 35) if max_count > 0 else 0
        bar = "#" * bar_len
        print(f"  {lo:>7.0f}-{hi:>6.0f}ms | {bar:<35} ({count})")


# ---------------------------------------------------------------------------
# Main Benchmark
# ---------------------------------------------------------------------------

def main():
    print("Cold Start Benchmark - FaaS Latency Analysis")
    print(f"  Invocations per runtime: {NUM_INVOCATIONS}")
    print(f"  Container recycle probability: {CONTAINER_RECYCLE_PROBABILITY*100:.0f}%\n")

    all_stats = {}
    all_results = {}

    for runtime, profile in RUNTIME_PROFILES.items():
        results = simulate_invocations(profile)
        stats = compute_stats(results)
        all_stats[runtime] = stats
        all_results[runtime] = results

    # --- Comparison table ---
    print(f"{'='*90}")
    print(f"  {'Runtime':<14} {'Avg(all)':>10} {'Avg(cold)':>10} {'Avg(warm)':>10} "
          f"{'p50':>8} {'p95':>8} {'p99':>8} {'Cold%':>6}")
    print(f"  {'-'*84}")

    for runtime, s in all_stats.items():
        print(f"  {runtime:<14} {s['avg_all']:>9.1f}ms {s['avg_cold']:>9.1f}ms "
              f"{s['avg_warm']:>9.1f}ms {s['p50']:>7.1f} {s['p95']:>7.1f} "
              f"{s['p99']:>7.1f} {s['cold_pct']:>5.1f}%")
    print(f"{'='*90}")

    # --- Average cold start comparison ---
    max_cold = max(s["avg_cold"] for s in all_stats.values())
    print(f"\n  Average Cold Start Latency")
    print(f"  {'='*65}")
    for runtime, s in all_stats.items():
        print(draw_bar(runtime, s["avg_cold"], max_cold))

    # --- Average warm start comparison ---
    max_warm = max(s["avg_warm"] for s in all_stats.values())
    print(f"\n  Average Warm Start Latency")
    print(f"  {'='*65}")
    for runtime, s in all_stats.items():
        print(draw_bar(runtime, s["avg_warm"], max_warm))

    # --- p99 latency comparison ---
    max_p99 = max(s["p99"] for s in all_stats.values())
    print(f"\n  p99 Latency (tail latency - what your worst users experience)")
    print(f"  {'='*65}")
    for runtime, s in all_stats.items():
        print(draw_bar(runtime, s["p99"], max_p99))

    # --- Cold vs warm multiplier ---
    print(f"\n  Cold Start Penalty (cold / warm ratio)")
    print(f"  {'='*55}")
    for runtime, s in all_stats.items():
        ratio = s["avg_cold"] / s["avg_warm"] if s["avg_warm"] > 0 else 0
        bar_len = min(40, int(ratio / 2))
        bar = "#" * bar_len
        print(f"  {runtime:<14} [{bar:<40}] {ratio:>6.0f}x")

    # --- Histogram for worst offender ---
    worst = max(all_stats.items(), key=lambda x: x[1]["avg_cold"])
    best = min(all_stats.items(), key=lambda x: x[1]["avg_cold"])

    cold_latencies = [r["latency_ms"] for r in all_results[worst[0]] if r["type"] == "cold"]
    draw_histogram(cold_latencies, f"Cold Start Distribution - {worst[0]} (slowest)")

    cold_latencies = [r["latency_ms"] for r in all_results[best[0]] if r["type"] == "cold"]
    draw_histogram(cold_latencies, f"Cold Start Distribution - {best[0]} (fastest)")

    # --- Takeaways ---
    print(f"\n  Key Takeaways")
    print(f"  {'='*55}")
    print(f"  1. Go has the fastest cold starts ({all_stats['Go 1.21']['avg_cold']:.0f}ms avg)")
    print(f"  2. Java's cold starts are brutal ({all_stats['Java 17']['avg_cold']:.0f}ms avg)")
    print(f"  3. Warm starts are fast everywhere (<15ms)")
    print(f"  4. p99 includes cold starts - this is what SLA reviews catch")
    print(f"  5. At {CONTAINER_RECYCLE_PROBABILITY*100:.0f}% recycle rate, "
          f"cold starts dominate tail latency")
    print()


if __name__ == "__main__":
    main()
