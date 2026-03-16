"""
SLO-Based Alerting System
===========================
Implements error budget tracking and burn rate alerting.
Compares burn rate alerts against static threshold alerts to show
why SLO-based alerting catches real incidents without false positives.

Run: python alerting_system.py
"""

import time
import random
from collections import deque
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# SLO and error budget
# ---------------------------------------------------------------------------

@dataclass
class SLO:
    name: str
    target: float
    window_seconds: int

    @property
    def error_budget_fraction(self):
        return 1.0 - self.target

    @property
    def error_budget_display(self):
        return f"{self.error_budget_fraction * 100:.2f}%"


@dataclass
class RequestOutcome:
    timestamp: float
    success: bool


# ---------------------------------------------------------------------------
# Error budget tracker
# ---------------------------------------------------------------------------

class ErrorBudgetTracker:
    def __init__(self, slo: SLO):
        self.slo = slo
        self.outcomes: deque = deque()
        self.alerts_fired: list = field(default_factory=list) if False else []

    def record(self, success: bool):
        now = time.time()
        self.outcomes.append(RequestOutcome(now, success))
        self._prune_old(now)

    def _prune_old(self, now):
        cutoff = now - self.slo.window_seconds
        while self.outcomes and self.outcomes[0].timestamp < cutoff:
            self.outcomes.popleft()

    def current_error_rate(self):
        if not self.outcomes:
            return 0.0
        failures = sum(1 for o in self.outcomes if not o.success)
        return failures / len(self.outcomes)

    def budget_remaining(self):
        consumed = self.current_error_rate() / self.slo.error_budget_fraction
        return max(0.0, 1.0 - consumed)

    def burn_rate(self):
        error_rate = self.current_error_rate()
        if self.slo.error_budget_fraction == 0:
            return float('inf') if error_rate > 0 else 0
        return error_rate / self.slo.error_budget_fraction


# ---------------------------------------------------------------------------
# Alerting rules
# ---------------------------------------------------------------------------

@dataclass
class Alert:
    name: str
    severity: str
    message: str
    burn_rate: float
    budget_remaining: float
    tick: int


class BurnRateAlerter:
    """Multi-window burn rate alerting (Google SRE style)."""

    RULES = [
        {"name": "critical_fast", "burn_rate": 14.4, "severity": "PAGE",
         "message": "Budget exhausted in <1 hour at current rate"},
        {"name": "critical_slow", "burn_rate": 6.0, "severity": "PAGE",
         "message": "Budget exhausted in <6 hours at current rate"},
        {"name": "warning", "burn_rate": 3.0, "severity": "TICKET",
         "message": "Budget exhausted in <3 days at current rate"},
        {"name": "slow_burn", "burn_rate": 1.0, "severity": "LOG",
         "message": "Consuming budget faster than expected"},
    ]

    def evaluate(self, tracker, tick):
        br = tracker.burn_rate()
        remaining = tracker.budget_remaining()
        alerts = []

        for rule in self.RULES:
            if br >= rule["burn_rate"]:
                alerts.append(Alert(
                    name=rule["name"],
                    severity=rule["severity"],
                    message=rule["message"],
                    burn_rate=br,
                    budget_remaining=remaining,
                    tick=tick
                ))
                break

        return alerts


class StaticThresholdAlerter:
    """Traditional static threshold alerting for comparison."""

    def evaluate(self, tracker, tick):
        error_rate = tracker.current_error_rate()
        alerts = []

        if error_rate > 0.05:
            alerts.append(Alert(
                name="static_error_rate",
                severity="PAGE",
                message=f"Error rate {error_rate:.1%} exceeds 5% threshold",
                burn_rate=tracker.burn_rate(),
                budget_remaining=tracker.budget_remaining(),
                tick=tick
            ))

        return alerts


# ---------------------------------------------------------------------------
# Traffic simulation scenarios
# ---------------------------------------------------------------------------

def generate_traffic_scenarios():
    """Returns a list of (phase_name, num_ticks, error_probability) tuples."""
    return [
        ("Normal traffic", 30, 0.001),
        ("Minor hiccup (self-resolving)", 5, 0.03),
        ("Back to normal", 15, 0.001),
        ("Gradual degradation starts", 10, 0.008),
        ("Degradation worsens", 10, 0.02),
        ("Major incident", 10, 0.12),
        ("Incident mitigated", 5, 0.04),
        ("Recovery", 15, 0.001),
    ]


