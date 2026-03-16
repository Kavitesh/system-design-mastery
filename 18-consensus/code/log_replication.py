"""
Raft Log Replication Simulation
================================
Demonstrates Raft-style log replication with AppendEntries RPCs,
commit index tracking, and majority acknowledgment. Shows how
a leader replicates entries and handles lagging followers.
"""

# ---------------------------------------------------------------------------
# Log entry and node
# ---------------------------------------------------------------------------
class LogEntry:
    def __init__(self, term, command):
        self.term = term
        self.command = command

    def __repr__(self):
        return f"[T{self.term}:{self.command}]"


class RaftNode:
    def __init__(self, node_id, is_leader=False):
        self.node_id = node_id
        self.is_leader = is_leader
        self.log = []
        self.commit_index = -1
        self.current_term = 1
        self.next_index = {}
        self.match_index = {}

    def append_command(self, command):
        entry = LogEntry(self.current_term, command)
        self.log.append(entry)
        print(f"  Leader appends {entry} at index {len(self.log) - 1}")

    def build_append_entries(self, follower_id):
        ni = self.next_index[follower_id]
        prev_idx = ni - 1
        prev_term = self.log[prev_idx].term if prev_idx >= 0 else 0
        return {"term": self.current_term, "prev_index": prev_idx,
                "prev_term": prev_term, "entries": self.log[ni:],
                "leader_commit": self.commit_index}

    def handle_append_entries(self, msg):
        prev = msg["prev_index"]
        if prev >= 0 and (prev >= len(self.log) or self.log[prev].term != msg["prev_term"]):
            return {"success": False, "match": -1, "node": self.node_id}
        pos = prev + 1
        for entry in msg["entries"]:
            if pos < len(self.log) and self.log[pos].term != entry.term:
                self.log = self.log[:pos]
            if pos >= len(self.log):
                self.log.append(entry)
            pos += 1
        if msg["leader_commit"] > self.commit_index:
            self.commit_index = min(msg["leader_commit"], len(self.log) - 1)
        return {"success": True, "match": prev + len(msg["entries"]), "node": self.node_id}

    def handle_response(self, resp, fid, cluster_size):
        if resp["success"]:
            self.match_index[fid] = resp["match"]
            self.next_index[fid] = resp["match"] + 1
        else:
            self.next_index[fid] = max(0, self.next_index[fid] - 1)
        for idx in range(len(self.log) - 1, self.commit_index, -1):
            if self.log[idx].term != self.current_term:
                continue
            count = 1 + sum(1 for mi in self.match_index.values() if mi >= idx)
            if count >= (cluster_size // 2) + 1:
                old = self.commit_index
                self.commit_index = idx
                if old != idx:
                    print(f"  Commit index: {old} -> {idx} (replicated on {count}/{cluster_size})")
                break

    def status(self):
        log_str = " ".join(str(e) for e in self.log) or "(empty)"
        role = "LEADER" if self.is_leader else "follow"
        return f"  {role:>6} {self.node_id}: {log_str}  commit={self.commit_index}"


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------
def replicate(leader, followers, size, drop=None):
    for f in followers:
        if f.node_id == drop:
            continue
        msg = leader.build_append_entries(f.node_id)
        resp = f.handle_append_entries(msg)
        leader.handle_response(resp, f.node_id, size)


def run():
    size = 5
    leader = RaftNode("L", is_leader=True)
    followers = [RaftNode(f"F{i}") for i in range(1, size)]
    for f in followers:
        leader.next_index[f.node_id] = 0
        leader.match_index[f.node_id] = -1

    print("=" * 60)
    print("Phase 1: Normal replication")
    print("=" * 60)
    for cmd in ["SET x=1", "SET y=2", "SET z=3"]:
        leader.append_command(cmd)
    replicate(leader, followers, size)
    for n in [leader] + followers:
        print(n.status())

    print("\n" + "=" * 60)
    print("Phase 2: F3 goes offline, new writes continue")
    print("=" * 60)
    leader.current_term = 2
    for cmd in ["DEL y", "SET w=10"]:
        leader.append_command(cmd)
    replicate(leader, followers, size, drop="F3")
    for n in [leader] + followers:
        print(n.status())

    print("\n" + "=" * 60)
    print("Phase 3: F3 reconnects, catches up")
    print("=" * 60)
    replicate(leader, followers, size)
    replicate(leader, followers, size)
    for n in [leader] + followers:
        print(n.status())

    print("\n" + "=" * 60)
    print("Consistency check")
    print("=" * 60)
    ok = all(len(f.log) == len(leader.log) for f in followers)
    print(f"  All logs match leader: {ok}")
    print(f"  Entries: {len(leader.log)}, committed: {leader.commit_index + 1}")


if __name__ == "__main__":
    print("Raft Log Replication Simulation\n")
    run()
