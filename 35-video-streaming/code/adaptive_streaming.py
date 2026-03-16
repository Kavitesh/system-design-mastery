"""
Adaptive Bitrate Streaming Simulator
======================================
Simulates a video player's ABR algorithm as bandwidth fluctuates.
Shows quality selection, buffer management, and rebuffering events.

Run:  python adaptive_streaming.py
"""

import random, time

# ---------------------------------------------------------------------------

LEVELS = [
    {"name": "360p",  "kbps": 500},
    {"name": "480p",  "kbps": 1000},
    {"name": "720p",  "kbps": 2500},
    {"name": "1080p", "kbps": 4500},
    {"name": "1440p", "kbps": 8000},
    {"name": "4K",    "kbps": 16000},
]

SEG_SEC = 4
BUF_MAX = 40
SAFETY = 0.85

PROFILES = {
    "stable_wifi": {"desc": "Stable home Wi-Fi", "base": 25000, "var": 0.1, "drops": []},
    "commute":     {"desc": "Mobile on a train",  "base": 5000,  "var": 0.6,
                    "drops": [(20,25,200), (45,48,500)]},
    "congested":   {"desc": "Evening ISP congestion", "base": 12000, "var": 0.3,
                    "drops": [], "ramp": (30,50,0.3)},
}

def get_bw(prof, t):
    for s, e, bw in prof.get("drops", []):
        if s <= t <= e: return bw + random.uniform(-50, 50)
    base = prof["base"]
    ramp = prof.get("ramp")
    if ramp:
        rs, re, rf = ramp
        if rs <= t <= re: base *= 1 - ((t-rs)/(re-rs)) * (1-rf)
    return max(100, base * random.uniform(1-prof["var"], 1+prof["var"]))

# ---------------------------------------------------------------------------

class Player:
    def __init__(self):
        self.idx = 0
        self.buf = 0.0
        self.bw_est = 5000
        self.switches = 0
        self.rebuffers = 0
        self.history = []

    def pick(self):
        usable = self.bw_est * SAFETY
        best = 0
        for i, lv in enumerate(LEVELS):
            if lv["kbps"] <= usable: best = i
        if self.buf < 8:  best = min(best, self.idx)
        if self.buf < 5:  best = max(0, best - 1)
        if self.buf > 30: best = min(best + 1, len(LEVELS) - 1)
        if best != self.idx: self.switches += 1
        self.idx = best
        return LEVELS[best]

    def download(self, bw):
        lv = self.pick()
        dl_time = (lv["kbps"] * SEG_SEC) / bw
        self.buf -= dl_time
        rebuf = self.buf < 0
        if rebuf: self.rebuffers += 1; self.buf = 0
        self.buf = min(self.buf + SEG_SEC, BUF_MAX)
        self.bw_est = 0.3 * bw + 0.7 * self.bw_est
        self.history.append(lv["name"])
        return lv, rebuf

# ---------------------------------------------------------------------------

def simulate(name, duration=60):
    prof = PROFILES[name]
    player = Player()
    print(f"\n{'='*72}")
    print(f"ABR SIMULATION: {prof['desc']}")
    print(f"{'='*72}")
    print(f"Duration: {duration}s  |  Base BW: {prof['base']:,} kbps  |  Levels: {len(LEVELS)}\n")
    print(f"{'Seg':>4} {'Time':>5} {'Quality':>6} {'Bitrate':>7} {'BW':>7} {'Est':>7} {'Buffer':>16} {'Status'}")
    print("-" * 72)

    seg, total_bits = 0, 0
    for t in range(0, duration, SEG_SEC):
        bw = get_bw(prof, t)
        lv, rebuf = player.download(bw)
        seg += 1; total_bits += lv["kbps"] * SEG_SEC
        bar_n = int(player.buf / BUF_MAX * 15)
        bar = "#" * bar_n + "." * (15 - bar_n)
        m, s = divmod(t + SEG_SEC, 60)
        status = "REBUFFER" if rebuf else ("low buf" if player.buf < 5 else "")
        print(f"{seg:4d} {m}:{s:02d} {lv['name']:>6s} {lv['kbps']:>5d}kb {bw:>5.0f}kb "
              f"{player.bw_est:>5.0f}kb [{bar}] {status}")
        time.sleep(0.03)

    print(f"\n{'='*72}")
    print("SUMMARY")
    print(f"  Segments: {seg}  |  Switches: {player.switches}  |  Rebuffers: {player.rebuffers}")
    print(f"  Avg bitrate: {total_bits/duration:,.0f} kbps  |  Data: {total_bits/8/1024:.1f} MB")
    counts = {lv["name"]: 0 for lv in LEVELS}
    for q in player.history: counts[q] += 1
    print(f"\n  Quality distribution:")
    for lv in LEVELS:
        c = counts[lv["name"]]; pct = c/seg*100
        print(f"    {lv['name']:>6s}: {c:3d} ({pct:4.1f}%)  {'#'*int(pct/2)}")

    qoe = max(0, min(100, 100 - player.rebuffers*15 - player.switches*2 +
              sum(i for i,lv in enumerate(LEVELS) if counts[lv["name"]]>0)*3))
    verdict = "Smooth" if qoe >= 80 else "Acceptable" if qoe >= 50 else "Poor"
    print(f"\n  QoE: {qoe}/100 - {verdict}")

# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Adaptive bitrate streaming simulator starting")
    for p in PROFILES:
        simulate(p)
