"""
Two-Phase Commit Simulation
============================
Simulates 2PC with a coordinator and multiple participants.
Demonstrates success, participant failure, and coordinator
timeout scenarios.

Run: python two_phase_commit.py
"""

import time
import threading
from enum import Enum

# ---------------------------------------------------------------------------
# Participant states and vote outcomes
# ---------------------------------------------------------------------------

class Vote(Enum):
    YES = "YES"
    NO = "NO"
    TIMEOUT = "TIMEOUT"

class ParticipantState(Enum):
    INIT = "INIT"
    PREPARED = "PREPARED"
    COMMITTED = "COMMITTED"
    ABORTED = "ABORTED"

# ---------------------------------------------------------------------------
# Participant - holds resources and responds to coordinator
# ---------------------------------------------------------------------------

class Participant:
    def __init__(self, name: str, fail_on_prepare=False, slow=False):
        self.name = name
        self.state = ParticipantState.INIT
        self.fail_on_prepare = fail_on_prepare
        self.slow = slow
        self.wal = []

    def prepare(self) -> Vote:
        if self.slow:
            time.sleep(0.3)
        if self.fail_on_prepare:
            print(f"  [{self.name}] PREPARE - validation failed, voting NO")
            self.state = ParticipantState.ABORTED
            return Vote.NO
        self.wal.append("PREPARE")
        self.state = ParticipantState.PREPARED
        print(f"  [{self.name}] PREPARE - locks acquired, WAL written, voting YES")
        return Vote.YES

    def commit(self):
        self.wal.append("COMMIT")
        self.state = ParticipantState.COMMITTED
        print(f"  [{self.name}] COMMIT - changes applied, locks released")

    def abort(self):
        self.wal.append("ABORT")
        self.state = ParticipantState.ABORTED
        print(f"  [{self.name}] ABORT - rolled back, locks released")

# ---------------------------------------------------------------------------
# Coordinator - drives the 2PC protocol
# ---------------------------------------------------------------------------

class Coordinator:
    def __init__(self, participants: list, timeout: float = 0.2):
        self.participants = participants
        self.timeout = timeout

    def _collect_vote(self, p: Participant, results: dict):
        try:
            results[p.name] = p.prepare()
        except Exception:
            results[p.name] = Vote.TIMEOUT

    def run(self) -> str:
        print("\n--- Phase 1: PREPARE (Voting) ---")
        votes = {}
        threads = [threading.Thread(target=self._collect_vote, args=(p, votes))
                   for p in self.participants]
        for t in threads: t.start()
        for t in threads: t.join(timeout=self.timeout)

        for p in self.participants:
            if p.name not in votes:
                votes[p.name] = Vote.TIMEOUT
                print(f"  [{p.name}] TIMEOUT - no response within {self.timeout}s")

        print(f"\n  Votes: {', '.join(f'{k}={v.value}' for k, v in votes.items())}")

        if all(v == Vote.YES for v in votes.values()):
            print("\n--- Phase 2: COMMIT (all voted YES) ---")
            for p in self.participants:
                p.commit()
            return "COMMIT"
        else:
            print("\n--- Phase 2: ABORT (not all voted YES) ---")
            for p in self.participants:
                if p.state == ParticipantState.PREPARED:
                    p.abort()
                else:
                    print(f"  [{p.name}] Already aborted, skipping")
            return "ABORT"

# ---------------------------------------------------------------------------
# Run scenarios
# ---------------------------------------------------------------------------

def run_scenario(title: str, participants: list):
    print(f"\n{'='*60}")
    print(f"SCENARIO: {title}")
    print(f"{'='*60}")
    result = Coordinator(participants).run()
    print(f"\n  Decision: {result}")
    for p in participants:
        print(f"  [{p.name}] state={p.state.value}, WAL={p.wal}")


def main():
    print("2PC - Two-Phase Commit Simulation")

    run_scenario("All participants succeed", [
        Participant("FlightDB"), Participant("HotelDB"), Participant("PaymentDB")])

    run_scenario("One participant fails validation", [
        Participant("FlightDB"), Participant("HotelDB", fail_on_prepare=True),
        Participant("PaymentDB")])

    run_scenario("Participant timeout (simulates crash)", [
        Participant("FlightDB"), Participant("HotelDB", slow=True),
        Participant("PaymentDB")])

    print(f"\n{'='*60}")
    print("KEY TAKEAWAY: 2PC blocks when participants are slow or")
    print("unreachable. All participants hold locks until the")
    print("coordinator decides. This is why 2PC is risky across")
    print("unreliable networks.")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
