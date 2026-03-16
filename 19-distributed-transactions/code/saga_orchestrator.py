"""
Saga Orchestrator Pattern
==========================
A central orchestrator coordinates a multi-step trip booking
transaction. When a step fails, it runs compensating
transactions in reverse order to undo completed steps.

Run: python saga_orchestrator.py
"""

import time
import uuid
from dataclasses import dataclass
from enum import Enum

# ---------------------------------------------------------------------------
# Saga step definition
# ---------------------------------------------------------------------------

class StepStatus(Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    COMPENSATED = "COMPENSATED"
    FAILED = "FAILED"

@dataclass
class SagaStep:
    name: str
    action: callable
    compensation: callable
    status: StepStatus = StepStatus.PENDING

# ---------------------------------------------------------------------------
# Simulated services
# ---------------------------------------------------------------------------

def make_service(label: str, fail: bool = False):
    def forward(booking_id: str) -> bool:
        print(f"  [{label}] Processing for booking {booking_id[:8]}...")
        time.sleep(0.05)
        if fail:
            print(f"  [{label}] FAILED - resource unavailable")
            return False
        conf = f"{label[:2].upper()}-{booking_id[:6].upper()}"
        print(f"  [{label}] Success - confirmation {conf}")
        return True

    def compensate(booking_id: str):
        print(f"  [{label}] Compensating for {booking_id[:8]}...")
        print(f"  [{label}] Reservation cancelled, resources released")

    return forward, compensate

# ---------------------------------------------------------------------------
# Saga orchestrator - manages steps and compensations
# ---------------------------------------------------------------------------

class SagaOrchestrator:
    def __init__(self, saga_id: str, steps: list):
        self.saga_id = saga_id
        self.steps = steps
        self.completed_steps = []

    def execute(self) -> bool:
        print(f"\n  Saga {self.saga_id[:8]} - executing {len(self.steps)} steps")
        for i, step in enumerate(self.steps):
            print(f"\n  --- Step {i+1}/{len(self.steps)}: {step.name} ---")
            if step.action():
                step.status = StepStatus.COMPLETED
                self.completed_steps.append(step)
            else:
                step.status = StepStatus.FAILED
                print(f"\n  Step '{step.name}' FAILED - starting compensation")
                self._compensate()
                return False
        print(f"\n  Saga {self.saga_id[:8]} completed successfully")
        return True

    def _compensate(self):
        print(f"\n  --- Running compensations (reverse order) ---")
        for step in reversed(self.completed_steps):
            print(f"\n  Compensating: {step.name}")
            step.compensation()
            step.status = StepStatus.COMPENSATED

    def print_summary(self):
        print(f"\n  Step Summary:")
        icons = {"COMPLETED": "+", "COMPENSATED": "~", "FAILED": "X", "PENDING": " "}
        for step in self.steps:
            print(f"    [{icons[step.status.value]}] {step.name}: {step.status.value}")

# ---------------------------------------------------------------------------
# Run trip booking scenarios
# ---------------------------------------------------------------------------

def run_booking(title: str, fail_step: str = None):
    print(f"\n{'='*60}")
    print(f"SCENARIO: {title}")
    print(f"{'='*60}")

    bid = str(uuid.uuid4())
    services = {
        "Flight": make_service("Flight", fail="Flight" == fail_step),
        "Hotel": make_service("Hotel", fail="Hotel" == fail_step),
        "Car Rental": make_service("Car Rental", fail="Car Rental" == fail_step),
        "Payment": make_service("Payment", fail="Payment" == fail_step),
    }

    steps = [
        SagaStep(f"Reserve {name}", lambda b=bid, s=svc: s[0](b), lambda b=bid, s=svc: s[1](b))
        for name, svc in services.items()
    ]

    saga = SagaOrchestrator(bid, steps)
    saga.execute()
    saga.print_summary()


def main():
    print("Saga Orchestrator - Trip Booking Simulation")

    run_booking("Successful trip booking")
    run_booking("Hotel unavailable - compensate flight", fail_step="Hotel")
    run_booking("Car unavailable - compensate flight and hotel", fail_step="Car Rental")

    print(f"\n{'='*60}")
    print("KEY TAKEAWAY: The orchestrator runs steps sequentially.")
    print("On failure, it compensates completed steps in reverse.")
    print("Each compensation is a new transaction, not a rollback -")
    print("the flight cancellation is a real cancellation, not an undo.")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
