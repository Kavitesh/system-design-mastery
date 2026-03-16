"""
RPO/RTO Calculator
===================
Interactive calculator that shows RPO/RTO tradeoffs for different DR strategies.
Estimates costs, recovery characteristics, and helps teams pick the right strategy
based on their actual requirements.
"""

import argparse
import sys

# ---------------------------------------------------------------------------
# DR strategy definitions
# ---------------------------------------------------------------------------

STRATEGIES = {
    "backup-restore": {
        "name": "Backup & Restore",
        "rpo_hours": 24.0,
        "rto_hours": 24.0,
        "monthly_cost_per_gb": 0.023,
        "infra_multiplier": 0.05,
        "description": "Periodic backups to offsite storage. Rebuild infrastructure from scratch on failure.",
    },
    "pilot-light": {
        "name": "Pilot Light",
        "rpo_hours": 1.0,
        "rto_hours": 1.0,
        "monthly_cost_per_gb": 0.10,
        "infra_multiplier": 0.15,
        "description": "Core database replicas running in DR region. Compute spun up on demand.",
    },
    "warm-standby": {
        "name": "Warm Standby",
        "rpo_hours": 0.25,
        "rto_hours": 0.5,
        "monthly_cost_per_gb": 0.10,
        "infra_multiplier": 0.40,
        "description": "Scaled-down but complete environment in DR region, ready to scale up.",
    },
    "hot-standby": {
        "name": "Hot Standby (Active-Passive)",
        "rpo_hours": 0.02,
        "rto_hours": 0.08,
        "monthly_cost_per_gb": 0.10,
        "infra_multiplier": 0.90,
        "description": "Full-scale DR environment. Automated failover in minutes.",
    },
    "active-active": {
        "name": "Multi-Site Active-Active",
        "rpo_hours": 0.0,
        "rto_hours": 0.0,
        "monthly_cost_per_gb": 0.15,
        "infra_multiplier": 1.50,
        "description": "Multiple regions serving traffic simultaneously. Near-zero downtime.",
    },
}

# ---------------------------------------------------------------------------
# Cost calculator
# ---------------------------------------------------------------------------

def calculate_costs(strategy: dict, data_size_gb: float, base_monthly_infra: float) -> dict:
    storage_cost = data_size_gb * strategy["monthly_cost_per_gb"]
    infra_cost = base_monthly_infra * strategy["infra_multiplier"]
    total_monthly = storage_cost + infra_cost

    return {
        "storage_monthly": storage_cost,
        "infra_monthly": infra_cost,
        "total_monthly": total_monthly,
        "total_annual": total_monthly * 12,
    }


def calculate_downtime_cost(rto_hours: float, revenue_per_hour: float) -> float:
    return rto_hours * revenue_per_hour


def format_time(hours: float) -> str:
    if hours == 0:
        return "Near-zero"
    if hours < 1/60:
        return f"{hours * 3600:.0f} seconds"
    if hours < 1:
        return f"{hours * 60:.0f} minutes"
    if hours < 24:
        return f"{hours:.1f} hours"
    return f"{hours / 24:.1f} days"


# ---------------------------------------------------------------------------
# Analysis output
# ---------------------------------------------------------------------------

def analyze_single(key: str, data_size_gb: float, base_infra: float, revenue_per_hour: float):
    s = STRATEGIES[key]
    costs = calculate_costs(s, data_size_gb, base_infra)
    downtime_cost = calculate_downtime_cost(s["rto_hours"], revenue_per_hour)

    print(f"Strategy: {s['name']}")
    print(f"  {s['description']}")
    print()
    print(f"  RPO: {format_time(s['rpo_hours']):>20}  (max data loss per incident)")
    print(f"  RTO: {format_time(s['rto_hours']):>20}  (max downtime per incident)")
    print()
    print(f"  DR storage cost:    ${costs['storage_monthly']:>10,.2f}/month")
    print(f"  DR infra cost:      ${costs['infra_monthly']:>10,.2f}/month")
    print(f"  Total DR cost:      ${costs['total_monthly']:>10,.2f}/month  (${costs['total_annual']:>,.2f}/year)")
    print(f"  Downtime cost:      ${downtime_cost:>10,.2f}/incident")
    print()

    if downtime_cost > 0 and costs["total_annual"] > 0:
        incidents_to_justify = costs["total_annual"] / downtime_cost
        print(f"  Break-even: {incidents_to_justify:.1f} incidents/year to justify DR spend")
    print()


