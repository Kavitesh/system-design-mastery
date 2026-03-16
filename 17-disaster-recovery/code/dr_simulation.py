"""
Disaster Recovery Simulation
==============================
Simulates disaster scenarios and recovery using different DR strategies.
Models data loss, downtime, and recovery steps to show why strategy
selection matters more than most teams realize.
"""

import random
import time
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class Region:
    name: str
    is_primary: bool = False
    is_healthy: bool = True
    data_version: int = 0
    replication_lag_sec: float = 0.0
    services_running: list = field(default_factory=list)

    def write(self):
        self.data_version += 1
        return self.data_version


@dataclass
class DisasterEvent:
    name: str
    affected_region: str
    data_loss_window_sec: float
    downtime_sec: float
    description: str


@dataclass
class RecoveryResult:
    strategy: str
    disaster: str
    data_versions_lost: int
    downtime_sec: float
    recovery_steps: list
    success: bool


# ---------------------------------------------------------------------------
# DR strategies
# ---------------------------------------------------------------------------

class DRStrategy:
    name = "base"

    def recover(self, primary: Region, standby: Region, disaster: DisasterEvent) -> RecoveryResult:
        raise NotImplementedError


class BackupRestore(DRStrategy):
    name = "Backup & Restore"

    def __init__(self, backup_interval_sec: float = 3600):
        self.backup_interval = backup_interval_sec
        self.last_backup_version = 0

    def take_backup(self, region: Region):
        self.last_backup_version = region.data_version

    def recover(self, primary: Region, standby: Region, disaster: DisasterEvent) -> RecoveryResult:
        steps = []
        versions_lost = primary.data_version - self.last_backup_version

        steps.append(f"Detected failure in {primary.name}")
        steps.append(f"Last backup at version {self.last_backup_version} (current: {primary.data_version})")
        steps.append(f"Provisioning new infrastructure (estimated 45-60 min)")
        steps.append(f"Restoring from backup ({self.last_backup_version} versions to restore)")
        steps.append(f"Verifying data integrity")
        steps.append(f"Updating DNS records")
        steps.append(f"Recovery complete - lost {versions_lost} writes since last backup")

        return RecoveryResult(
            strategy=self.name,
            disaster=disaster.name,
            data_versions_lost=versions_lost,
            downtime_sec=max(disaster.downtime_sec, 3600),
            recovery_steps=steps,
            success=True,
        )


class PilotLight(DRStrategy):
    name = "Pilot Light"

    def recover(self, primary: Region, standby: Region, disaster: DisasterEvent) -> RecoveryResult:
        steps = []
        lag_versions = max(1, int(standby.replication_lag_sec * 10))

        steps.append(f"Detected failure in {primary.name}")
        steps.append(f"DR database in {standby.name} has replication lag of {standby.replication_lag_sec:.0f}s")
        steps.append(f"Spinning up application servers in {standby.name} (est. 15-30 min)")
        steps.append(f"Promoting DR database to primary")
        steps.append(f"Configuring load balancer")
        steps.append(f"Running smoke tests")
        steps.append(f"Switching DNS to {standby.name}")
        steps.append(f"Recovery complete - lost ~{lag_versions} recent writes")

        return RecoveryResult(
            strategy=self.name,
            disaster=disaster.name,
            data_versions_lost=lag_versions,
            downtime_sec=1800,
            recovery_steps=steps,
            success=True,
        )


class WarmStandby(DRStrategy):
    name = "Warm Standby"

    def recover(self, primary: Region, standby: Region, disaster: DisasterEvent) -> RecoveryResult:
        steps = []
        lag_versions = max(1, int(standby.replication_lag_sec * 10))

        steps.append(f"Detected failure in {primary.name}")
        steps.append(f"Warm standby in {standby.name} already running (scaled down)")
        steps.append(f"Scaling up compute capacity in {standby.name}")
        steps.append(f"Promoting DR database to primary")
        steps.append(f"Updating DNS to {standby.name}")
        steps.append(f"Recovery complete - lost ~{lag_versions} recent writes")

        return RecoveryResult(
            strategy=self.name,
            disaster=disaster.name,
            data_versions_lost=lag_versions,
            downtime_sec=900,
            recovery_steps=steps,
            success=True,
        )


