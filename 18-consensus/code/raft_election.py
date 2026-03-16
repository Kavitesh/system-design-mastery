"""
Raft Leader Election Simulation
================================
Simulates Raft's leader election with terms, randomized timeouts,
RequestVote RPCs, and majority quorum. Run multiple times to see
different nodes win based on timeout randomization.
"""

import random

# ---------------------------------------------------------------------------
# Node states
# ---------------------------------------------------------------------------
FOLLOWER = "Follower"
CANDIDATE = "Candidate"
LEADER = "Leader"


class RaftNode:
    def __init__(self, node_id, cluster_size):
        self.node_id = node_id
        self.cluster_size = cluster_size
        self.state = FOLLOWER
        self.current_term = 0
        self.voted_for = None
        self.votes_received = 0
        self.election_timeout = random.randint(5, 15)
        self.ticks = 0

    def quorum(self):
        return (self.cluster_size // 2) + 1

    def tick(self):
        if self.state == LEADER:
            return None
        self.ticks += 1
        if self.ticks >= self.election_timeout:
            return self._start_election()
        return None

    def _start_election(self):
        self.current_term += 1
        self.state = CANDIDATE
        self.voted_for = self.node_id
        self.votes_received = 1
        self.election_timeout = random.randint(5, 15)
        self.ticks = 0
        return {"type": "RequestVote", "term": self.current_term,
                "candidate_id": self.node_id}

    def handle_request_vote(self, msg):
        if msg["term"] > self.current_term:
            self.current_term = msg["term"]
            self.state = FOLLOWER
            self.voted_for = None
        if msg["term"] < self.current_term:
            return {"granted": False, "voter": self.node_id}
        if self.voted_for in (None, msg["candidate_id"]):
            self.voted_for = msg["candidate_id"]
            self.ticks = 0
            return {"granted": True, "voter": self.node_id}
        return {"granted": False, "voter": self.node_id}

    def handle_vote_response(self, resp):
        if self.state != CANDIDATE:
            return
        if resp["granted"]:
            self.votes_received += 1
            if self.votes_received >= self.quorum():
                self.state = LEADER

    def receive_heartbeat(self, leader_id, term):
        if term >= self.current_term:
            self.current_term = term
            self.state = FOLLOWER
            self.voted_for = None
            self.ticks = 0


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------
def simulate_election(num_nodes=5, max_ticks=50, crash_node=None):
    nodes = {i: RaftNode(i, num_nodes) for i in range(num_nodes)}
    quorum = nodes[0].quorum()
    print(f"Cluster: {num_nodes} nodes, quorum={quorum}"
          + (f", node {crash_node} crashed" if crash_node is not None else ""))

    for tick in range(1, max_ticks + 1):
        requests = []
        for nid, node in nodes.items():
            if nid == crash_node:
                continue
            result = node.tick()
            if result:
                requests.append((nid, result))
                print(f"  [tick {tick:2d}] Node {nid} starts election (term={result['term']})")

        for sender, req in requests:
            for nid, node in nodes.items():
                if nid == sender or nid == crash_node:
                    continue
                resp = node.handle_request_vote(req)
                if resp["granted"]:
                    print(f"  [tick {tick:2d}] Node {nid} votes for Node {sender}")
                nodes[sender].handle_vote_response(resp)

        for nid, node in nodes.items():
            if node.state == LEADER:
                print(f"\n  ** Node {nid} wins (term={node.current_term}, "
                      f"votes={node.votes_received}/{num_nodes}) **\n")
                for oid, other in nodes.items():
                    if oid != nid and oid != crash_node:
                        other.receive_heartbeat(nid, node.current_term)
                return nid

    print("  No leader elected within tick limit")
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Raft Leader Election Simulation\n")

    print("=" * 60)
    print("Scenario 1: Normal 5-node election")
    print("=" * 60)
    simulate_election(num_nodes=5)

    print("=" * 60)
    print("Scenario 2: Election with one crashed node")
    print("=" * 60)
    simulate_election(num_nodes=5, crash_node=2)

    print("=" * 60)
    print("Scenario 3: Multiple rounds (different winners each time)")
    print("=" * 60)
    winners = {}
    for r in range(1, 6):
        print(f"--- Round {r} ---")
        w = simulate_election(num_nodes=5)
        if w is not None:
            winners[w] = winners.get(w, 0) + 1

    print("Election results:")
    for nid in sorted(winners):
        print(f"  Node {nid}: won {winners[nid]} time(s)")
    print("Different nodes win due to randomized election timeouts")
