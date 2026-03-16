"""
Concurrency Test
================
Spawns multiple threads attempting to book the same seats simultaneously.
Demonstrates how locking prevents double-booking even under heavy
contention.

Uses an in-memory booking engine (no Flask server required).

Usage:
  python concurrency_test.py
"""

import threading
import time
import random
from collections import defaultdict

# ---------------------------------------------------------------------------
# Booking engine with configurable locking strategy
# ---------------------------------------------------------------------------

class BookingEngine:
    def __init__(self, seats: list[str], strategy: str = "locked"):
        self.seats = {s: {"status": "available", "owner": None, "version": 0} for s in seats}
        self.strategy = strategy
        self._lock = threading.Lock()
        self._seat_locks = {s: threading.Lock() for s in seats}
        self.results = []

    def attempt_book(self, seat_id: str, user_id: str) -> dict:
        if self.strategy == "no_lock":
            return self._book_no_lock(seat_id, user_id)
        elif self.strategy == "global_lock":
            return self._book_global_lock(seat_id, user_id)
        elif self.strategy == "optimistic":
            return self._book_optimistic(seat_id, user_id)
        elif self.strategy == "per_seat_lock":
            return self._book_per_seat_lock(seat_id, user_id)

    def _book_no_lock(self, seat_id: str, user_id: str) -> dict:
        """Deliberately unsafe - no locking. Will produce double bookings."""
        seat = self.seats[seat_id]
        if seat["status"] == "available":
            # Simulate network/processing delay that widens the race window
            time.sleep(random.uniform(0.001, 0.005))
            seat["status"] = "booked"
            seat["owner"] = user_id
            result = {"user": user_id, "seat": seat_id, "result": "booked"}
        else:
            result = {"user": user_id, "seat": seat_id, "result": "denied"}
        self.results.append(result)
        return result

    def _book_global_lock(self, seat_id: str, user_id: str) -> dict:
        """Safe but slow - one global lock serializes all bookings."""
        with self._lock:
            seat = self.seats[seat_id]
            if seat["status"] == "available":
                time.sleep(random.uniform(0.001, 0.003))
                seat["status"] = "booked"
                seat["owner"] = user_id
                result = {"user": user_id, "seat": seat_id, "result": "booked"}
            else:
                result = {"user": user_id, "seat": seat_id, "result": "denied"}
        self.results.append(result)
        return result

    def _book_optimistic(self, seat_id: str, user_id: str) -> dict:
        """Optimistic locking - read version, write only if version matches."""
        max_retries = 3
        for attempt in range(max_retries):
            seat = self.seats[seat_id]
            if seat["status"] != "available":
                result = {"user": user_id, "seat": seat_id, "result": "denied"}
                self.results.append(result)
                return result

            read_version = seat["version"]
            time.sleep(random.uniform(0.001, 0.003))

            with self._lock:
                if seat["version"] == read_version and seat["status"] == "available":
                    seat["status"] = "booked"
                    seat["owner"] = user_id
                    seat["version"] += 1
                    result = {"user": user_id, "seat": seat_id, "result": "booked"}
                    self.results.append(result)
                    return result
                # Version changed - retry

        result = {"user": user_id, "seat": seat_id, "result": "denied (retries exhausted)"}
        self.results.append(result)
        return result

    def _book_per_seat_lock(self, seat_id: str, user_id: str) -> dict:
        """Pessimistic per-seat locking - best balance of safety and throughput."""
        with self._seat_locks[seat_id]:
            seat = self.seats[seat_id]
            if seat["status"] == "available":
                time.sleep(random.uniform(0.001, 0.003))
                seat["status"] = "booked"
                seat["owner"] = user_id
                result = {"user": user_id, "seat": seat_id, "result": "booked"}
            else:
                result = {"user": user_id, "seat": seat_id, "result": "denied"}
        self.results.append(result)
        return result


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

def run_contention_test(strategy: str, num_users: int, seats: list[str]):
    engine = BookingEngine(seats, strategy=strategy)
    threads = []

    for i in range(num_users):
        seat = random.choice(seats)
        t = threading.Thread(target=engine.attempt_book, args=(seat, f"user-{i}"))
        threads.append(t)

    start = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.time() - start

    booked = [r for r in engine.results if r["result"] == "booked"]
    denied = [r for r in engine.results if "denied" in r["result"]]

    # Check for double bookings
    owners_per_seat = defaultdict(list)
    for seat_id, seat_data in engine.seats.items():
        if seat_data["owner"]:
            owners_per_seat[seat_id].append(seat_data["owner"])

    booked_by_result = defaultdict(list)
    for r in booked:
        booked_by_result[r["seat"]].append(r["user"])

    double_booked = {s: users for s, users in booked_by_result.items() if len(users) > 1}

    return {
        "strategy": strategy,
        "users": num_users,
        "seats_available": len(seats),
        "booked": len(booked),
        "denied": len(denied),
        "double_bookings": len(double_booked),
        "double_booking_details": double_booked,
        "elapsed_ms": round(elapsed * 1000, 1),
    }


def main():
    print("=" * 65)
    print("CONCURRENCY TEST - Double Booking Prevention")
    print("=" * 65)

    seats = ["A1", "A2", "A3", "A4", "A5"]
    num_users = 50

    strategies = [
        ("no_lock",       "No Locking (unsafe)"),
        ("global_lock",   "Global Lock (safe, slow)"),
        ("optimistic",    "Optimistic Locking (safe, fast)"),
        ("per_seat_lock", "Per-Seat Lock (safe, fastest)"),
    ]

    print(f"\nScenario: {num_users} users fighting for {len(seats)} seats\n")
    print(f"{'Strategy':<30} {'Booked':<8} {'Denied':<8} {'Double':<8} {'Time':<10}")
    print("-" * 65)

    details = []
    for strategy_key, strategy_name in strategies:
        result = run_contention_test(strategy_key, num_users, seats.copy())
        marker = " !!!" if result["double_bookings"] > 0 else ""
        print(f"{strategy_name:<30} {result['booked']:<8} {result['denied']:<8} "
              f"{result['double_bookings']:<8} {result['elapsed_ms']:<10}{marker}")
        details.append(result)

    # Show double-booking details for the unsafe strategy
    print("\n--- Double Booking Analysis ---")
    for result in details:
        if result["double_bookings"] > 0:
            print(f"\n  [{result['strategy']}] FOUND {result['double_bookings']} double-booked seat(s):")
            for seat, users in result["double_booking_details"].items():
                print(f"    Seat {seat} sold to: {', '.join(users)}")
        else:
            print(f"  [{result['strategy']}] No double bookings - correct!")

    print("\n--- Key Takeaways ---")
    print("  1. No locking produces double bookings under contention")
    print("  2. Global lock is safe but serializes ALL bookings (bottleneck)")
    print("  3. Optimistic locking retries on conflict - good for moderate contention")
    print("  4. Per-seat locking gives maximum parallelism with full safety")


if __name__ == "__main__":
    main()
