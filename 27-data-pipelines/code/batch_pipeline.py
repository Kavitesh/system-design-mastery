"""
Multi-Stage Batch ETL Pipeline
===============================
Simulates a realistic batch pipeline that extracts user transaction data,
transforms it, validates data quality, and loads results to a destination.
"""

import json
import random
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
#   Data generation - simulates a source database
# ---------------------------------------------------------------------------

PRODUCTS = ["Widget A", "Widget B", "Gadget X", "Gadget Y", "Thingamajig"]
REGIONS = ["us-east", "us-west", "eu-west", "ap-south"]

def generate_transactions(n=200):
    """Generate fake transaction records with intentional quality issues."""
    records = []
    base_date = datetime(2025, 3, 1)
    for i in range(n):
        record = {
            "txn_id": f"TXN-{i:05d}",
            "user_id": f"U{random.randint(1, 50):04d}",
            "product": random.choice(PRODUCTS),
            "amount": round(random.uniform(5.0, 500.0), 2),
            "region": random.choice(REGIONS),
            "timestamp": (base_date + timedelta(
                hours=random.randint(0, 720)
            )).isoformat(),
        }
        # Inject data quality issues (10% of records)
        if random.random() < 0.04:
            record["amount"] = -abs(record["amount"])  # negative amount
        if random.random() < 0.03:
            record["user_id"] = None  # null user
        if random.random() < 0.03:
            record["amount"] = 99999.99  # suspicious outlier

        records.append(record)
    return records


# ---------------------------------------------------------------------------
#   Pipeline stages
# ---------------------------------------------------------------------------

@dataclass
class PipelineMetrics:
    stage: str
    input_count: int = 0
    output_count: int = 0
    dropped_count: int = 0
    duration_ms: float = 0
    errors: list = field(default_factory=list)


def extract(source_records):
    """Extract stage - pull records from source and do basic parsing."""
    start = time.perf_counter()
    extracted = []
    errors = []
    for record in source_records:
        try:
            serialized = json.dumps(record)
            parsed = json.loads(serialized)
            extracted.append(parsed)
        except (json.JSONDecodeError, TypeError) as e:
            errors.append(f"Parse error on {record.get('txn_id', '?')}: {e}")

    metrics = PipelineMetrics(
        stage="EXTRACT",
        input_count=len(source_records),
        output_count=len(extracted),
        dropped_count=len(errors),
        duration_ms=(time.perf_counter() - start) * 1000,
        errors=errors,
    )
    return extracted, metrics


def transform(records):
    """Transform stage - clean, enrich, and reshape records."""
    start = time.perf_counter()
    transformed = []
    dropped = []

    for r in records:
        # Drop records with null user_id
        if r.get("user_id") is None:
            dropped.append((r["txn_id"], "null user_id"))
            continue

        # Drop negative amounts
        if r["amount"] < 0:
            dropped.append((r["txn_id"], f"negative amount: {r['amount']}"))
            continue

        # Enrich with derived fields
        ts = datetime.fromisoformat(r["timestamp"])
        r["day_of_week"] = ts.strftime("%A")
        r["hour"] = ts.hour
        r["amount_bucket"] = (
            "small" if r["amount"] < 50
            else "medium" if r["amount"] < 200
            else "large"
        )
        r["is_outlier"] = r["amount"] > 5000

        transformed.append(r)

    metrics = PipelineMetrics(
        stage="TRANSFORM",
        input_count=len(records),
        output_count=len(transformed),
        dropped_count=len(dropped),
        duration_ms=(time.perf_counter() - start) * 1000,
        errors=[f"{txn}: {reason}" for txn, reason in dropped],
    )
    return transformed, metrics


