"""
SLA / Uptime Calculator
========================
Calculates what each level of availability nines actually means in
real downtime - per year, month, week, and day. Also shows composite
system availability when multiple components are chained together,
and estimates the cost of downtime at different revenue levels.

Run: python sla_calculator.py
"""

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Time constants
# ---------------------------------------------------------------------------

SECONDS_PER_MINUTE = 60
SECONDS_PER_HOUR = 3600
SECONDS_PER_DAY = 86400
SECONDS_PER_WEEK = 604800
SECONDS_PER_MONTH = 2592000   # 30 days
SECONDS_PER_YEAR = 31536000   # 365 days


# ---------------------------------------------------------------------------
# Downtime formatter
# ---------------------------------------------------------------------------

def format_downtime(seconds: float) -> str:
    if seconds >= SECONDS_PER_DAY:
        days = seconds / SECONDS_PER_DAY
        return f"{days:.2f} days"
    elif seconds >= SECONDS_PER_HOUR:
        hours = seconds / SECONDS_PER_HOUR
        return f"{hours:.2f} hours"
    elif seconds >= SECONDS_PER_MINUTE:
        minutes = seconds / SECONDS_PER_MINUTE
        return f"{minutes:.2f} minutes"
    else:
        return f"{seconds:.2f} seconds"


# ---------------------------------------------------------------------------
# SLA calculator
# ---------------------------------------------------------------------------

@dataclass
class SLALevel:
    name: str
    nines: float
    percentage: float

    @property
    def downtime_per_year(self) -> float:
        return SECONDS_PER_YEAR * (1 - self.percentage / 100)

    @property
    def downtime_per_month(self) -> float:
        return SECONDS_PER_MONTH * (1 - self.percentage / 100)

    @property
    def downtime_per_week(self) -> float:
        return SECONDS_PER_WEEK * (1 - self.percentage / 100)

    @property
    def downtime_per_day(self) -> float:
        return SECONDS_PER_DAY * (1 - self.percentage / 100)


STANDARD_LEVELS = [
    SLALevel("one nine", 1, 90.0),
    SLALevel("two nines", 2, 99.0),
    SLALevel("three nines", 3, 99.9),
    SLALevel("three and a half", 3.5, 99.95),
    SLALevel("four nines", 4, 99.99),
    SLALevel("five nines", 5, 99.999),
    SLALevel("six nines", 6, 99.9999),
]


def print_availability_table():
    print("AVAILABILITY LEVELS - WHAT THE NINES ACTUALLY MEAN")
    print("=" * 85)
    header = f"{'Level':<18} {'Uptime %':<12} {'Down/Year':<16} {'Down/Month':<16} {'Down/Week':<14}"
    print(header)
    print("-" * 85)
    for level in STANDARD_LEVELS:
        print(f"{level.name:<18} {level.percentage:<12} "
              f"{format_downtime(level.downtime_per_year):<16} "
              f"{format_downtime(level.downtime_per_month):<16} "
              f"{format_downtime(level.downtime_per_week):<14}")
    print("=" * 85)


# ---------------------------------------------------------------------------
# Composite availability
# ---------------------------------------------------------------------------

def serial_availability(components: list[tuple[str, float]]) -> float:
    result = 1.0
    for _, avail in components:
        result *= avail / 100
    return result * 100


def parallel_availability(components: list[tuple[str, float]]) -> float:
    unavail = 1.0
    for _, avail in components:
        unavail *= (1 - avail / 100)
    return (1 - unavail) * 100


