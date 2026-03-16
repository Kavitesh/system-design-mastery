"""
Tunable Consistency Demo
========================
A 5-node quorum system where you control the read and write
consistency levels (ONE, QUORUM, ALL). Shows how R + W > N
determines whether stale reads are possible.

Run: python tunable_consistency.py
"""

import time
import random
import threading

N = 5

# ---------------------------------------------------------------------------
#  Replica with simulated latency
# ---------------------------------------------------------------------------

class Replica:
    def __init__(self, rid):
        self.rid = rid
        self.store = {}
        self.latency = random.uniform(1, 8) / 1000

    def write(self, key, val, ver):
        time.sleep(self.latency)
        cur = self.store.get(key)
        if cur is None or ver > cur[1]:
            self.store[key] = (val, ver)

    def read(self, key):
        time.sleep(self.latency)
        e = self.store.get(key)
        return e if e else (None, 0)

# ---------------------------------------------------------------------------
#  Quorum cluster
# ---------------------------------------------------------------------------

class QuorumCluster:
    def __init__(self):
        self.replicas = [Replica(i) for i in range(N)]
        self.ver = 0

    def _resolve(self, level):
        if level == "ONE": return 1
        if level == "QUORUM": return N // 2 + 1
        if level == "ALL": return N
        return int(level)

    def write(self, key, val, wl="QUORUM"):
        w = self._resolve(wl)
        self.ver += 1
        start = time.time()
        done = 0
        for r in self.replicas:
            r.write(key, val, self.ver)
            done += 1
            if done >= w:
                break
        elapsed = (time.time() - start) * 1000
        rest = self.replicas[done:]
        for r in rest:
            threading.Thread(target=r.write, args=(key, val, self.ver),
                             daemon=True).start()
        return {"ok": done >= w, "acks": done, "need": w,
                "ver": self.ver, "ms": round(elapsed, 2)}

    def read(self, key, rl="QUORUM"):
        r_need = self._resolve(rl)
        start = time.time()
        results = []
        for r in self.replicas:
            results.append(r.read(key))
            if len(results) >= r_need:
                break
        elapsed = (time.time() - start) * 1000
        results.sort(key=lambda x: x[1], reverse=True)
        val, ver = results[0]
        return {"val": val, "ver": ver, "nodes": r_need,
                "ms": round(elapsed, 2)}

# ---------------------------------------------------------------------------
#  Scenarios
# ---------------------------------------------------------------------------

def run_scenario(label, wl, rl):
    c = QuorumCluster()
    print(f"\n--- W={wl}, R={rl} ---")
    w_needed = c._resolve(wl)
    r_needed = c._resolve(rl)
    strong = (w_needed + r_needed) > N
    print(f"    R+W = {r_needed}+{w_needed} = {r_needed + w_needed} "
          f"{'>' if strong else '<='} {N}  ->  "
          f"{'STRONG' if strong else 'EVENTUAL'}\n")

    w = c.write("user", "Alice", wl)
    print(f"    Write 'Alice': acks={w['acks']}/{w['need']}, "
          f"v{w['ver']}, {w['ms']}ms")
    w2 = c.write("user", "Alice_v2", wl)
    print(f"    Write 'Alice_v2': acks={w2['acks']}/{w2['need']}, "
          f"v{w2['ver']}, {w2['ms']}ms")
    r = c.read("user", rl)
    stale = r["ver"] < w2["ver"]
    tag = " ** STALE **" if stale else ""
    print(f"    Read: val='{r['val']}', v{r['ver']}, "
          f"queried={r['nodes']}, {r['ms']}ms{tag}")

# ---------------------------------------------------------------------------
#  Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print(f"  TUNABLE CONSISTENCY DEMO  (N={N}, QUORUM={N//2+1})")
    print("=" * 60)

    run_scenario("Fastest, weakest", "ONE", "ONE")
    run_scenario("Balanced", "QUORUM", "QUORUM")
    run_scenario("Slow writes, fast reads", "ALL", "ONE")
    run_scenario("Fast writes, slow reads", "ONE", "ALL")

    print("\n" + "=" * 60)
    print("  QUORUM FORMULA: R + W > N guarantees strong consistency")
    print()
    print("  W=1, R=1   -> 2 <= 5   stale reads possible")
    print("  W=3, R=3   -> 6 > 5    always fresh")
    print("  W=5, R=1   -> 6 > 5    always fresh (write-heavy cost)")
    print("  W=1, R=5   -> 6 > 5    always fresh (read-heavy cost)")
    print("=" * 60)


if __name__ == "__main__":
    main()
