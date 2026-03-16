"""
Naive Modulo Hashing vs Consistent Hashing
===========================================
Demonstrates the rehashing catastrophe with modulo hashing and
how consistent hashing keeps key redistribution to a minimum.
"""

import hashlib
from bisect import bisect_right

# ---------------------------------------------------------------------------
# Hashing helpers
# ---------------------------------------------------------------------------

def hash_key(key: str) -> int:
    return int(hashlib.md5(key.encode()).hexdigest(), 16)


# ---------------------------------------------------------------------------
# Modulo hashing - the naive approach
# ---------------------------------------------------------------------------

def modulo_assign(keys: list[str], num_servers: int) -> dict[str, int]:
    return {key: hash_key(key) % num_servers for key in keys}


# ---------------------------------------------------------------------------
# Consistent hashing - minimal redistribution
# ---------------------------------------------------------------------------

class SimpleConsistentHash:
    def __init__(self, servers: list[str], vnodes: int = 150):
        self.vnodes = vnodes
        self.ring: list[tuple[int, str]] = []
        for server in servers:
            self._add_server(server)
        self.ring.sort()

    def _add_server(self, server: str):
        for i in range(self.vnodes):
            vnode_key = f"{server}#vn{i}"
            pos = hash_key(vnode_key)
            self.ring.append((pos, server))

    def lookup(self, key: str) -> str:
        h = hash_key(key)
        positions = [entry[0] for entry in self.ring]
        idx = bisect_right(positions, h) % len(self.ring)
        return self.ring[idx][1]

    def assign_all(self, keys: list[str]) -> dict[str, str]:
        return {key: self.lookup(key) for key in keys}


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

def compare(num_keys: int, old_servers: int, new_servers: int):
    keys = [f"user:{i}" for i in range(num_keys)]

    print(f"\n{'='*60}")
    print(f"  {num_keys} keys | {old_servers} servers -> {new_servers} servers")
    print(f"{'='*60}")

    old_mod = modulo_assign(keys, old_servers)
    new_mod = modulo_assign(keys, new_servers)
    mod_moved = sum(1 for k in keys if old_mod[k] != new_mod[k])

    server_names_old = [f"server-{i}" for i in range(old_servers)]
    server_names_new = [f"server-{i}" for i in range(new_servers)]

    ch_old = SimpleConsistentHash(server_names_old)
    ch_new = SimpleConsistentHash(server_names_new)

    old_ch_map = ch_old.assign_all(keys)
    new_ch_map = ch_new.assign_all(keys)
    ch_moved = sum(1 for k in keys if old_ch_map[k] != new_ch_map[k])

    print(f"\n  Modulo hashing:")
    print(f"    Keys moved:  {mod_moved:>7,} / {num_keys:,}  ({mod_moved/num_keys*100:.1f}%)")
    print(f"    Theoretical: ~{(old_servers-1)/old_servers*100:.1f}% expected")

    print(f"\n  Consistent hashing:")
    print(f"    Keys moved:  {ch_moved:>7,} / {num_keys:,}  ({ch_moved/num_keys*100:.1f}%)")
    print(f"    Theoretical: ~{1/new_servers*100:.1f}% ideal (K/N)")

    ratio = mod_moved / max(ch_moved, 1)
    print(f"\n  Modulo moved {ratio:.1f}x more keys than consistent hashing")


# ---------------------------------------------------------------------------
# Show per-server distribution
# ---------------------------------------------------------------------------

def show_distribution(num_keys: int, num_servers: int):
    keys = [f"item:{i}" for i in range(num_keys)]
    server_names = [f"server-{i}" for i in range(num_servers)]

    ch = SimpleConsistentHash(server_names)
    assignment = ch.assign_all(keys)

    counts = {s: 0 for s in server_names}
    for server in assignment.values():
        counts[server] += 1

    ideal = num_keys / num_servers
    print(f"\n{'='*60}")
    print(f"  Distribution across {num_servers} servers ({num_keys} keys)")
    print(f"  Ideal per server: {ideal:.0f}")
    print(f"{'='*60}")
    print(f"  {'Server':<12} {'Keys':>7} {'vs Ideal':>10}")
    print(f"  {'-'*12} {'-'*7} {'-'*10}")

    for server, count in sorted(counts.items()):
        diff = ((count - ideal) / ideal) * 100
        print(f"  {server:<12} {count:>7,} {diff:>+9.1f}%")

    values = list(counts.values())
    std_dev = (sum((v - ideal) ** 2 for v in values) / len(values)) ** 0.5
    print(f"\n  Std deviation: {std_dev:.1f} keys ({std_dev/ideal*100:.1f}% of ideal)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Consistent Hashing - naive vs consistent comparison")

    compare(num_keys=10_000, old_servers=4, new_servers=5)
    compare(num_keys=10_000, old_servers=9, new_servers=10)
    compare(num_keys=100_000, old_servers=99, new_servers=100)

    show_distribution(num_keys=10_000, num_servers=5)