def print_composite_demo():
    print("\nCOMPOSITE SYSTEM AVAILABILITY")
    print("=" * 70)

    serial_components = [
        ("Load Balancer", 99.99),
        ("Web Server", 99.9),
        ("App Server", 99.9),
        ("Database", 99.9),
    ]

    print("\nScenario 1: Serial chain (all must work)")
    print("-" * 70)
    print("  Request -> Load Balancer -> Web -> App -> Database")
    print()
    for name, avail in serial_components:
        down = SECONDS_PER_YEAR * (1 - avail / 100)
        print(f"  {name:<20} {avail}% uptime  ({format_downtime(down)}/year)")

    total_serial = serial_availability(serial_components)
    total_down = SECONDS_PER_YEAR * (1 - total_serial / 100)
    print(f"\n  Combined: {total_serial:.4f}% uptime ({format_downtime(total_down)}/year)")
    print(f"  Each component is three nines, but the chain is worse than two nines.")

    # Parallel redundancy
    print(f"\nScenario 2: Parallel redundancy (any one works)")
    print("-" * 70)

    for count in [2, 3, 4]:
        components = [(f"Server {i+1}", 99.9) for i in range(count)]
        combined = parallel_availability(components)
        down = SECONDS_PER_YEAR * (1 - combined / 100)
        nines = 0
        temp = 100 - combined
        while temp < 1 and temp > 0:
            nines += 1
            temp *= 10
        print(f"  {count}x servers at 99.9% each -> {combined:.6f}% ({format_downtime(down)}/year)")

    # Real architecture
    print(f"\nScenario 3: Realistic architecture")
    print("-" * 70)
    print("  2x Load Balancers (active-active) -> 3x App Servers -> 2x DB (primary-standby)")
    print()

    lb_avail = parallel_availability([("LB1", 99.99), ("LB2", 99.99)])
    app_avail = parallel_availability([("App1", 99.9), ("App2", 99.9), ("App3", 99.9)])
    db_avail = parallel_availability([("DB1", 99.9), ("DB2", 99.9)])

    print(f"  Load Balancer tier:  {lb_avail:.6f}%")
    print(f"  App Server tier:     {app_avail:.6f}%")
    print(f"  Database tier:       {db_avail:.6f}%")

    system_avail = serial_availability([
        ("LB tier", lb_avail),
        ("App tier", app_avail),
        ("DB tier", db_avail),
    ])
    system_down = SECONDS_PER_YEAR * (1 - system_avail / 100)
    print(f"\n  System availability: {system_avail:.6f}% ({format_downtime(system_down)}/year)")
    print(f"  Redundancy at each tier turns three-nines components into a four-nines system.")
    print("=" * 70)


# ---------------------------------------------------------------------------
# Cost of downtime
# ---------------------------------------------------------------------------

def print_cost_analysis():
    print("\nCOST OF DOWNTIME")
    print("=" * 70)
    print(f"{'Revenue/Hour':<16} {'99.9% cost/yr':<18} {'99.99% cost/yr':<18} {'99.999% cost/yr'}")
    print("-" * 70)

    revenues = [1_000, 10_000, 100_000, 1_000_000]
    targets = [99.9, 99.99, 99.999]

    for rev in revenues:
        costs = []
        for target in targets:
            downtime_hours = (SECONDS_PER_YEAR * (1 - target / 100)) / 3600
            cost = downtime_hours * rev
            costs.append(f"${cost:,.0f}")
        print(f"${rev:>12,}/hr  {costs[0]:<18} {costs[1]:<18} {costs[2]}")

    print("-" * 70)
    print("At $100K/hr revenue, the gap between three nines and four nines is")
    down_3 = (SECONDS_PER_YEAR * 0.001) / 3600
    down_4 = (SECONDS_PER_YEAR * 0.0001) / 3600
    savings = (down_3 - down_4) * 100_000
    print(f"  {down_3 - down_4:.1f} fewer hours of downtime = ${savings:,.0f}/year in saved revenue.")
    print(f"  That's your budget for redundancy and failover infrastructure.")
    print("=" * 70)


# ---------------------------------------------------------------------------
# Error budget
# ---------------------------------------------------------------------------

def print_error_budget():
    print("\nERROR BUDGET")
    print("=" * 70)
    print("An error budget is the inverse of your SLO - it's how much failure")
    print("you can afford before breaching your target.\n")

    slo = 99.9
    budget_seconds = SECONDS_PER_MONTH * (1 - slo / 100)
    incidents = [
        ("Deploy caused 2min of 500s", 120),
        ("DB failover took 45s", 45),
        ("Network blip, 30s of errors", 30),
        ("Bad config pushed, 5min outage", 300),
    ]

    print(f"SLO: {slo}% monthly -> Error budget: {format_downtime(budget_seconds)}")
    print(f"\nIncidents this month:")
    print(f"{'Incident':<42} {'Duration':<12} {'Budget Used'}")
    print("-" * 70)

    total_used = 0
    for desc, duration in incidents:
        total_used += duration
        pct = (total_used / budget_seconds) * 100
        bar = "#" * int(pct / 2) + "-" * (50 - int(pct / 2))
        print(f"  {desc:<40} {format_downtime(duration):<12} {pct:.1f}%")

    remaining = budget_seconds - total_used
    print(f"\n  Budget remaining: {format_downtime(remaining)} "
          f"({(remaining/budget_seconds)*100:.1f}%)")
    if remaining < budget_seconds * 0.2:
        print(f"  WARNING: Less than 20% budget remaining - freeze risky deployments!")
    print("=" * 70)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("SLA / Uptime Calculator")
    print()
    print_availability_table()
    print_composite_demo()
    print_cost_analysis()
    print_error_budget()
    print("\nKey takeaway: each nine is 10x harder. Most apps should target three nines.")
    print("Four nines is worth it when downtime directly costs real money per minute.")
