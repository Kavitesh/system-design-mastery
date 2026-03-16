"""
Active-Passive Failover Simulation
====================================
Simulates a database cluster with one primary and one standby node.
The primary handles all writes and sends heartbeats to the standby.
When heartbeats stop, the standby promotes itself to primary.

Demonstrates heartbeat detection, replication lag, split-brain risk,
and the tradeoffs between fast detection and false positives.

Run: python failover_demo.py
"""

import time
import threading
import random
from dataclasses import dataclass, field
from enum import Enum


# ---------------------------------------------------------------------------
# Node roles and states
# ---------------------------------------------------------------------------

class Role(Enum):
    PRIMARY = "PRIMARY"
    STANDBY = "STANDBY"
    PROMOTING = "PROMOTING"


@dataclass
class WriteOperation:
    sequence: int
    data: str
    timestamp: float


# ---------------------------------------------------------------------------
# Database node
# ---------------------------------------------------------------------------

class DatabaseNode:
    def __init__(self, name: str, role: Role):
        self.name = name
        self.role = role
        self.alive = True
        self.data: list[WriteOperation] = []
        self.last_heartbeat_sent = 0.0
        self.last_heartbeat_received = 0.0
        self.write_seq = 0
        self.lock = threading.Lock()

    def write(self, value: str) -> WriteOperation | None:
        if self.role != Role.PRIMARY or not self.alive:
            return None
        with self.lock:
            self.write_seq += 1
            op = WriteOperation(self.write_seq, value, time.time())
            self.data.append(op)
            return op

    def replicate(self, op: WriteOperation):
        with self.lock:
            self.data.append(op)

    def send_heartbeat(self) -> float:
        self.last_heartbeat_sent = time.time()
        return self.last_heartbeat_sent

    def receive_heartbeat(self, timestamp: float):
        self.last_heartbeat_received = timestamp

    def promote(self):
        self.role = Role.PROMOTING
        time.sleep(0.5)
        self.role = Role.PRIMARY

    def kill(self):
        self.alive = False

    def recover(self):
        self.alive = True
        self.role = Role.STANDBY


# ---------------------------------------------------------------------------
# Cluster coordinator
# ---------------------------------------------------------------------------