def validate(records, rules=None):
    """Validation gate - check data quality before loading."""
    start = time.perf_counter()
    rules = rules or {}
    min_records = rules.get("min_records", 10)
    max_null_rate = rules.get("max_null_rate", 0.05)
    max_outlier_rate = rules.get("max_outlier_rate", 0.10)

    issues = []

    if len(records) < min_records:
        issues.append(f"FAIL: only {len(records)} records (minimum: {min_records})")

    null_count = sum(1 for r in records if any(v is None for v in r.values()))
    null_rate = null_count / max(len(records), 1)
    if null_rate > max_null_rate:
        issues.append(f"FAIL: null rate {null_rate:.1%} exceeds {max_null_rate:.1%}")

    outlier_count = sum(1 for r in records if r.get("is_outlier", False))
    outlier_rate = outlier_count / max(len(records), 1)
    if outlier_rate > max_outlier_rate:
        issues.append(
            f"WARN: outlier rate {outlier_rate:.1%} exceeds {max_outlier_rate:.1%}"
        )

    passed = not any("FAIL" in i for i in issues)

    metrics = PipelineMetrics(
        stage="VALIDATE",
        input_count=len(records),
        output_count=len(records) if passed else 0,
        dropped_count=0 if passed else len(records),
        duration_ms=(time.perf_counter() - start) * 1000,
        errors=issues,
    )
    return passed, metrics


def load(records):
    """Load stage - write results to destination (simulated)."""
    start = time.perf_counter()

    # Aggregate by region and product
    summary = {}
    for r in records:
        key = (r["region"], r["product"])
        if key not in summary:
            summary[key] = {"count": 0, "total_amount": 0.0}
        summary[key]["count"] += 1
        summary[key]["total_amount"] += r["amount"]

    time.sleep(0.05)  # simulate write latency

    metrics = PipelineMetrics(
        stage="LOAD",
        input_count=len(records),
        output_count=len(records),
        duration_ms=(time.perf_counter() - start) * 1000,
    )
    return summary, metrics


# ---------------------------------------------------------------------------
#   Pipeline runner
# ---------------------------------------------------------------------------

def print_metrics(metrics):
    status = "OK" if metrics.dropped_count == 0 and not metrics.errors else "ISSUES"
    print(f"  [{metrics.stage}] {metrics.input_count} in -> "
          f"{metrics.output_count} out | "
          f"dropped: {metrics.dropped_count} | "
          f"{metrics.duration_ms:.1f}ms | {status}")
    for err in metrics.errors[:5]:
        print(f"    - {err}")
    if len(metrics.errors) > 5:
        print(f"    ... and {len(metrics.errors) - 5} more")


def run_pipeline():
    print("Batch ETL Pipeline Demo")
    print(f"\n{'='*60}")
    print("Pipeline: Extract -> Transform -> Validate -> Load")
    print(f"{'='*60}")

    random.seed(42)
    raw_data = generate_transactions(200)
    print(f"\nGenerated {len(raw_data)} source records")

    all_metrics = []

    # Stage 1: Extract
    print(f"\n--- Stage 1: Extract ---")
    extracted, m = extract(raw_data)
    print_metrics(m)
    all_metrics.append(m)

    # Stage 2: Transform
    print(f"\n--- Stage 2: Transform ---")
    transformed, m = transform(extracted)
    print_metrics(m)
    all_metrics.append(m)

    # Stage 3: Validate
    print(f"\n--- Stage 3: Validate ---")
    passed, m = validate(transformed)
    print_metrics(m)
    all_metrics.append(m)

    if not passed:
        print(f"\n  PIPELINE HALTED - validation failed")
        return

    # Stage 4: Load
    print(f"\n--- Stage 4: Load ---")
    summary, m = load(transformed)
    print_metrics(m)
    all_metrics.append(m)

    # Summary
    print(f"\n{'='*60}")
    print("Pipeline Summary")
    print(f"{'='*60}")
    total_time = sum(m.duration_ms for m in all_metrics)
    total_dropped = sum(m.dropped_count for m in all_metrics)
    print(f"  Total time:      {total_time:.1f}ms")
    print(f"  Records in:      {all_metrics[0].input_count}")
    print(f"  Records loaded:  {all_metrics[-1].output_count}")
    print(f"  Records dropped: {total_dropped}")
    print(f"  Drop rate:       {total_dropped/all_metrics[0].input_count:.1%}")

    print(f"\n{'REGION':<12} {'PRODUCT':<16} {'COUNT':>6} {'TOTAL ($)':>12}")
    print(f"{'-'*12} {'-'*16} {'-'*6} {'-'*12}")
    for (region, product), stats in sorted(summary.items()):
        print(f"  {region:<10} {product:<16} {stats['count']:>6} "
              f"{stats['total_amount']:>12,.2f}")


if __name__ == "__main__":
    run_pipeline()
