"""
Notification Preference Manager
=================================
Manages per-user notification preferences including channel opt-in/opt-out,
category controls, quiet hours, and engagement-based throttling.
Transactional notifications bypass all preference checks.

Run the demo:
    python preference_manager.py
"""

from datetime import datetime, timezone, timedelta
import json


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CHANNELS = ("email", "sms", "push")
CATEGORIES = ("transactional", "social", "promotional", "system")
TRANSACTIONAL = "transactional"

ENGAGEMENT_TIERS = {
    "high":   {"min_opens_7d": 5,  "action": "full frequency"},
    "medium": {"min_opens_7d": 1,  "action": "important only"},
    "low":    {"min_opens_7d": 0,  "max_days_silent": 14, "action": "weekly digest"},
    "dead":   {"min_opens_7d": 0,  "max_days_silent": 30, "action": "stop non-transactional"},
}


# ---------------------------------------------------------------------------
# Preference Manager
# ---------------------------------------------------------------------------

class PreferenceManager:
    def __init__(self):
        self._prefs = {}
        self._engagement = {}

    def set_defaults(self, user_id):
        self._prefs[user_id] = {
            "global_enabled": True,
            "quiet_hours": None,
            "channels": {ch: True for ch in CHANNELS},
            "categories": {
                "transactional": {ch: True for ch in CHANNELS},
                "social":        {"email": False, "sms": False, "push": True},
                "promotional":   {"email": True,  "sms": False, "push": False},
                "system":        {"email": True,  "sms": False, "push": True},
            },
        }
        self._engagement[user_id] = {
            "opens_last_7d": 3,
            "last_open": datetime.now(timezone.utc).isoformat(),
        }

    def get_prefs(self, user_id):
        return self._prefs.get(user_id)

    def set_channel(self, user_id, channel, enabled):
        if user_id not in self._prefs:
            return False
        self._prefs[user_id]["channels"][channel] = enabled
        return True

    def set_category_channel(self, user_id, category, channel, enabled):
        if category == TRANSACTIONAL:
            return False
        if user_id not in self._prefs:
            return False
        self._prefs[user_id]["categories"][category][channel] = enabled
        return True

    def set_quiet_hours(self, user_id, start_hour, end_hour, tz_offset_hours=0):
        if user_id not in self._prefs:
            return False
        self._prefs[user_id]["quiet_hours"] = {
            "start": start_hour,
            "end": end_hour,
            "tz_offset": tz_offset_hours,
        }
        return True

    def disable_all(self, user_id):
        if user_id not in self._prefs:
            return False
        self._prefs[user_id]["global_enabled"] = False
        return True

    def should_send(self, user_id, category, channel, send_time=None):
        """Core decision: should this notification be delivered?"""
        if category == TRANSACTIONAL:
            return True, "transactional - always delivered"

        prefs = self._prefs.get(user_id)
        if not prefs:
            return True, "no preferences found - using defaults"

        if not prefs["global_enabled"]:
            return False, "user disabled all notifications"

        if not prefs["channels"].get(channel, False):
            return False, f"user opted out of {channel} channel"

        cat_prefs = prefs["categories"].get(category, {})
        if not cat_prefs.get(channel, False):
            return False, f"user opted out of {category} via {channel}"

        if prefs["quiet_hours"] and send_time:
            qh = prefs["quiet_hours"]
            user_hour = (send_time.hour + qh["tz_offset"]) % 24
            if qh["start"] > qh["end"]:
                in_quiet = user_hour >= qh["start"] or user_hour < qh["end"]
            else:
                in_quiet = qh["start"] <= user_hour < qh["end"]
            if in_quiet:
                return False, f"quiet hours ({qh['start']}:00-{qh['end']}:00 user local)"

        tier = self._get_engagement_tier(user_id)
        if tier == "dead" and category != TRANSACTIONAL:
            return False, "engagement dead - suppressing non-transactional"
        if tier == "low" and category == "promotional":
            return False, "low engagement - suppressing promotional"

        return True, "all checks passed"

    def _get_engagement_tier(self, user_id):
        data = self._engagement.get(user_id)
        if not data:
            return "medium"
        opens = data.get("opens_last_7d", 0)
        last_open_str = data.get("last_open")
        days_silent = 0
        if last_open_str:
            last_open = datetime.fromisoformat(last_open_str)
            if last_open.tzinfo is None:
                last_open = last_open.replace(tzinfo=timezone.utc)
            days_silent = (datetime.now(timezone.utc) - last_open).days

        if opens >= 5:
            return "high"
        if opens >= 1 and days_silent < 14:
            return "medium"
        if days_silent >= 30:
            return "dead"
        return "low"

    def record_open(self, user_id):
        if user_id in self._engagement:
            self._engagement[user_id]["opens_last_7d"] += 1
            self._engagement[user_id]["last_open"] = datetime.now(timezone.utc).isoformat()

    def set_engagement(self, user_id, opens_last_7d, days_since_last_open=0):
        last_open = datetime.now(timezone.utc) - timedelta(days=days_since_last_open)
        self._engagement[user_id] = {
            "opens_last_7d": opens_last_7d,
            "last_open": last_open.isoformat(),
        }


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def run_demo():
    print("=" * 68)
    print("NOTIFICATION PREFERENCE MANAGER")
    print("=" * 68)

    pm = PreferenceManager()

    pm.set_defaults("alice")
    pm.set_defaults("bob")
    pm.set_defaults("carol")
    pm.set_defaults("dave")

    pm.set_channel("bob", "sms", False)
    pm.set_category_channel("bob", "promotional", "email", False)

    pm.set_quiet_hours("carol", start_hour=22, end_hour=8, tz_offset_hours=-5)

    pm.disable_all("dave")

    pm.set_engagement("alice", opens_last_7d=8, days_since_last_open=0)
    pm.set_engagement("bob", opens_last_7d=2, days_since_last_open=3)
    pm.set_engagement("carol", opens_last_7d=0, days_since_last_open=20)
    pm.set_engagement("dave", opens_last_7d=0, days_since_last_open=45)

    print("\n--- User Configurations ---\n")
    configs = {
        "alice": "Defaults, high engagement",
        "bob":   "No SMS, no promo email, medium engagement",
        "carol": "Quiet hours 22:00-08:00 ET, low engagement",
        "dave":  "All notifications disabled, dead engagement",
    }
    for user, desc in configs.items():
        tier = pm._get_engagement_tier(user)
        print(f"  {user:8s} - {desc} (tier: {tier})")

    print("\n--- Decision Matrix ---\n")
    print(f"  {'User':8s} {'Category':15s} {'Channel':8s} {'Send?':6s} Reason")
    print(f"  {'-'*8} {'-'*15} {'-'*8} {'-'*6} {'-'*35}")

    utc_3am = datetime(2025, 6, 15, 8, 0, tzinfo=timezone.utc)

    test_cases = [
        ("alice", "social",        "push",  None),
        ("alice", "promotional",   "email", None),
        ("alice", "transactional", "sms",   None),
        ("bob",   "social",        "sms",   None),
        ("bob",   "promotional",   "email", None),
        ("bob",   "transactional", "sms",   None),
        ("carol", "social",        "push",  utc_3am),
        ("carol", "social",        "push",  None),
        ("carol", "promotional",   "email", None),
        ("carol", "transactional", "sms",   utc_3am),
        ("dave",  "social",        "push",  None),
        ("dave",  "transactional", "email", None),
    ]

    for user, category, channel, send_time in test_cases:
        send, reason = pm.should_send(user, category, channel, send_time)
        status = "YES" if send else "NO"
        print(f"  {user:8s} {category:15s} {channel:8s} {status:6s} {reason}")

    print("\n--- Transactional Override ---\n")
    print("  Transactional notifications always deliver, even when:")
    print("  - User disabled all notifications (dave)")
    print("  - User is in quiet hours (carol)")
    print("  - User has dead engagement score")
    print("  This is by design - you can't opt out of your own OTP code.")

    print("\n--- Engagement Tiers ---\n")
    print(f"  {'Tier':8s} {'Opens/7d':10s} {'Action'}")
    print(f"  {'-'*8} {'-'*10} {'-'*35}")
    for tier, rules in ENGAGEMENT_TIERS.items():
        print(f"  {tier:8s} {'>=' + str(rules['min_opens_7d']):10s} {rules['action']}")

    print("\n  Engagement scoring prevents notification fatigue by reducing")
    print("  frequency for disengaged users before they hit unsubscribe.")

    result = pm.set_category_channel("alice", "transactional", "sms", False)
    print(f"\n--- Attempting to opt out of transactional ---")
    print(f"  Result: {'blocked' if not result else 'allowed'} (transactional opt-out is not permitted)")


if __name__ == "__main__":
    run_demo()
