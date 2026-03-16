"""
Health Check System
===================
Monitors multiple services with independent liveness and readiness
probes. Liveness failures trigger restarts. Readiness failures pull
the service from the load balancer rotation without restarting it.

Simulates services that go through healthy, degraded, overloaded,
and crashed states to show how each probe type responds differently.

Run: python health_checker.py
"""

import time
import random
import threading
from dataclasses import dataclass, field
from enum import Enum


# ---------------------------------------------------------------------------
# Service states and health result
# ---------------------------------------------------------------------------

class ServiceState(Enum):
    HEALTHY = "healthy"
    WARMING_UP = "warming_up"
    OVERLOADED = "overloaded"
    DEADLOCKED = "deadlocked"
    CRASHED = "crashed"


@dataclass
class HealthResult:
    alive: bool
    ready: bool
    details: str


# ---------------------------------------------------------------------------
# Simulated service
# ---------------------------------------------------------------------------

class Service:
    def __init__(self, name: str, warmup_seconds: float = 0):
        self.name = name
        self.state = ServiceState.WARMING_UP if warmup_seconds > 0 else ServiceState.HEALTHY
        self.warmup_seconds = warmup_seconds
        self.started_at = time.time()
        self.request_count = 0
        self.overload_threshold = random.randint(15, 25)
        self.restart_count = 0

    def liveness_check(self) -> HealthResult:
        if self.state == ServiceState.CRASHED:
            return HealthResult(alive=False, ready=False, details="process crashed - not responding")
        if self.state == ServiceState.DEADLOCKED:
            return HealthResult(alive=False, ready=False, details="process deadlocked - needs restart")
        return HealthResult(alive=True, ready=True, details="process is running")

    def readiness_check(self) -> HealthResult:
        if self.state in (ServiceState.CRASHED, ServiceState.DEADLOCKED):
            return HealthResult(alive=False, ready=False, details=f"state: {self.state.value}")
        if self.state == ServiceState.WARMING_UP:
            elapsed = time.time() - self.started_at
            remaining = max(0, self.warmup_seconds - elapsed)
            if remaining > 0:
                return HealthResult(alive=True, ready=False,
                                    details=f"warming up - {remaining:.1f}s remaining")
            self.state = ServiceState.HEALTHY
        if self.state == ServiceState.OVERLOADED:
            return HealthResult(alive=True, ready=False,
                                details=f"overloaded - {self.request_count} pending requests")
        return HealthResult(alive=True, ready=True, details="accepting traffic")

    def handle_request(self):
        self.request_count += 1
        if self.request_count >= self.overload_threshold:
            self.state = ServiceState.OVERLOADED

    def restart(self):
        self.restart_count += 1
        self.state = ServiceState.WARMING_UP
        self.started_at = time.time()
        self.request_count = 0
        self.overload_threshold = random.randint(15, 25)


# ---------------------------------------------------------------------------
# Health checker with configurable thresholds
# ---------------------------------------------------------------------------

class HealthChecker:
    def __init__(self, check_interval: float = 1.0,
                 liveness_threshold: int = 3,
                 readiness_threshold: int = 2):
        self.services: dict[str, Service] = {}
        self.check_interval = check_interval
        self.liveness_threshold = liveness_threshold
        self.readiness_threshold = readiness_threshold
        self.liveness_failures: dict[str, int] = {}
        self.readiness_failures: dict[str, int] = {}
        self.in_rotation: dict[str, bool] = {}
        self.log: list[str] = []

    def register(self, service: Service):
        self.services[service.name] = service
        self.liveness_failures[service.name] = 0
        self.readiness_failures[service.name] = 0
        self.in_rotation[service.name] = False

    def _log(self, msg: str):
        timestamp = time.strftime("%H:%M:%S")
        entry = f"[{timestamp}] {msg}"
        self.log.append(entry)
        print(entry)

    def check_all(self):
        for name, service in self.services.items():
            liveness = service.liveness_check()
            readiness = service.readiness_check()

            if not liveness.alive:
                self.liveness_failures[name] += 1
                self.readiness_failures[name] += 1
                if self.in_rotation[name]:
                    self.in_rotation[name] = False
                    self._log(f"  REMOVE {name} from rotation - {liveness.details}")
                if self.liveness_failures[name] >= self.liveness_threshold:
                    self._log(f"  RESTART {name} - liveness failed {self.liveness_failures[name]}x")
                    service.restart()
                    self.liveness_failures[name] = 0
                    self.readiness_failures[name] = 0
            elif not readiness.ready:
                self.liveness_failures[name] = 0
                self.readiness_failures[name] += 1
                if self.in_rotation[name]:
                    self.in_rotation[name] = False
                    self._log(f"  REMOVE {name} from rotation - {readiness.details}")
            else:
                if not self.in_rotation[name]:
                    self._log(f"  ADD {name} to rotation - {readiness.details}")
                    self.in_rotation[name] = True
                self.liveness_failures[name] = 0
                self.readiness_failures[name] = 0

    def get_healthy_services(self) -> list[str]:
        return [name for name, active in self.in_rotation.items() if active]

    def print_status(self):
        print("\n" + "=" * 60)
        print(f"{'Service':<15} {'State':<14} {'In Rotation':<14} {'Restarts':<10}")
        print("-" * 60)
        for name, service in self.services.items():
            rotation = "YES" if self.in_rotation[name] else "NO"
            print(f"{name:<15} {service.state.value:<14} {rotation:<14} {service.restart_count:<10}")
        healthy = self.get_healthy_services()
        print(f"\nAvailable backends: {healthy if healthy else 'NONE - all services degraded'}")
        print("=" * 60)


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

def run_simulation():
    print("Health Check System - Liveness & Readiness Probes")
    print("=" * 60)

    checker = HealthChecker(check_interval=1.0, liveness_threshold=3, readiness_threshold=2)

    api = Service("api-server", warmup_seconds=2.0)
    db = Service("database", warmup_seconds=3.0)
    cache = Service("cache", warmup_seconds=1.0)
    worker = Service("worker", warmup_seconds=0)

    for svc in [api, db, cache, worker]:
        checker.register(svc)

    scenarios = [
        (0, "STARTUP", "All services starting up - readiness probes will hold traffic"),
        (5, "NORMAL", "All services healthy and serving traffic"),
        (8, "OVERLOAD", "Sending burst of requests to api-server"),
        (12, "CRASH", "Database process crashes"),
        (18, "DEADLOCK", "Worker process deadlocks"),
        (24, "RECOVERY", "All services recovered after restarts"),
    ]

    scenario_idx = 0
    for tick in range(28):
        if scenario_idx < len(scenarios) and tick == scenarios[scenario_idx][0]:
            _, label, desc = scenarios[scenario_idx]
            print(f"\n--- [{label}] {desc} ---")
            scenario_idx += 1

        if tick == 8:
            for _ in range(20):
                api.handle_request()

        if tick == 12:
            db.state = ServiceState.CRASHED

        if tick == 18:
            worker.state = ServiceState.DEADLOCKED

        checker.check_all()
        time.sleep(0.3)

    checker.print_status()

    print("\n--- Summary ---")
    print(f"Total health checks run: {len(checker.log)}")
    restarts = sum(s.restart_count for s in checker.services.values())
    print(f"Total restarts triggered: {restarts}")
    print("\nKey insight: liveness failures trigger restarts.")
    print("Readiness failures remove from rotation but keep the process alive.")
    print("This prevents killing a service that's just temporarily overloaded.")


if __name__ == "__main__":
    run_simulation()
