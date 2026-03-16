"""
ZooKeeper-like Service Registry
================================
Simulates a coordination service with ephemeral nodes, watches,
session TTLs, and automatic deregistration on failure. Demonstrates
service discovery patterns used in ZooKeeper and etcd.
"""

import time
from collections import defaultdict

# ---------------------------------------------------------------------------
# Service registry (simplified ZooKeeper)
# ---------------------------------------------------------------------------
class ZNode:
    def __init__(self, path, data="", ephemeral=False, session_id=None):
        self.path = path
        self.data = data
        self.ephemeral = ephemeral
        self.session_id = session_id
        self.children = []


class ServiceRegistry:
    def __init__(self):
        self.znodes = {"/": ZNode("/")}
        self.sessions = {}
        self.watches = defaultdict(list)
        self.seq_counters = defaultdict(int)
        self.log_count = 0

    def _log(self, msg):
        self.log_count += 1
        print(f"  [{self.log_count:>3}] {msg}")

    def create_session(self, client_id, ttl=5):
        self.sessions[client_id] = {"ttl": ttl, "active": True}
        self._log(f"Session created: {client_id} (TTL={ttl}s)")
        return client_id

    def create(self, path, data="", ephemeral=False, session_id=None, sequential=False):
        if sequential:
            self.seq_counters[path] += 1
            path = f"{path}-{self.seq_counters[path]:04d}"
        parent = "/".join(path.split("/")[:-1]) or "/"
        if parent not in self.znodes or path in self.znodes:
            return None
        node = ZNode(path, data, ephemeral, session_id)
        self.znodes[path] = node
        self.znodes[parent].children.append(path)
        kind = "ephemeral" if ephemeral else "persistent"
        self._log(f"Created {kind}: {path} = {data}" if data else f"Created {kind}: {path}")
        self._fire_watches(parent, "CHILD_ADDED", path)
        return path

    def get(self, path):
        return self.znodes[path].data if path in self.znodes else None

    def get_children(self, path):
        return list(self.znodes[path].children) if path in self.znodes else []

    def delete(self, path, reason="explicit"):
        if path not in self.znodes:
            return
        for child in list(self.znodes[path].children):
            self.delete(child, reason)
        parent = "/".join(path.split("/")[:-1]) or "/"
        if parent in self.znodes:
            self.znodes[parent].children.remove(path)
        del self.znodes[path]
        self._log(f"Deleted: {path} ({reason})")
        self._fire_watches(parent, "CHILD_REMOVED", path)

    def expire_session(self, client_id):
        self.sessions[client_id]["active"] = False
        self._log(f"Session expired: {client_id}")
        paths = [p for p, n in list(self.znodes.items())
                 if n.ephemeral and n.session_id == client_id]
        for p in paths:
            self.delete(p, reason=f"session expired ({client_id})")

    def watch(self, path, callback):
        self.watches[path].append(callback)

    def _fire_watches(self, path, event, data):
        for cb in self.watches.pop(path, []):
            cb(path, event, data)

    def print_tree(self, path="/", indent=0):
        if path not in self.znodes:
            return
        node = self.znodes[path]
        name = path.split("/")[-1] or "/"
        flags = []
        if node.ephemeral:
            flags.append("ephemeral")
        if node.data and path != "/":
            flags.append(f"data={node.data}")
        extra = f" ({', '.join(flags)})" if flags else ""
        print(f"  {'    ' * indent}{name}{extra}")
        for child in sorted(node.children):
            self.print_tree(child, indent + 1)


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------
def on_change(path, event, data):
    print(f"  >>> WATCH: {event} on {path} - {data}")


def run():
    reg = ServiceRegistry()

    print("=" * 60)
    print("Phase 1: Service registration")
    print("=" * 60)
    reg.create("/services")
    reg.create("/services/api")
    reg.create("/services/worker")

    for i, addr in enumerate(["10.0.1.1:8080", "10.0.1.2:8080", "10.0.1.3:8080"], 1):
        sid = reg.create_session(f"api-host-{i}")
        reg.create("/services/api/inst", data=addr, ephemeral=True,
                   session_id=sid, sequential=True)

    sid_w = reg.create_session("worker-host-1")
    reg.create("/services/worker/inst", data="10.0.2.1:9090",
               ephemeral=True, session_id=sid_w, sequential=True)
    print("\n  Service tree:")
    reg.print_tree()

    print("\n" + "=" * 60)
    print("Phase 2: Service discovery with watches")
    print("=" * 60)
    reg.watch("/services/api", on_change)
    instances = reg.get_children("/services/api")
    print(f"  Discovered {len(instances)} API instances:")
    for inst in instances:
        print(f"    {inst} -> {reg.get(inst)}")

    print("\n" + "=" * 60)
    print("Phase 3: api-host-2 crashes")
    print("=" * 60)
    reg.expire_session("api-host-2")
    remaining = reg.get_children("/services/api")
    print(f"\n  API instances after crash: {len(remaining)}")
    for inst in remaining:
        print(f"    {inst} -> {reg.get(inst)}")

    print("\n" + "=" * 60)
    print("Phase 4: Leader election via sequential nodes")
    print("=" * 60)
    reg.create("/election")
    for name in ["node-alpha", "node-beta", "node-gamma"]:
        sid = reg.create_session(name)
        reg.create("/election/candidate", data=name, ephemeral=True,
                   session_id=sid, sequential=True)

    children = sorted(reg.get_children("/election"))
    leader_path = children[0]
    leader_name = reg.get(leader_path)
    print(f"\n  Candidates (lowest sequence = leader):")
    for c in children:
        role = "LEADER" if c == leader_path else "follower"
        print(f"    {c} = {reg.get(c)} [{role}]")

    print("\n" + "=" * 60)
    print("Phase 5: Leader crashes, next takes over")
    print("=" * 60)
    reg.expire_session(leader_name)
    children = sorted(reg.get_children("/election"))
    new_leader = reg.get(children[0])
    print(f"\n  New leader: {new_leader}")
    for c in children:
        role = "LEADER" if c == children[0] else "follower"
        print(f"    {c} = {reg.get(c)} [{role}]")

    print("\n  Final tree:")
    reg.print_tree()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("ZooKeeper-like Service Registry\n")
    run()
    print("\nKey patterns:")
    print("  - Ephemeral nodes vanish when sessions expire (crash detection)")
    print("  - Sequential nodes provide ordering (leader election)")
    print("  - Watches notify clients of changes (service discovery)")