def simulate_tick(error_probability, requests_per_tick=50):
    results = []
    for _ in range(requests_per_tick):
        results.append(random.random() > error_probability)
    return results


# ---------------------------------------------------------------------------
# Run the simulation
# ---------------------------------------------------------------------------

def main():
    print("SLO-Based Alerting - burn rate vs static thresholds")
    print("=" * 70)

    slo = SLO(name="api-availability", target=0.999, window_seconds=3600)
    tracker = ErrorBudgetTracker(slo)
    burn_alerter = BurnRateAlerter()
    static_alerter = StaticThresholdAlerter()

    print(f"\n  SLO: {slo.target:.1%} availability over {slo.window_seconds}s window")
    print(f"  Error budget: {slo.error_budget_display} ({slo.error_budget_fraction * 3600:.1f}s of errors per hour)")
    print(f"  Burn rate 1.0 = consuming budget at exactly the sustainable rate")
    print()

    scenarios = generate_traffic_scenarios()
    tick = 0
    burn_alerts_total = []
    static_alerts_total = []

    for phase_name, num_ticks, error_prob in scenarios:
        print(f"\n{'='*70}")
        print(f"PHASE: {phase_name} (error_prob={error_prob:.1%})")
        print(f"{'='*70}")

        for i in range(num_ticks):
            tick += 1
            outcomes = simulate_tick(error_prob)
            for success in outcomes:
                tracker.record(success)

            br = tracker.burn_rate()
            remaining = tracker.budget_remaining()
            error_rate = tracker.current_error_rate()

            burn_alerts = burn_alerter.evaluate(tracker, tick)
            static_alerts = static_alerter.evaluate(tracker, tick)
            burn_alerts_total.extend(burn_alerts)
            static_alerts_total.extend(static_alerts)

            budget_bar_len = int(remaining * 30)
            budget_bar = "\033[32m" + "#" * budget_bar_len + "\033[31m" + "-" * (30 - budget_bar_len) + "\033[0m"

            status_parts = [f"tick={tick:>3}", f"err={error_rate:.3%}", f"burn={br:.1f}x",
                           f"budget=[{budget_bar}] {remaining:.0%}"]

            for a in burn_alerts:
                color = "\033[91m" if a.severity == "PAGE" else "\033[33m"
                status_parts.append(f"{color}[{a.severity}] {a.message}\033[0m")

            for a in static_alerts:
                if not burn_alerts:
                    status_parts.append(f"\033[35m[STATIC-{a.severity}] {a.message}\033[0m")

            print("  " + " | ".join(status_parts))

    print(f"\n{'=' * 70}")
    print("ALERTING COMPARISON")
    print(f"{'=' * 70}")

    burn_pages = [a for a in burn_alerts_total if a.severity == "PAGE"]
    burn_tickets = [a for a in burn_alerts_total if a.severity == "TICKET"]
    static_pages = [a for a in static_alerts_total if a.severity == "PAGE"]

    print(f"\n  {'Metric':<35} {'Burn Rate':>12} {'Static':>12}")
    print(f"  {'-'*60}")
    print(f"  {'Total alerts fired':<35} {len(burn_alerts_total):>12} {len(static_alerts_total):>12}")
    print(f"  {'PAGE alerts':<35} {len(burn_pages):>12} {len(static_pages):>12}")
    print(f"  {'TICKET alerts':<35} {len(burn_tickets):>12} {'n/a':>12}")

    burn_page_ticks = set(a.tick for a in burn_pages) if burn_pages else set()
    static_page_ticks = set(a.tick for a in static_pages) if static_pages else set()

    if burn_page_ticks:
        print(f"\n  Burn rate first PAGE at tick {min(burn_page_ticks)}")
    if static_page_ticks:
        print(f"  Static first PAGE at tick {min(static_page_ticks)}")

    print(f"\n  Takeaway: Burn rate alerting pages only during sustained incidents.")
    print(f"  Static thresholds fire during brief spikes that self-resolve,")
    print(f"  causing alert fatigue without adding value.")


if __name__ == "__main__":
    main()
