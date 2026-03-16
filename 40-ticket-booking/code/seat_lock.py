"""
Seat Lock Engine
================
Demonstrates the temporary seat reservation pattern used by ticket
booking systems. Seats are held with an automatic expiry timer -
simulating Redis SET NX EX without requiring Redis.

Usage:
  python seat_lock.py
"""

import time
import threading
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Seat lock store (simulates Redis key-value with TTL)
# ---------------------------------------------------------------------------

@dataclass
class SeatHold:
    user_id: str
    expires_at: float

class SeatLockEngine:
    def __init__(self, hold_duration: int = 420):
        self.hold_duration = hold_duration
        self._locks: dict[str, SeatHold] = {}
        self._mutex = threading.Lock()
        self._stats = {"acquired": 0, "denied": 0, "expired": 0, "released": 0, "confirmed": 0}

    def _key(self, event_id: str, seat_id: str) -> str:
        return f"{event_id}:{seat_id}"

    def _purge_expired(self):
        now = time.time()
        expired_keys = [k for k, v in self._locks.items() if v.expires_at <= now]
        for k in expired_keys:
            del self._locks[k]
            self._stats["expired"] += 1
        return len(expired_keys)

    def hold(self, event_id: str, seat_id: str, user_id: str) -> dict:
        """Attempt to hold a seat. Returns success/failure with details."""
        key = self._key(event_id, seat_id)

        with self._mutex:
            self._purge_expired()

            if key in self._locks:
                existing = self._locks[key]
                self._stats["denied"] += 1
                return {
                    "success": False,
                    "reason": "already_held",
                    "held_by": existing.user_id,
                    "expires_in": round(existing.expires_at - time.time(), 1),
                }

            # Atomic acquisition - equivalent to SET key value NX EX
            self._locks[key] = SeatHold(
                user_id=user_id,
                expires_at=time.time() + self.hold_duration,
            )
            self._stats["acquired"] += 1

        return {
            "success": True,
            "seat": seat_id,
            "user": user_id,
            "hold_seconds": self.hold_duration,
        }

    def release(self, event_id: str, seat_id: str, user_id: str) -> dict:
        """Release a hold. Only the holder can release."""
        key = self._key(event_id, seat_id)

        with self._mutex:
            if key not in self._locks:
                return {"success": False, "reason": "no_hold_found"}

            if self._locks[key].user_id != user_id:
                return {"success": False, "reason": "not_your_hold"}

            del self._locks[key]
            self._stats["released"] += 1

        return {"success": True, "seat": seat_id, "released_by": user_id}

    def confirm(self, event_id: str, seat_id: str, user_id: str) -> dict:
        """Convert a hold into a confirmed booking. Only the holder can confirm."""
        key = self._key(event_id, seat_id)

        with self._mutex:
            self._purge_expired()

            if key not in self._locks:
                return {"success": False, "reason": "hold_expired_or_missing"}

            hold = self._locks[key]
            if hold.user_id != user_id:
                return {"success": False, "reason": "not_your_hold"}

            del self._locks[key]
            self._stats["confirmed"] += 1

        return {"success": True, "seat": seat_id, "confirmed_by": user_id}

    def status(self, event_id: str, seat_id: str) -> dict:
        key = self._key(event_id, seat_id)
        with self._mutex:
            self._purge_expired()
            if key in self._locks:
                hold = self._locks[key]
                return {"status": "held", "user": hold.user_id,
                        "expires_in": round(hold.expires_at - time.time(), 1)}
            return {"status": "available"}

    def get_stats(self) -> dict:
        with self._mutex:
            self._purge_expired()
            return {**self._stats, "active_holds": len(self._locks)}


# ---------------------------------------------------------------------------
# Demo scenario
# ---------------------------------------------------------------------------

def run_demo():
    print("=" * 60)
    print("SEAT LOCK ENGINE - Hold Timer Demo")
    print("=" * 60)

    # Short hold for demo purposes (3 seconds instead of 7 minutes)
    engine = SeatLockEngine(hold_duration=3)
    event = "coldplay-2026"

    # Scenario 1: successful hold and confirm
    print("\n--- Scenario 1: Hold + Confirm ---")
    result = engine.hold(event, "A1", "alice")
    print(f"Alice holds A1:    {result}")

    result = engine.confirm(event, "A1", "alice")
    print(f"Alice confirms A1: {result}")

    # Scenario 2: contention - two users want the same seat
    print("\n--- Scenario 2: Contention ---")
    result = engine.hold(event, "B5", "bob")
    print(f"Bob holds B5:      {result}")

    result = engine.hold(event, "B5", "carol")
    print(f"Carol tries B5:    {result}")

    # Scenario 3: wrong user tries to confirm
    print("\n--- Scenario 3: Ownership Check ---")
    result = engine.confirm(event, "B5", "carol")
    print(f"Carol confirms B5: {result}")

    result = engine.confirm(event, "B5", "bob")
    print(f"Bob confirms B5:   {result}")

    # Scenario 4: hold expires, seat becomes available
    print("\n--- Scenario 4: Hold Expiry (3s timer) ---")
    result = engine.hold(event, "C10", "dave")
    print(f"Dave holds C10:    {result}")

    status = engine.status(event, "C10")
    print(f"C10 status now:    {status}")

    print("Waiting 4 seconds for hold to expire...")
    time.sleep(4)

    status = engine.status(event, "C10")
    print(f"C10 status after:  {status}")

    result = engine.hold(event, "C10", "eve")
    print(f"Eve holds C10:     {result}")

    # Scenario 5: voluntary release
    print("\n--- Scenario 5: Voluntary Release ---")
    engine.hold(event, "D1", "frank")
    result = engine.release(event, "D1", "frank")
    print(f"Frank releases D1: {result}")

    result = engine.hold(event, "D1", "grace")
    print(f"Grace holds D1:    {result}")

    # Final stats
    print("\n--- Engine Stats ---")
    stats = engine.get_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    run_demo()
