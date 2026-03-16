"""
Conflict Resolution Strategies
===============================
Simulates concurrent writes on two leaders and resolves conflicts using
three strategies: last-write-wins, version vectors, and custom merge.
"""

import time
import copy

# ---------------------------------------------------------------------------
#   Multi-master node
# ---------------------------------------------------------------------------

class MasterNode:
    """A leader node in a multi-master setup."""

    def __init__(self, node_id):
        self.node_id = node_id
        self.data = {}
        self.version_clock = {}

    def local_write(self, key, value, timestamp=None):
        ts = timestamp or time.time()
        prev_vec = copy.deepcopy(self.version_clock.get(key, {}))
        prev_vec[self.node_id] = prev_vec.get(self.node_id, 0) + 1

        entry = {
            "value": value, "timestamp": ts,
            "origin": self.node_id, "vector": prev_vec,
        }
        self.data[key] = entry
        self.version_clock[key] = prev_vec
        print(f"  [Node {self.node_id}] WRITE {key}={value} "
              f"ts={ts:.4f} vec={prev_vec}")
        return entry


# ---------------------------------------------------------------------------
#   Resolution strategies
# ---------------------------------------------------------------------------

def resolve_lww(entry_a, entry_b):
    print("\n  --- Last-Write-Wins (LWW) ---")
    if entry_a["timestamp"] >= entry_b["timestamp"]:
        winner, loser = entry_a, entry_b
    else:
        winner, loser = entry_b, entry_a
    print(f"  Winner:  {winner['value']} from Node {winner['origin']}")
    print(f"  DROPPED: {loser['value']} from Node {loser['origin']} "
          f"(DATA LOST!)")
    return winner


def compare_vectors(vec_a, vec_b):
    all_keys = set(vec_a.keys()) | set(vec_b.keys())
    a_gte = all(vec_a.get(k, 0) >= vec_b.get(k, 0) for k in all_keys)
    b_gte = all(vec_b.get(k, 0) >= vec_a.get(k, 0) for k in all_keys)
    if a_gte and not b_gte:
        return "A_DOMINATES"
    if b_gte and not a_gte:
        return "B_DOMINATES"
    if a_gte and b_gte:
        return "EQUAL"
    return "CONCURRENT"


def resolve_version_vector(entry_a, entry_b):
    print("\n  --- Version Vectors ---")
    print(f"  A: {entry_a['value']} vec={entry_a['vector']}")
    print(f"  B: {entry_b['value']} vec={entry_b['vector']}")
    result = compare_vectors(entry_a["vector"], entry_b["vector"])
    print(f"  Comparison: {result}")
    if result == "CONCURRENT":
        print(f"  TRUE CONFLICT - neither write knew about the other.")
        return [entry_a, entry_b]
    if result == "A_DOMINATES":
        print(f"  A causally supersedes B. Keep: {entry_a['value']}")
        return entry_a
    print(f"  B causally supersedes A. Keep: {entry_b['value']}")
    return entry_b


def resolve_merge(entry_a, entry_b):
    print("\n  --- Custom Merge (set union) ---")
    val_a = set(entry_a["value"]) if isinstance(entry_a["value"], list) \
        else {entry_a["value"]}
    val_b = set(entry_b["value"]) if isinstance(entry_b["value"], list) \
        else {entry_b["value"]}
    merged = sorted(val_a | val_b)
    print(f"  A: {val_a}  B: {val_b}  Merged: {merged}")
    print(f"  No data lost - both contributions preserved.")
    return merged


# ---------------------------------------------------------------------------
#   Demos
# ---------------------------------------------------------------------------

def demo_concurrent_writes():
    print("=" * 65)
    print("CONCURRENT WRITES - Two leaders, same key, same time")
    print("=" * 65)
    node_a, node_b = MasterNode("A"), MasterNode("B")
    now = time.time()
    ea = node_a.local_write("cart:user1", "item-apple", now)
    eb = node_b.local_write("cart:user1", "item-banana", now + 0.001)

    resolve_lww(ea, eb)
    resolve_version_vector(ea, eb)
    resolve_merge(
        {"value": ["item-apple"], "vector": ea["vector"],
         "timestamp": ea["timestamp"], "origin": "A"},
        {"value": ["item-banana"], "vector": eb["vector"],
         "timestamp": eb["timestamp"], "origin": "B"})
    print()


def demo_causal_order():
    print("=" * 65)
    print("CAUSAL ORDER - Sequential writes on one node")
    print("=" * 65)
    node_a = MasterNode("A")
    now = time.time()
    e1 = node_a.local_write("status", "draft", now)
    e2 = node_a.local_write("status", "published", now + 1)
    resolve_version_vector(e1, e2)
    print("  Second write dominates - no conflict, just causal order.\n")


def demo_shopping_cart():
    print("=" * 65)
    print("SHOPPING CART - Merge vs LWW")
    print("=" * 65)
    phone, laptop = MasterNode("phone"), MasterNode("laptop")
    now = time.time()
    ea = phone.local_write("cart:user1", ["milk", "eggs"], now)
    eb = laptop.local_write("cart:user1", ["milk", "bread"], now + 0.001)
    print("\n  LWW discards one edit entirely:")
    resolve_lww(ea, eb)
    print("\n  Merge preserves both:")
    resolve_merge(ea, eb)
    print()


# ---------------------------------------------------------------------------
#   Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    demo_concurrent_writes()
    demo_causal_order()
    demo_shopping_cart()
    print("Done. LWW is simple but lossy. Version vectors detect conflicts.")
    print("Custom merge preserves data but requires domain knowledge.")