def compare_all(data_size_gb: float, base_infra: float, revenue_per_hour: float):
    print(f"Inputs: {data_size_gb:.0f} GB data, ${base_infra:,.0f}/month base infra, ${revenue_per_hour:,.0f}/hour revenue")
    print()

    header = f"{'Strategy':<30} {'RPO':>12} {'RTO':>12} {'DR $/month':>12} {'Downtime $/inc':>16}"
    print(header)
    print("=" * len(header))

    for key, s in STRATEGIES.items():
        costs = calculate_costs(s, data_size_gb, base_infra)
        downtime_cost = calculate_downtime_cost(s["rto_hours"], revenue_per_hour)
        print(
            f"{s['name']:<30} "
            f"{format_time(s['rpo_hours']):>12} "
            f"{format_time(s['rto_hours']):>12} "
            f"${costs['total_monthly']:>10,.0f} "
            f"${downtime_cost:>14,.0f}"
        )

    print()
    print("--- Cost vs. Risk Analysis ---")
    print()

    best_value = None
    best_ratio = float("inf")

    for key, s in STRATEGIES.items():
        costs = calculate_costs(s, data_size_gb, base_infra)
        downtime_cost = calculate_downtime_cost(s["rto_hours"], revenue_per_hour)

        if downtime_cost == 0:
            risk_score = 0
        else:
            risk_score = (s["rpo_hours"] + s["rto_hours"]) * revenue_per_hour

        if costs["total_monthly"] > 0 and risk_score > 0:
            ratio = costs["total_annual"] / risk_score
            if ratio < best_ratio:
                best_ratio = ratio
                best_value = s["name"]
            print(f"  {s['name']:<30} Annual DR cost / risk score = {ratio:.1f}")
        elif risk_score == 0:
            print(f"  {s['name']:<30} Zero risk (highest cost)")

    if best_value:
        print()
        print(f"  Best cost/risk ratio: {best_value}")

    print()
    recommend(data_size_gb, revenue_per_hour)


def recommend(data_size_gb: float, revenue_per_hour: float):
    print("--- Recommendation ---")
    annual_revenue = revenue_per_hour * 8760

    if revenue_per_hour > 50000:
        pick = "active-active"
    elif revenue_per_hour > 10000:
        pick = "hot-standby"
    elif revenue_per_hour > 1000:
        pick = "warm-standby"
    elif revenue_per_hour > 100:
        pick = "pilot-light"
    else:
        pick = "backup-restore"

    s = STRATEGIES[pick]
    print(f"  At ${revenue_per_hour:,.0f}/hour revenue, consider: {s['name']}")
    print(f"  RPO: {format_time(s['rpo_hours'])}, RTO: {format_time(s['rto_hours'])}")
    print()
    print("  This is a starting point. Adjust based on regulatory requirements,")
    print("  compliance mandates, and how your customers actually react to downtime.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="RPO/RTO Calculator for DR strategies")
    parser.add_argument("--strategy", choices=list(STRATEGIES.keys()), help="Analyze a single strategy")
    parser.add_argument("--data-size", type=float, default=100, help="Data size in GB (default: 100)")
    parser.add_argument("--base-infra", type=float, default=5000, help="Monthly infra cost in USD (default: 5000)")
    parser.add_argument("--revenue-per-hour", type=float, default=5000, help="Revenue per hour in USD (default: 5000)")
    args = parser.parse_args()

    print("RPO/RTO Calculator")
    print()

    if args.strategy:
        analyze_single(args.strategy, args.data_size, args.base_infra, args.revenue_per_hour)
    else:
        compare_all(args.data_size, args.base_infra, args.revenue_per_hour)


if __name__ == "__main__":
    main()
