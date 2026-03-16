"""
Quorum Reads and Writes
=======================
Demonstrates the quorum formula W + R > N for leaderless replication.
Shows how different W/R/N configurations affect consistency and
availability.
"""

import random

# ---------------------------------------------------------------------------
#   Replica node
# ---------------------------------------------------------------------------

class ReplicaNode:
    """A single node in a leaderless replicated cluster."""

    def __init__(self, node_id):
        self.node_id = node_id
        self.data = {}
        self.alive = True
        self.version = 0

    def write(self, key, value):
        if not self.alive:
            return None
        self.version += 1
        self.data[key] = {"value": value, "version": self.version}
        return self.version

    def read(self, key):
        if not self.alive:
            return None
        return self.data.get(key)


# ---------------------------------------------------------------------------
#   Quorum cluster
# ---------------------------------------------------------------------------

class QuorumCluster:
    """Manages N replicas with configurable read and write quorums."""

    def __init__(self, n, w, r):
        self.n = n
        self.w = w
        self.r = r
        self.nodes = [ReplicaNode(i) for i in range(n)]
        self.quorum_ok = (w + r) > n

    def info(self):
        status = "CONSISTENT" if self.quorum_ok else "NOT GUARANTEED"
        print(f"  N={self.n}, W={self.w}, R={self.r}, "
              f"W+R={self.w + self.r} {'>' if self.quorum_ok else '<='} "
              f"N={self.n} -> {status}")

    def quorum_write(self, key, value):
        ack_count = 0
        write_nodes = []
        for node in self.nodes:
            ver = node.write(key, value)
            if ver is not None:
                ack_count += 1
                write_nodes.append(node.node_id)
            if ack_count >= self.w:
                break

        success = ack_count >= self.w
        symbol = "OK" if success else "FAIL"
        print(f"  WRITE {key}={value} -> acks={ack_count}/{self.w} "
              f"[{symbol}] nodes={write_nodes}")
        return success

    def quorum_read(self, key):
        responses = []
        read_nodes = []
        shuffled = list(self.nodes)
        random.shuffle(shuffled)

        for node in shuffled:
            result = node.read(key)
            if result is not None:
                responses.append(result)
                read_nodes.append(node.node_id)
            elif node.alive:
                read_nodes.append(node.node_id)
            if len(read_nodes) >= self.r:
                break

        if not responses:
            print(f"  READ {key} -> None [NO DATA] nodes={read_nodes}")
            return None

        best = max(responses, key=lambda r: r["version"])
        print(f"  READ {key} -> {best['value']} (v{best['version']}) "
              f"nodes={read_nodes}")
        return best["value"]

    def kill_node(self, node_id):
        self.nodes[node_id].alive = False
        print(f"  NODE {node_id} is DOWN")


# ---------------------------------------------------------------------------
#   Scenarios
# ---------------------------------------------------------------------------

def run_scenario(title, n, w, r, note):
    print("=" * 65)
    print(f"SCENARIO: {title}")
    print("=" * 65)
    cluster = QuorumCluster(n=n, w=w, r=r)
    cluster.info()
    print()
    cluster.quorum_write("user:1", "Alice")
    cluster.quorum_read("user:1")
    print(f"  {note}\n")
    return cluster


def scenario_fault_tolerance():
    print("=" * 65)
    print("SCENARIO: Node failure (N=3, W=2, R=2)")
    print("=" * 65)
    cluster = QuorumCluster(n=3, w=2, r=2)
    cluster.info()
    print()

    cluster.quorum_write("user:4", "Diana")
    print()
    cluster.kill_node(2)
    print("  With one node down:")
    cluster.quorum_write("user:5", "Eve")
    cluster.quorum_read("user:4")
    print()

    cluster.kill_node(1)
    print("  With two nodes down:")
    result = cluster.quorum_write("user:6", "Frank")
    if not result:
        print("  Can't reach W=2 with only 1 node alive.")
    print()


# ---------------------------------------------------------------------------
#   Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    random.seed(42)

    run_scenario(
        "Balanced (N=3, W=2, R=2)", 3, 2, 2,
        "Overlap guaranteed - read always sees latest write.")

    run_scenario(
        "Write-heavy (N=3, W=1, R=3)", 3, 1, 3,
        "Fast writes (W=1), but reads must hit all 3 nodes.")

    run_scenario(
        "Unsafe (N=3, W=1, R=1)", 3, 1, 1,
        "W+R=2 <= N=3: read might miss the written node. No guarantee.")

    run_scenario(
        "Large cluster (N=5, W=3, R=3)", 5, 3, 3,
        "Tolerates 2 node failures for both reads and writes.")

    scenario_fault_tolerance()

    print("Done. The formula W + R > N is the dividing line for consistency.")
