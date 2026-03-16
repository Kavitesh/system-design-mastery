"""
Structured Logging System
==========================
Demonstrates structured JSON logging with correlation IDs, log levels,
and the difference between structured and unstructured approaches.

Run: python structured_logging.py
"""

import json
import uuid
import time
import random
from datetime import datetime, timezone
from enum import IntEnum

# ---------------------------------------------------------------------------
# Log levels
# ---------------------------------------------------------------------------

class LogLevel(IntEnum):
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


LEVEL_NAMES = {v: v.name for v in LogLevel}
LEVEL_COLORS = {
    LogLevel.DEBUG: "\033[90m",
    LogLevel.INFO: "\033[32m",
    LogLevel.WARNING: "\033[33m",
    LogLevel.ERROR: "\033[31m",
    LogLevel.CRITICAL: "\033[91m\033[1m",
}
RESET = "\033[0m"

# ---------------------------------------------------------------------------
# Structured logger
# ---------------------------------------------------------------------------

class StructuredLogger:
    def __init__(self, service_name, min_level=LogLevel.DEBUG):
        self.service_name = service_name
        self.min_level = min_level
        self.logs = []

    def _emit(self, level, message, **fields):
        if level < self.min_level:
            return None

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": LEVEL_NAMES[level],
            "service": self.service_name,
            "message": message,
            **fields
        }
        self.logs.append(entry)

        color = LEVEL_COLORS.get(level, "")
        compact = json.dumps(entry, default=str)
        print(f"{color}{compact}{RESET}")
        return entry

    def debug(self, message, **fields):
        return self._emit(LogLevel.DEBUG, message, **fields)

    def info(self, message, **fields):
        return self._emit(LogLevel.INFO, message, **fields)

    def warning(self, message, **fields):
        return self._emit(LogLevel.WARNING, message, **fields)

    def error(self, message, **fields):
        return self._emit(LogLevel.ERROR, message, **fields)

    def critical(self, message, **fields):
        return self._emit(LogLevel.CRITICAL, message, **fields)

    def with_correlation(self, correlation_id):
        return CorrelatedLogger(self, correlation_id)


class CorrelatedLogger:
    """Logger that automatically attaches a correlation ID to every entry."""

    def __init__(self, parent, correlation_id):
        self._parent = parent
        self._correlation_id = correlation_id

    def debug(self, msg, **f):
        return self._parent.debug(msg, correlation_id=self._correlation_id, **f)

    def info(self, msg, **f):
        return self._parent.info(msg, correlation_id=self._correlation_id, **f)

    def warning(self, msg, **f):
        return self._parent.warning(msg, correlation_id=self._correlation_id, **f)

    def error(self, msg, **f):
        return self._parent.error(msg, correlation_id=self._correlation_id, **f)

    def critical(self, msg, **f):
        return self._parent.critical(msg, correlation_id=self._correlation_id, **f)


# ---------------------------------------------------------------------------
# Simulate a request lifecycle with correlated logs
# ---------------------------------------------------------------------------

def simulate_request(logger, request_id):
    correlation_id = str(uuid.uuid4())[:8]
    log = logger.with_correlation(correlation_id)

    user_id = random.randint(1000, 9999)
    endpoint = random.choice(["/api/orders", "/api/users", "/api/checkout", "/api/search"])
    method = "GET" if "search" in endpoint or "users" in endpoint else "POST"

    log.info("Request received", method=method, path=endpoint, user_id=user_id)

    latency_ms = random.expovariate(1 / 50)

    if endpoint == "/api/checkout":
        log.info("Processing payment", user_id=user_id, amount=round(random.uniform(10, 500), 2))

        if random.random() < 0.15:
            log.error("Payment declined", user_id=user_id, reason="insufficient_funds",
                       provider="stripe", latency_ms=round(latency_ms, 1))
            return "error"

    if random.random() < 0.05:
        log.warning("Upstream timeout, retrying", endpoint=endpoint,
                     attempt=1, max_retries=3)
        latency_ms += random.uniform(100, 300)

        if random.random() < 0.3:
            log.error("Upstream failed after retries", endpoint=endpoint,
                       attempts=3, latency_ms=round(latency_ms, 1))
            return "error"
        log.info("Retry succeeded", endpoint=endpoint, attempt=2)

    status = 200 if random.random() > 0.02 else 500
    log.info("Request completed", method=method, path=endpoint,
             status=status, latency_ms=round(latency_ms, 1), user_id=user_id)

    return "ok" if status == 200 else "error"


# ---------------------------------------------------------------------------
# Demo: unstructured vs structured comparison
# ---------------------------------------------------------------------------

def show_unstructured_vs_structured():
    print("=" * 70)
    print("UNSTRUCTURED LOGGING (the old way)")
    print("=" * 70)
    print()
    print("2024-03-15 10:23:45 INFO Starting payment for user 4521")
    print("2024-03-15 10:23:45 ERROR Payment failed for user 4521 - card declined")
    print("2024-03-15 10:23:46 INFO Retrying payment for user 4521 attempt 2")
    print()
    print("  Problems: Can't filter by user_id. Can't aggregate error types.")
    print("  Searching requires regex. No correlation across services.")
    print()

    print("=" * 70)
    print("STRUCTURED LOGGING (the right way)")
    print("=" * 70)
    print()


# ---------------------------------------------------------------------------
# Run the demo
# ---------------------------------------------------------------------------

def main():
    print("Structured Logging - JSON output with correlation IDs")
    print("=" * 70)
    print()

    show_unstructured_vs_structured()

    logger = StructuredLogger("order-service")

    results = {"ok": 0, "error": 0}
    for i in range(12):
        result = simulate_request(logger, i)
        results[result] += 1

    print(f"\n{'=' * 70}")
    print("LOG ANALYSIS")
    print(f"{'=' * 70}")
    print(f"  Total log entries: {len(logger.logs)}")

    level_counts = {}
    for entry in logger.logs:
        level_counts[entry["level"]] = level_counts.get(entry["level"], 0) + 1

    print(f"  By level:")
    for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        count = level_counts.get(level, 0)
        if count:
            print(f"    {level:<10} {count:>3}  {'|' * count}")

    print(f"\n  Requests: {results['ok']} succeeded, {results['error']} failed")

    correlation_ids = set()
    for entry in logger.logs:
        if "correlation_id" in entry:
            correlation_ids.add(entry["correlation_id"])

    print(f"  Unique correlation IDs: {len(correlation_ids)}")
    print(f"\n  Filter example - all ERROR entries:")
    for entry in logger.logs:
        if entry["level"] == "ERROR":
            print(f"    [{entry['correlation_id']}] {entry['message']}")


if __name__ == "__main__":
    main()
