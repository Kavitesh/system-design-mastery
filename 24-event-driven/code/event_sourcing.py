"""
Event Sourcing
==============
Event-sourced bank account. State is never stored directly - it's
reconstructed by replaying an immutable sequence of events.

Run: python event_sourcing.py
"""

import uuid
import time
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

# ---------------------------------------------------------------------------
# Events - immutable facts about what happened
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AccountEvent:
    event_type: str
    amount: float
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: float = field(default_factory=time.time)
    description: str = ""

    def __str__(self):
        ts = datetime.fromtimestamp(self.timestamp).strftime("%H:%M:%S")
        return f"[{ts}] {self.event_type:20s} ${self.amount:>10.2f}  {self.description}"


# ---------------------------------------------------------------------------
# Event Store - append-only log
# ---------------------------------------------------------------------------

class EventStore:
    def __init__(self):
        self._streams: dict = {}

    def append(self, stream_id: str, event: AccountEvent):
        if stream_id not in self._streams:
            self._streams[stream_id] = []
        self._streams[stream_id].append(event)

    def get_events(self, stream_id: str, up_to: float = None) -> List[AccountEvent]:
        events = self._streams.get(stream_id, [])
        if up_to is not None:
            return [e for e in events if e.timestamp <= up_to]
        return list(events)

    def stream_count(self) -> int:
        return len(self._streams)


# ---------------------------------------------------------------------------
# Bank Account - state rebuilt from events, never stored
# ---------------------------------------------------------------------------

class BankAccount:
    def __init__(self, account_id: str, store: EventStore):
        self.account_id = account_id
        self._store = store

    def _apply_events(self, events: List[AccountEvent]) -> dict:
        state = {"balance": 0.0, "opened": False, "transaction_count": 0}
        for event in events:
            if event.event_type == "AccountOpened":
                state["opened"] = True
                state["balance"] = event.amount
            elif event.event_type == "MoneyDeposited":
                state["balance"] += event.amount
                state["transaction_count"] += 1
            elif event.event_type == "MoneyWithdrawn":
                state["balance"] -= event.amount
                state["transaction_count"] += 1
            elif event.event_type == "InterestApplied":
                state["balance"] += event.amount
                state["transaction_count"] += 1
        return state

    def get_state(self) -> dict:
        events = self._store.get_events(self.account_id)
        return self._apply_events(events)

    def get_state_at(self, timestamp: float) -> dict:
        events = self._store.get_events(self.account_id, up_to=timestamp)
        return self._apply_events(events)

    def open(self, initial_deposit: float):
        event = AccountEvent("AccountOpened", initial_deposit, description="Initial deposit")
        self._store.append(self.account_id, event)
        return event

    def deposit(self, amount: float, description: str = ""):
        state = self.get_state()
        if not state["opened"]:
            raise ValueError("Account not opened")
        event = AccountEvent("MoneyDeposited", amount, description=description)
        self._store.append(self.account_id, event)
        return event

    def withdraw(self, amount: float, description: str = ""):
        state = self.get_state()
        if state["balance"] < amount:
            raise ValueError(f"Insufficient funds: ${state['balance']:.2f} < ${amount:.2f}")
        event = AccountEvent("MoneyWithdrawn", amount, description=description)
        self._store.append(self.account_id, event)
        return event

    def apply_interest(self, rate: float):
        state = self.get_state()
        interest = state["balance"] * rate
        event = AccountEvent("InterestApplied", round(interest, 2),
                             description=f"{rate*100:.1f}% on ${state['balance']:.2f}")
        self._store.append(self.account_id, event)
        return event


# ---------------------------------------------------------------------------
# Main demo
# ---------------------------------------------------------------------------

def main():
    print("=" * 65)
    print("EVENT SOURCING DEMO - Bank Account from Immutable Events")
    print("=" * 65)

    store = EventStore()
    account = BankAccount("ACCT-1001", store)

    # --- Build up a transaction history ---
    print("\n1. RECORDING TRANSACTIONS")
    print("-" * 50)
    events = []
    events.append(account.open(500.00))
    time.sleep(0.01)
    events.append(account.deposit(1200.00, "Paycheck"))
    time.sleep(0.01)
    events.append(account.withdraw(85.50, "Electric bill"))
    time.sleep(0.01)

    checkpoint_time = time.time()
    time.sleep(0.01)

    events.append(account.withdraw(200.00, "ATM withdrawal"))
    time.sleep(0.01)
    events.append(account.deposit(45.00, "Refund from Amazon"))
    time.sleep(0.01)
    events.append(account.apply_interest(0.02))

    for e in events:
        print(f"  {e}")

    # --- Current state from replay ---
    print("\n2. CURRENT STATE (rebuilt from events)")
    print("-" * 50)
    state = account.get_state()
    print(f"  Account:      {account.account_id}")
    print(f"  Balance:      ${state['balance']:.2f}")
    print(f"  Transactions: {state['transaction_count']}")

    # --- Temporal query: state at a past point ---
    print("\n3. TEMPORAL QUERY - 'What was the balance earlier?'")
    print("-" * 50)
    past_state = account.get_state_at(checkpoint_time)
    print(f"  Balance at checkpoint: ${past_state['balance']:.2f}")
    print(f"  Transactions at that point: {past_state['transaction_count']}")
    print(f"  (Before the ATM withdrawal, refund, and interest)")

    # --- Full event log ---
    print("\n4. COMPLETE AUDIT TRAIL")
    print("-" * 50)
    all_events = store.get_events("ACCT-1001")
    print(f"  {'#':<4} {'Event Type':<20} {'Amount':>10}  Description")
    print(f"  {'─'*4} {'─'*20} {'─'*10}  {'─'*20}")
    running = 0.0
    for i, e in enumerate(all_events, 1):
        if e.event_type == "AccountOpened":
            running = e.amount
        elif e.event_type in ("MoneyDeposited", "InterestApplied"):
            running += e.amount
        elif e.event_type == "MoneyWithdrawn":
            running -= e.amount
        print(f"  {i:<4} {e.event_type:<20} ${e.amount:>9.2f}  {e.description:<20} -> ${running:.2f}")

    # --- Overdraft protection ---
    print("\n5. BUSINESS RULE ENFORCEMENT")
    print("-" * 50)
    try:
        account.withdraw(99999.00, "Buy a car")
    except ValueError as err:
        print(f"  Withdrawal rejected: {err}")
        print(f"  No event created - the event log stays clean.")

    # --- Second account ---
    print("\n6. MULTIPLE ACCOUNTS (same event store)")
    print("-" * 50)
    account2 = BankAccount("ACCT-2002", store)
    account2.open(10000.00)
    account2.withdraw(3500.00, "Rent")
    account2.deposit(250.00, "Side gig")

    state2 = account2.get_state()
    print(f"  Account {account2.account_id}: ${state2['balance']:.2f}")
    print(f"  Total streams in event store: {store.stream_count()}")
    total_events = sum(len(store.get_events(sid)) for sid in ["ACCT-1001", "ACCT-2002"])
    print(f"  Total events across all accounts: {total_events}")

    print("\n" + "=" * 65)
    print("DONE - State was never stored. Every balance was computed by")
    print("replaying events. Change the replay logic and you change history.")
    print("=" * 65)


if __name__ == "__main__":
    main()