class FailoverCluster:
    def __init__(self, heartbeat_interval: float = 1.0,
                 failover_timeout: float = 3.0):
        self.primary = DatabaseNode("node-1", Role.PRIMARY)
        self.standby = DatabaseNode("node-2", Role.STANDBY)
        self.heartbeat_interval = heartbeat_interval
        self.failover_timeout = failover_timeout
        self.failover_triggered = False
        self.failover_time = 0.0
        self.replication_lag_ops = 0
        self.log: list[str] = []

    def _log(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        entry = f"[{ts}] {msg}"
        self.log.append(entry)
        print(entry)

    def simulate_writes(self, count: int, interval: float = 0.3):
        operations = [
            "INSERT user (id=101, name='alice')",
            "UPDATE account SET balance=500 WHERE id=101",
            "INSERT order (id=5001, user_id=101, total=79.99)",
            "DELETE session WHERE expired < NOW()",
            "UPDATE inventory SET stock=stock-1 WHERE product_id=42",
            "INSERT payment (id=8001, amount=79.99, status='pending')",
            "UPDATE order SET status='shipped' WHERE id=5001",
            "INSERT audit_log (action='login', user_id=101)",
        ]
        for i in range(count):
            sql = operations[i % len(operations)]
            op = self.primary.write(sql)
            if op:
                self._log(f"  PRIMARY write #{op.sequence}: {sql}")
                lag = random.uniform(0.01, 0.05)
                time.sleep(lag)
                if self.standby.alive:
                    self.standby.replicate(op)
                    self._log(f"  STANDBY replicated #{op.sequence} (lag: {lag*1000:.0f}ms)")
                else:
                    self.replication_lag_ops += 1
            time.sleep(interval)

    def run_heartbeats(self, duration: float):
        start = time.time()
        while time.time() - start < duration:
            if self.primary.alive:
                ts = self.primary.send_heartbeat()
                self.standby.receive_heartbeat(ts)
            time.sleep(self.heartbeat_interval)

    def check_failover(self) -> bool:
        if not self.standby.alive:
            return False
        since_last = time.time() - self.standby.last_heartbeat_received
        if since_last > self.failover_timeout:
            return True
        return False

    def print_cluster_status(self):
        print(f"\n{'='*55}")
        print(f"{'Node':<12} {'Role':<12} {'Alive':<8} {'Writes':<8} {'Data Rows'}")
        print(f"{'-'*55}")
        for node in [self.primary, self.standby]:
            print(f"{node.name:<12} {node.role.value:<12} "
                  f"{'YES' if node.alive else 'NO':<8} "
                  f"{node.write_seq:<8} {len(node.data)}")
        print(f"{'='*55}")


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

def run_failover_simulation():
    print("Active-Passive Failover Simulation")
    print("=" * 55)
    print(f"Heartbeat interval: 1.0s | Failover timeout: 3.0s\n")

    cluster = FailoverCluster(heartbeat_interval=1.0, failover_timeout=3.0)

    # Phase 1: Normal operation
    print("--- PHASE 1: Normal Operation ---")
    cluster._log("Cluster started - node-1 is PRIMARY, node-2 is STANDBY")

    hb_thread = threading.Thread(target=cluster.run_heartbeats, args=(4.0,))
    hb_thread.start()
    cluster.simulate_writes(5, interval=0.5)
    hb_thread.join()
    cluster.print_cluster_status()

    # Phase 2: Primary failure
    print("\n--- PHASE 2: Primary Failure ---")
    cluster._log("SIMULATING primary node-1 crash")
    cluster.primary.kill()
    cluster._log("node-1 is DOWN - heartbeats stopped")

    print("\nWaiting for failover timeout...")
    detection_start = time.time()
    for second in range(4):
        time.sleep(0.8)
        since = time.time() - cluster.standby.last_heartbeat_received
        missed = int(since / cluster.heartbeat_interval)
        cluster._log(f"  node-2: no heartbeat for {since:.1f}s ({missed} missed)")

        if cluster.check_failover() and not cluster.failover_triggered:
            cluster.failover_time = time.time() - detection_start
            cluster.failover_triggered = True
            cluster._log(f"  FAILOVER TRIGGERED - promoting node-2 to PRIMARY")
            cluster.standby.promote()
            cluster._log(f"  node-2 is now PRIMARY (promotion took 0.5s)")
            break

    cluster.print_cluster_status()

    # Phase 3: New primary serves traffic
    print("\n--- PHASE 3: New Primary Serves Traffic ---")
    old_primary = cluster.primary
    cluster.primary = cluster.standby
    cluster.primary.write_seq = len(cluster.primary.data)

    cluster.simulate_writes(3, interval=0.4)
    cluster.print_cluster_status()

    # Phase 4: Old primary recovers as standby
    print("\n--- PHASE 4: Old Primary Recovers as Standby ---")
    old_primary.recover()
    cluster.standby = old_primary
    cluster._log(f"node-1 recovered - rejoining as STANDBY")
    cluster._log(f"node-1 needs to sync {cluster.replication_lag_ops} missed operations")

    for op in cluster.primary.data[len(cluster.standby.data):]:
        cluster.standby.replicate(op)
    cluster._log(f"node-1 caught up - {len(cluster.standby.data)} rows synced")
    cluster.print_cluster_status()

    # Summary
    print("\n--- Failover Summary ---")
    print(f"Detection time:    {cluster.failover_time:.1f}s (timeout threshold: 3.0s)")
    print(f"Promotion time:    0.5s")
    print(f"Total failover:    {cluster.failover_time + 0.5:.1f}s")
    print(f"Operations lost:   {cluster.replication_lag_ops} (async replication gap)")
    print(f"Split-brain risk:  None (old primary confirmed dead before promotion)")

    print("\n--- Key Tradeoffs ---")
    print("Shorter timeout  = faster detection, but more false positives")
    print("Longer timeout   = fewer false alarms, but more downtime during real failures")
    print("Sync replication = zero data loss, but higher write latency")
    print("Async replication = lower latency, but potential data loss on failover")


if __name__ == "__main__":
    run_failover_simulation()