class ActiveActive(DRStrategy):
    name = "Active-Active"

    def recover(self, primary: Region, standby: Region, disaster: DisasterEvent) -> RecoveryResult:
        steps = []

        steps.append(f"Detected failure in {primary.name}")
        steps.append(f"{standby.name} already serving traffic")
        steps.append(f"Removing {primary.name} from routing pool")
        steps.append(f"Redistributing traffic to remaining regions")
        steps.append(f"Recovery complete - zero data loss (sync replication)")

        return RecoveryResult(
            strategy=self.name,
            disaster=disaster.name,
            data_versions_lost=0,
            downtime_sec=30,
            recovery_steps=steps,
            success=True,
        )


# ---------------------------------------------------------------------------
# Disaster scenarios
# ---------------------------------------------------------------------------

DISASTERS = [
    DisasterEvent(
        name="Database corruption",
        affected_region="us-east-1",
        data_loss_window_sec=300,
        downtime_sec=7200,
        description="A bad migration corrupts the users table. Replication copies the corruption everywhere.",
    ),
    DisasterEvent(
        name="Region-wide outage",
        affected_region="us-east-1",
        data_loss_window_sec=60,
        downtime_sec=14400,
        description="AWS us-east-1 loses power. All services in the region are unreachable.",
    ),
    DisasterEvent(
        name="Accidental deletion",
        affected_region="us-east-1",
        data_loss_window_sec=10,
        downtime_sec=3600,
        description="An engineer runs DROP TABLE orders in production. Replication deletes it everywhere.",
    ),
    DisasterEvent(
        name="Network partition",
        affected_region="us-east-1",
        data_loss_window_sec=30,
        downtime_sec=1800,
        description="A fiber cut isolates us-east-1. The region is up but unreachable from the internet.",
    ),
]

# ---------------------------------------------------------------------------
# Simulation runner
# ---------------------------------------------------------------------------

def simulate_production_writes(primary: Region, standby: Region, num_writes: int, repl_lag: float):
    for _ in range(num_writes):
        primary.write()
    standby.data_version = primary.data_version - int(repl_lag * 10)
    standby.replication_lag_sec = repl_lag


def run_simulation():
    strategies = [
        BackupRestore(backup_interval_sec=3600),
        PilotLight(),
        WarmStandby(),
        ActiveActive(),
    ]

    print("Setting up production environment...")
    print()

    primary = Region(name="us-east-1", is_primary=True)
    standby = Region(name="us-west-2", is_primary=False)

    num_writes = 10000
    simulate_production_writes(primary, standby, num_writes, repl_lag=5.0)

    if isinstance(strategies[0], BackupRestore):
        strategies[0].last_backup_version = primary.data_version - 500

    print(f"  Primary ({primary.name}): {primary.data_version} data versions")
    print(f"  Standby ({standby.name}): {standby.data_version} data versions (lag: {standby.replication_lag_sec}s)")
    print(f"  Last full backup: version {strategies[0].last_backup_version}")
    print()

    for disaster in DISASTERS:
        print("=" * 72)
        print(f"DISASTER: {disaster.name}")
        print(f"  {disaster.description}")
        print("=" * 72)
        print()

        results = []
        for strategy in strategies:
            p = Region(name=primary.name, is_primary=True,
                       data_version=primary.data_version)
            s = Region(name=standby.name, is_primary=False,
                       data_version=standby.data_version,
                       replication_lag_sec=standby.replication_lag_sec)

            result = strategy.recover(p, s, disaster)
            results.append(result)

            print(f"  [{strategy.name}]")
            for step in result.recovery_steps:
                print(f"    -> {step}")
            print()

        print(f"  {'Strategy':<25} {'Data Lost':>12} {'Downtime':>14}")
        print(f"  {'-'*25} {'-'*12} {'-'*14}")
        for r in results:
            lost = f"{r.data_versions_lost} writes" if r.data_versions_lost > 0 else "None"
            if r.downtime_sec >= 3600:
                dt = f"{r.downtime_sec/3600:.1f} hours"
            elif r.downtime_sec >= 60:
                dt = f"{r.downtime_sec/60:.0f} minutes"
            else:
                dt = f"{r.downtime_sec:.0f} seconds"
            print(f"  {r.strategy:<25} {lost:>12} {dt:>14}")
        print()

    print("-" * 72)
    print("Key insight: Backup & Restore handles data corruption (accidental")
    print("deletion, bad migrations) better than replication-based strategies,")
    print("because replication faithfully copies the damage. You need BOTH")
    print("replication for hardware failures AND backups for logical errors.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    random.seed(42)
    print("Disaster Recovery Simulation")
    print()
    run_simulation()
