"""
Split-Brain Demonstration
==========================
Shows what happens when a network partition creates two leaders,
then demonstrates how fencing tokens prevent stale writes from
corrupting shared storage.
"""

# ---------------------------------------------------------------------------
# Storage backend (shared resource both leaders write to)
# ---------------------------------------------------------------------------
class SharedStorage:
    def __init__(self, use_fencing=False):
        self.data = {}
        self.use_fencing = use_fencing
        self.highest_token = 0
        self.log = []

    def write(self, key, value, token=None):
        if self.use_fencing:
            if token is None or token < self.highest_token:
                status = "REJECTED (stale)" if token else "REJECTED (no token)"
                self.log.append((key, value, token, status))
                return False
            self.highest_token = token
        self.data[key] = value
        self.log.append((key, value, token, "ACCEPTED"))
        return True

    def print_log(self):
        print(f"  {'#':>3}  {'Key':<16} {'Value':<12} {'Token':<7} Status")
        print(f"  {'---':>3}  {'---':<16} {'---':<12} {'---':<7} ---")
        for i, (k, v, t, s) in enumerate(self.log, 1):
            print(f"  {i:>3}  {k:<16} {v:<12} {str(t or '-'):<7} {s}")


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------
def scenario_no_fencing():
    print("=" * 60)
    print("Scenario 1: Split-brain WITHOUT fencing tokens")
    print("=" * 60)
    print("  Two leaders write to shared storage. No protection.\n")

    store = SharedStorage(use_fencing=False)

    print("  Leader A (term=3) writes:")
    for k, v in [("user:100", "active"), ("order:500", "processing"), ("balance", "$450")]:
        store.write(k, v)

    print("  Leader B (term=4) writes:")
    for k, v in [("user:100", "suspended"), ("order:500", "cancelled"), ("balance", "$500")]:
        store.write(k, v)

    print("  Leader A's stale write (doesn't know B exists):")
    store.write("balance", "$350")

    print("\n  Write log:")
    store.print_log()
    print(f"\n  Final balance: {store.data['balance']}")
    print("  PROBLEM: Stale leader overwrote the correct value\n")


def scenario_with_fencing():
    print("=" * 60)
    print("Scenario 2: Split-brain WITH fencing tokens")
    print("=" * 60)
    print("  Storage rejects writes with stale tokens.\n")

    store = SharedStorage(use_fencing=True)

    print("  Leader A writes (token=3):")
    for k, v in [("user:100", "active"), ("order:500", "processing"), ("balance", "$450")]:
        store.write(k, v, token=3)

    print("  Leader B writes (token=4 - accepted, higher):")
    for k, v in [("user:100", "suspended"), ("order:500", "cancelled"), ("balance", "$500")]:
        store.write(k, v, token=4)

    print("  Leader A retries (token=3 < 4 - REJECTED):")
    store.write("balance", "$350", token=3)
    store.write("user:100", "active", token=3)

    print("\n  Write log:")
    store.print_log()
    print(f"\n  Final balance: {store.data['balance']}")
    print("  SAFE: Stale writes rejected by fencing token check\n")


def scenario_timeline():
    print("=" * 60)
    print("Scenario 3: Partition timeline (how quorum helps)")
    print("=" * 60)

    events = [
        ("T=0 ", "Cluster healthy. Leader A (term=3) serving requests."),
        ("T=1 ", "Network partition: {A,B} | {C,D,E}"),
        ("T=2 ", "A sends heartbeats to B. A still thinks it's leader."),
        ("T=3 ", "C,D,E timeout. C starts election (term=4)."),
        ("T=4 ", "C wins with votes from D,E. New leader C (term=4)."),
        ("T=5 ", ">>> TWO LEADERS: A(term=3) and C(term=4) <<<"),
        ("T=6 ", "A can't commit - only {A,B}, needs 3 acks."),
        ("T=7 ", "C commits normally with {C,D,E} majority."),
        ("T=8 ", "Partition heals. A sees term=4, steps down."),
        ("T=9 ", "A's uncommitted entries overwritten. Cluster converged."),
    ]
    for ts, desc in events:
        marker = ">>>" if "TWO LEADERS" in desc else "   "
        print(f"  {marker} {ts}: {desc}")

    print("\n  The minority partition can't commit (no quorum).")
    print("  But it CAN corrupt external resources without fencing tokens.\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Split-Brain Problem and Fencing Tokens\n")
    scenario_no_fencing()
    scenario_with_fencing()
    scenario_timeline()

    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print("  - Quorum prevents internal split-brain")
    print("  - External resources need fencing tokens for protection")
    print("  - Fencing tokens are monotonic - stale leaders get blocked")
    print("  - The storage layer is the final safety net, not the leader")
