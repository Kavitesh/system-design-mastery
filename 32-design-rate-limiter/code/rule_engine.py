"""
Rule Engine
===========
Configurable rate limit rules with priority-based matching.
Demonstrates how different clients (free tier, enterprise,
anonymous) get different limits based on the most specific
matching rule.

Run: python rule_engine.py
"""

import time

# ---------------------------------------------------------------------------
# Rule definitions - ordered by priority (most specific first)
# ---------------------------------------------------------------------------

RULES = [
    {
        "id": "login-brute-force",
        "match": {"endpoint": "/api/login", "key_type": "ip"},
        "limit": 5,
        "window_seconds": 900,
        "action": "reject",
        "priority": 1,
        "description": "5 login attempts per 15 min per IP",
    },
    {
        "id": "upload-per-user",
        "match": {"endpoint": "/api/upload", "key_type": "user"},
        "limit": 10,
        "window_seconds": 60,
        "action": "reject",
        "priority": 2,
        "description": "10 uploads per minute per user",
    },
    {
        "id": "enterprise-tier",
        "match": {"plan": "enterprise", "key_type": "api_key"},
        "limit": 50000,
        "window_seconds": 3600,
        "action": "log_and_allow",
        "priority": 3,
        "description": "50K/hr enterprise soft limit - log but don't block",
    },
    {
        "id": "pro-tier",
        "match": {"plan": "pro", "key_type": "api_key"},
        "limit": 5000,
        "window_seconds": 3600,
        "action": "reject",
        "priority": 4,
        "description": "5K/hr for pro tier",
    },
    {
        "id": "free-tier",
        "match": {"plan": "free", "key_type": "api_key"},
        "limit": 100,
        "window_seconds": 3600,
        "action": "reject",
        "priority": 5,
        "description": "100/hr for free tier",
    },
    {
        "id": "global-default",
        "match": {"scope": "global"},
        "limit": 1000,
        "window_seconds": 60,
        "action": "reject",
        "priority": 99,
        "description": "1000/min global fallback",
    },
]


# ---------------------------------------------------------------------------
# Rule matching logic
# ---------------------------------------------------------------------------

class RuleEngine:
    def __init__(self, rules: list):
        self.rules = sorted(rules, key=lambda r: r["priority"])

    def _matches(self, rule: dict, context: dict) -> bool:
        match_criteria = rule["match"]
        if "scope" in match_criteria and match_criteria["scope"] == "global":
            return True
        for key, value in match_criteria.items():
            if context.get(key) != value:
                return False
        return True

    def find_rule(self, context: dict) -> dict | None:
        for rule in self.rules:
            if self._matches(rule, context):
                return rule
        return None

    def evaluate(self, context: dict, current_count: int) -> dict:
        rule = self.find_rule(context)
        if not rule:
            return {"allowed": True, "rule": None, "reason": "no matching rule"}

        if current_count < rule["limit"]:
            return {
                "allowed": True,
                "rule": rule["id"],
                "remaining": rule["limit"] - current_count - 1,
                "limit": rule["limit"],
                "window": rule["window_seconds"],
            }

        if rule["action"] == "log_and_allow":
            return {
                "allowed": True,
                "rule": rule["id"],
                "remaining": 0,
                "limit": rule["limit"],
                "window": rule["window_seconds"],
                "soft_limit_exceeded": True,
                "reason": f"soft limit exceeded - {rule['description']}",
            }

        return {
            "allowed": False,
            "rule": rule["id"],
            "remaining": 0,
            "limit": rule["limit"],
            "window": rule["window_seconds"],
            "reason": f"hard limit hit - {rule['description']}",
        }


# ---------------------------------------------------------------------------
# Demo scenarios
# ---------------------------------------------------------------------------

def run_demo():
    engine = RuleEngine(RULES)

    scenarios = [
        {
            "name": "Anonymous user hitting login",
            "context": {"endpoint": "/api/login", "key_type": "ip"},
            "counts": [0, 3, 4, 5, 6],
        },
        {
            "name": "Free tier user on general endpoint",
            "context": {"endpoint": "/api/data", "key_type": "api_key", "plan": "free"},
            "counts": [0, 50, 99, 100, 150],
        },
        {
            "name": "Enterprise user over soft limit",
            "context": {"endpoint": "/api/data", "key_type": "api_key", "plan": "enterprise"},
            "counts": [0, 49999, 50000, 60000],
        },
        {
            "name": "Pro user uploading files",
            "context": {"endpoint": "/api/upload", "key_type": "user", "plan": "pro"},
            "counts": [0, 5, 9, 10, 15],
        },
        {
            "name": "Unknown client - falls to global default",
            "context": {"endpoint": "/api/search", "key_type": "session"},
            "counts": [0, 500, 999, 1000],
        },
    ]

    print("=" * 70)
    print("RATE LIMIT RULE ENGINE DEMO")
    print("=" * 70)

    for scenario in scenarios:
        print(f"\n{'- ' * 35}")
        print(f"Scenario: {scenario['name']}")
        print(f"Context:  {scenario['context']}")

        matched = engine.find_rule(scenario["context"])
        if matched:
            print(f"Matched:  [{matched['id']}] {matched['description']}")
        print()

        print(f"  {'Count':>8}  {'Allowed':>8}  {'Remaining':>10}  {'Details'}")
        print(f"  {'-'*8}  {'-'*8}  {'-'*10}  {'-'*30}")

        for count in scenario["counts"]:
            result = engine.evaluate(scenario["context"], count)
            allowed = "YES" if result["allowed"] else "NO"
            remaining = result.get("remaining", "-")
            details = ""
            if result.get("soft_limit_exceeded"):
                details = "SOFT LIMIT - logged, not blocked"
            elif not result["allowed"]:
                details = f"REJECTED - {result.get('reason', '')}"
            print(f"  {count:>8}  {allowed:>8}  {remaining:>10}  {details}")

    print(f"\n{'=' * 70}")
    print("KEY INSIGHT: Most specific rule wins. Enterprise gets soft limits.")
    print("Upload endpoint triggers per-user rule even for pro-tier users.")
    print(f"{'=' * 70}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run_demo()
