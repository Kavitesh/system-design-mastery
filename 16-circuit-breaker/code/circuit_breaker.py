"""
Circuit Breaker Implementation
==============================
Full state machine with closed, open, and half-open states.
Simulates a flaky service to demonstrate state transitions.
"""

import time
import random
import threading
from enum import Enum

# ---------------------------------------------------------------------------
#  Circuit Breaker States
# ---------------------------------------------------------------------------

class State(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    def __init__(self, name, failure_threshold=3, reset_timeout=5, success_threshold=2):
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.success_threshold = success_threshold

        self.state = State.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.lock = threading.Lock()

    def call(self, func, *args, **kwargs):
        with self.lock:
            if self.state == State.OPEN:
                if self._timeout_expired():
                    self._transition(State.HALF_OPEN)
                else:
                    raise CircuitOpenError(f"[{self.name}] Circuit is OPEN - failing fast")

        try:
            result = func(*args, **kwargs)
        except Exception as e:
            self._on_failure()
            raise
        else:
            self._on_success()
            return result

    def _on_success(self):
        with self.lock:
            if self.state == State.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.success_threshold:
                    self._transition(State.CLOSED)
                else:
                    print(f"  [{self.name}] Half-open success {self.success_count}/{self.success_threshold}")
            elif self.state == State.CLOSED:
                self.failure_count = 0

    def _on_failure(self):
        with self.lock:
            if self.state == State.HALF_OPEN:
                self.success_count = 0
                self._transition(State.OPEN)
            elif self.state == State.CLOSED:
                self.failure_count += 1
                if self.failure_count >= self.failure_threshold:
                    self._transition(State.OPEN)
                else:
                    print(f"  [{self.name}] Failure {self.failure_count}/{self.failure_threshold}")

    def _transition(self, new_state):
        print(f"  [{self.name}] {self.state.value} -> {new_state.value}")
        self.state = new_state
        if new_state == State.OPEN:
            self.last_failure_time = time.time()
        self.failure_count = 0
        self.success_count = 0

    def _timeout_expired(self):
        return time.time() - self.last_failure_time >= self.reset_timeout


class CircuitOpenError(Exception):
    pass


# ---------------------------------------------------------------------------
#  Simulated Service
# ---------------------------------------------------------------------------

class FlakyService:
    def __init__(self):
        self.healthy = True

    def call(self):
        if not self.healthy:
            raise ConnectionError("Service unavailable")
        return "OK"


# ---------------------------------------------------------------------------
#  Demo
# ---------------------------------------------------------------------------

def main():
    print("Circuit Breaker Demo")
    print("=" * 50)

    service = FlakyService()
    breaker = CircuitBreaker("payment-svc", failure_threshold=3, reset_timeout=4, success_threshold=2)

    def make_request(label):
        try:
            result = breaker.call(service.call)
            print(f"  {label}: Success - {result}")
        except CircuitOpenError as e:
            print(f"  {label}: {e}")
        except ConnectionError as e:
            print(f"  {label}: Failed - {e}")

    print("\nPhase 1: Healthy - requests succeed")
    for i in range(3):
        make_request(f"req-{i+1}")

    print("\nPhase 2: Service down - breaker trips after 3 failures")
    service.healthy = False
    for i in range(5):
        make_request(f"req-{i+4}")

    print(f"\nPhase 3: Waiting {breaker.reset_timeout}s for reset timeout...")
    time.sleep(breaker.reset_timeout + 0.5)

    print("\nPhase 4: Half-open test - still down, breaker re-opens")
    make_request("req-10")

    print(f"\nPhase 5: Waiting {breaker.reset_timeout}s, then service recovers...")
    time.sleep(breaker.reset_timeout + 0.5)
    service.healthy = True

    print("\nPhase 6: Half-open succeeds - breaker closes")
    for i in range(4):
        make_request(f"req-{i+11}")


if __name__ == "__main__":
    main()
