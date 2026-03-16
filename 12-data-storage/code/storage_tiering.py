"""
storage_tiering.py - Hot/Warm/Cold Storage Tiering
===================================================
Demonstrates automatic data migration between storage tiers based on
access patterns. Objects that sit idle get demoted to cheaper tiers.
Accessing a cold object promotes it back to hot. Simulates time
progression to show the full lifecycle.
"""

# ---------------------------------------------------------------------------
# Tier Configuration
# ---------------------------------------------------------------------------

TIERS = {
    "hot":  {"cost_per_gb_month": 0.023, "retrieval_ms": 1,    "label": "HOT  (SSD)"},
    "warm": {"cost_per_gb_month": 0.0125, "retrieval_ms": 10,  "label": "WARM (HDD)"},
    "cold": {"cost_per_gb_month": 0.004, "retrieval_ms": 5000, "label": "COLD (Archive)"},
}

DEMOTE_TO_WARM_AFTER = 30
DEMOTE_TO_COLD_AFTER = 90

# ---------------------------------------------------------------------------
# Tiered Storage Engine
# ---------------------------------------------------------------------------

class TieredStorage:
    """Manages objects across hot, warm, and cold tiers. Tracks access
    timestamps and applies lifecycle rules to move data automatically."""

    def __init__(self):
        self.objects = {}
        self.simulated_now = 0

    def put(self, key, data):
        self.objects[key] = {
            "data": data, "size_bytes": len(data), "tier": "hot",
            "created_day": self.simulated_now, "last_accessed_day": self.simulated_now,
            "access_count": 0,
        }

    def get(self, key):
        obj = self.objects[key]
        latency = TIERS[obj["tier"]]["retrieval_ms"]
        obj["last_accessed_day"] = self.simulated_now
        obj["access_count"] += 1
        old_tier = obj["tier"]
        if old_tier != "hot":
            obj["tier"] = "hot"
            print(f"  PROMOTE '{key}': {old_tier} -> hot (accessed)")
        return obj["data"], latency

    def apply_lifecycle_rules(self):
        transitions = []
        for key, obj in self.objects.items():
            idle = self.simulated_now - obj["last_accessed_day"]
            old = obj["tier"]
            if idle >= DEMOTE_TO_COLD_AFTER and old != "cold":
                obj["tier"] = "cold"
            elif idle >= DEMOTE_TO_WARM_AFTER and old == "hot":
                obj["tier"] = "warm"
            if obj["tier"] != old:
                transitions.append((key, old, obj["tier"], idle))
        return transitions

    def advance_time(self, days):
        self.simulated_now += days

    def storage_report(self):
        tier_usage = {"hot": 0, "warm": 0, "cold": 0}
        for obj in self.objects.values():
            tier_usage[obj["tier"]] += obj["size_bytes"]
        total_cost = 0.0
        lines = []
        for name, byte_count in tier_usage.items():
            gb = byte_count / (1024 ** 3)
            cost = gb * TIERS[name]["cost_per_gb_month"]
            total_cost += cost
            count = sum(1 for o in self.objects.values() if o["tier"] == name)
            lines.append(f"  {TIERS[name]['label']:20s} | {count:3d} objects | ${cost:.6f}/mo")
        return lines, total_cost

    def summary(self, key):
        o = self.objects[key]
        return f"  '{key}': tier={o['tier']}, accesses={o['access_count']}, idle={self.simulated_now - o['last_accessed_day']}d"

# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

def run_simulation():
    print("=" * 65)
    print("Storage Tiering Simulation")
    print("=" * 65)

    store = TieredStorage()
    files = {
        "user/profile.json":   b'{"name": "Alice"}' * 100,
        "logs/2024-01-01.log": b"INFO request handled\n" * 500,
        "photos/vacation.jpg": b"\xff\xd8\xff" * 2000,
        "reports/q1-2024.pdf": b"%PDF-1.4 ..." * 1000,
        "backups/db-dump.sql": b"INSERT INTO users" * 3000,
    }

    print("\n--- Day 0: Ingesting 5 objects ---")
    for key, data in files.items():
        store.put(key, data)
        print(f"  Stored '{key}' ({len(data)} bytes) -> hot tier")

    print("\n--- Day 5: Accessing profile and photos ---")
    store.advance_time(5)
    store.get("user/profile.json")
    store.get("photos/vacation.jpg")

    for day, label in [(35, "Day 35"), (65, "Day 65"), (95, "Day 95")]:
        store.advance_time(day - store.simulated_now)
        print(f"\n--- {label}: Running lifecycle rules ---")
        for key, old, new, idle in store.apply_lifecycle_rules():
            print(f"  DEMOTE '{key}': {old} -> {new} (idle {idle} days)")

    print("\nCurrent state:")
    for key in files:
        print(store.summary(key))

    print("\n--- Day 95: Accessing cold backup ---")
    data, latency_ms = store.get("backups/db-dump.sql")
    print(f"  Retrieved {len(data)} bytes (simulated latency: {latency_ms}ms)")

    print("\n--- Storage Cost Report ---")
    lines, total_cost = store.storage_report()
    for line in lines:
        print(line)
    all_hot_gb = sum(len(d) for d in files.values()) / (1024 ** 3)
    all_hot_cost = all_hot_gb * TIERS["hot"]["cost_per_gb_month"]
    savings = ((all_hot_cost - total_cost) / all_hot_cost * 100) if all_hot_cost > 0 else 0
    print(f"\n  Tiered cost:   ${total_cost:.6f}/mo")
    print(f"  All-hot cost:  ${all_hot_cost:.6f}/mo")
    print(f"  Savings:       {savings:.1f}%")

    print("\n" + "-" * 65)
    print("Tiering cuts costs by moving idle data to cheaper storage.")
    print("In production, S3 lifecycle policies do this automatically.")
    print("-" * 65)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run_simulation()
