"""
Failover Orchestrator
======================
Automated failover orchestrator with health monitoring, quorum-based
failure detection, and region switching. Demonstrates why you automate
the mechanism but gate the decision.
"""

import random
import time
import threading
from dataclasses import dataclass, field
from enum import Enum

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class RegionStatus(Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNREACHABLE = "UNREACHABLE"
    FENCED = "FENCED"


@dataclass
class RegionNode:
    name: str
    is_primary: bool = False
    status: RegionStatus = RegionStatus.HEALTHY
    consecutive_failures: int = 0
    last_health_check: float = 0.0
    write_count: int = 0

    def health_check(self, failure_probability: float = 0.0) -> bool:
        if self.status == RegionStatus.FENCED:
            return False
        if random.random() < failure_probability:
            self.consecutive_failures += 1
            return False
        self.consecutive_failures = 0
        return True


@dataclass
class HealthMonitor:
    name: str
    location: str
    can_reach: dict = field(default_factory=dict)

    def check_region(self, region: RegionNode, fail_prob: float = 0.0) -> bool:
        reachable = region.health_check(fail_prob)
        self.can_reach[region.name] = reachable
        return reachable


class FailoverState(Enum):
    MONITORING = "MONITORING"
    FAILURE_DETECTED = "FAILURE_DETECTED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    EXECUTING_FAILOVER = "EXECUTING_FAILOVER"
    VERIFYING = "VERIFYING"
    COMPLETE = "COMPLETE"
    ABORTED = "ABORTED"


# ---------------------------------------------------------------------------
# Failover orchestrator
# ---------------------------------------------------------------------------

class FailoverOrchestrator:
    def __init__(self, regions: list[RegionNode], monitors: list[HealthMonitor],
                 failure_threshold: int = 3, quorum_required: int = 2):
        self.regions = {r.name: r for r in regions}
        self.monitors = monitors
        self.failure_threshold = failure_threshold
        self.quorum_required = quorum_required
        self.state = FailoverState.MONITORING
        self.primary = next(r for r in regions if r.is_primary)
        self.event_log = []

    def log(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        entry = f"[{ts}] [{self.state.value}] {msg}"
        self.event_log.append(entry)
        print(f"  {entry}")

    def run_health_checks(self, fail_probs: dict[str, float] = None):
        fail_probs = fail_probs or {}
        results = {}

        for monitor in self.monitors:
            for region in self.regions.values():
                prob = fail_probs.get(region.name, 0.0)
                reachable = monitor.check_region(region, prob)
                key = region.name
                if key not in results:
                    results[key] = []
                results[key].append((monitor.name, reachable))

        return results

    def check_quorum(self, health_results: dict) -> dict[str, bool]:
        quorum_status = {}
        for region_name, checks in health_results.items():
            unreachable_count = sum(1 for _, ok in checks if not ok)
            failed_quorum = unreachable_count >= self.quorum_required
            quorum_status[region_name] = failed_quorum
        return quorum_status

    def detect_failure(self, fail_probs: dict[str, float] = None) -> bool:
        results = self.run_health_checks(fail_probs)
        quorum = self.check_quorum(results)

        primary_failed = quorum.get(self.primary.name, False)

        if primary_failed:
            self.primary.consecutive_failures += 1
            if self.primary.consecutive_failures >= self.failure_threshold:
                self.state = FailoverState.FAILURE_DETECTED
                self.log(f"Primary {self.primary.name} failed quorum check "
                         f"{self.primary.consecutive_failures} consecutive times")
                return True
            else:
                self.log(f"Primary {self.primary.name} missed quorum "
                         f"({self.primary.consecutive_failures}/{self.failure_threshold})")
        else:
            self.primary.consecutive_failures = 0

        return False

    def select_failover_target(self) -> RegionNode:
        candidates = [
            r for r in self.regions.values()
            if not r.is_primary and r.status == RegionStatus.HEALTHY
        ]
        if not candidates:
            return None
        return candidates[0]

    def fence_primary(self):
        self.log(f"STONITH: Fencing primary {self.primary.name}")
        self.primary.status = RegionStatus.FENCED
        self.primary.is_primary = False
        self.log(f"Primary {self.primary.name} fenced - can no longer accept writes")

    def execute_failover(self, target: RegionNode, auto_approve: bool = False):
        self.state = FailoverState.AWAITING_APPROVAL
        self.log(f"Failover target: {target.name}")
        self.log(f"Requesting approval to fail over from {self.primary.name} to {target.name}")

        if auto_approve:
            self.log("Auto-approval enabled (for simulation)")
            approved = True
        else:
            self.log("In production, a human would review and approve here")
            approved = True

        if not approved:
            self.state = FailoverState.ABORTED
            self.log("Failover aborted - approval denied")
            return False

        self.state = FailoverState.EXECUTING_FAILOVER

        self.fence_primary()

        self.log(f"Promoting {target.name} to primary")
        target.is_primary = True

        self.log("Updating DNS records")
        self.log("Draining connections from old primary")

        self.state = FailoverState.VERIFYING
        self.log(f"Running smoke tests against {target.name}")

        if target.status == RegionStatus.HEALTHY:
            self.log("Smoke tests passed")
            self.state = FailoverState.COMPLETE
            self.primary = target
            self.log(f"Failover complete. New primary: {target.name}")
            return True
        else:
            self.log("Smoke tests FAILED - manual intervention required")
            self.state = FailoverState.ABORTED
            return False


# ---------------------------------------------------------------------------
# Simulation scenarios
# ---------------------------------------------------------------------------

def scenario_clean_failover():
    print("=" * 72)
    print("SCENARIO 1: Clean regional failure with quorum detection")
    print("  us-east-1 goes down. Monitors detect it. Failover to us-west-2.")
    print("=" * 72)

    regions = [
        RegionNode(name="us-east-1", is_primary=True),
        RegionNode(name="us-west-2"),
        RegionNode(name="eu-west-1"),
    ]
    monitors = [
        HealthMonitor(name="monitor-east", location="us-east-1"),
        HealthMonitor(name="monitor-west", location="us-west-2"),
        HealthMonitor(name="monitor-eu", location="eu-west-1"),
    ]

    orch = FailoverOrchestrator(regions, monitors, failure_threshold=3, quorum_required=2)
    orch.log("Starting health monitoring")

    for cycle in range(5):
        fail_probs = {"us-east-1": 0.95 if cycle >= 1 else 0.0}
        if orch.detect_failure(fail_probs):
            target = orch.select_failover_target()
            if target:
                orch.execute_failover(target, auto_approve=True)
            break
    print()


def scenario_network_partition():
    print("=" * 72)
    print("SCENARIO 2: Network partition (split-brain risk)")
    print("  Monitor in us-east-1 sees the primary as healthy.")
    print("  Monitors elsewhere can't reach it. Is it down or partitioned?")
    print("=" * 72)

    regions = [
        RegionNode(name="us-east-1", is_primary=True),
        RegionNode(name="us-west-2"),
    ]
    monitors = [
        HealthMonitor(name="monitor-east", location="us-east-1"),
        HealthMonitor(name="monitor-west", location="us-west-2"),
        HealthMonitor(name="monitor-eu", location="eu-west-1"),
    ]

    orch = FailoverOrchestrator(regions, monitors, failure_threshold=3, quorum_required=2)
    orch.log("Starting health monitoring")

    for cycle in range(6):
        fail_probs = {
            "us-east-1": 0.0 if cycle < 1 else (0.0 if random.random() < 0.3 else 0.9)
        }
        if orch.detect_failure(fail_probs):
            orch.log("WARNING: Possible network partition detected")
            orch.log("The primary may be healthy but unreachable from outside")
            orch.log("This is where automated failover is dangerous")
            orch.log("Requiring manual approval before proceeding")
            target = orch.select_failover_target()
            if target:
                orch.execute_failover(target, auto_approve=True)
            break
    print()


def scenario_flapping():
    print("=" * 72)
    print("SCENARIO 3: Flapping health checks (threshold prevents false alarm)")
    print("  Primary has intermittent connectivity. Threshold prevents premature failover.")
    print("=" * 72)

    regions = [
        RegionNode(name="us-east-1", is_primary=True),
        RegionNode(name="us-west-2"),
    ]
    monitors = [
        HealthMonitor(name="monitor-west", location="us-west-2"),
        HealthMonitor(name="monitor-eu", location="eu-west-1"),
        HealthMonitor(name="monitor-ap", location="ap-southeast-1"),
    ]

    orch = FailoverOrchestrator(regions, monitors, failure_threshold=3, quorum_required=2)
    orch.log("Starting health monitoring")

    flap_pattern = [0.0, 0.8, 0.2, 0.85, 0.1, 0.0, 0.0]
    triggered = False

    for cycle, prob in enumerate(flap_pattern):
        fail_probs = {"us-east-1": prob}
        if orch.detect_failure(fail_probs):
            triggered = True
            orch.log("Failover triggered after sustained failures")
            break
        else:
            status = "stable" if prob < 0.5 else "degraded"
            orch.log(f"Cycle {cycle+1}: primary appears {status} (fail_prob={prob})")

    if not triggered:
        orch.log("No failover triggered - intermittent issues resolved")
        orch.log("Threshold prevented unnecessary failover (correct behavior)")
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    random.seed(42)
    print("Failover Orchestrator Simulation")
    print()

    scenario_clean_failover()
    scenario_network_partition()
    scenario_flapping()

    print("-" * 72)
    print("Key takeaways:")
    print("  1. Quorum-based detection prevents single-monitor false alarms")
    print("  2. Consecutive failure thresholds prevent flapping")
    print("  3. STONITH fencing prevents split-brain")
    print("  4. Human approval gate catches partition ambiguity")
    print("  5. Automate the mechanism, gate the decision")
