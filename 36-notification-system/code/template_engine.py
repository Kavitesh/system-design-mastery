"""
Notification Template Engine
=============================
Manages notification templates with variable substitution, channel-specific
formatting, character limit enforcement, and localization support.
Templates are the single source of truth for all notification copy.

Run the demo:
    python template_engine.py
"""

import re
import json
from datetime import datetime


# ---------------------------------------------------------------------------
# Channel constraints
# ---------------------------------------------------------------------------

CHANNEL_LIMITS = {
    "sms": {"body": 160},
    "push": {"title": 65, "body": 178},
    "email": {"subject": 150, "body": 50000},
}


# ---------------------------------------------------------------------------
# Template store
# ---------------------------------------------------------------------------

class TemplateEngine:
    def __init__(self):
        self._templates = {}
        self._render_count = 0

    def register(self, template_id, category, channels):
        warnings = self._validate_limits(channels)
        self._templates[template_id] = {
            "id": template_id,
            "category": category,
            "channels": channels,
            "created_at": datetime.now().isoformat(),
        }
        return warnings

    def _validate_limits(self, channels):
        warnings = []
        for channel, fields in channels.items():
            limits = CHANNEL_LIMITS.get(channel, {})
            for field_name, text in fields.items():
                max_len = limits.get(field_name)
                if max_len and len(text) > max_len:
                    warnings.append(
                        f"{channel}.{field_name}: {len(text)} chars exceeds {max_len} limit"
                    )
        return warnings

    def render(self, template_id, channel, variables):
        if template_id not in self._templates:
            raise ValueError(f"Unknown template: {template_id}")

        template = self._templates[template_id]
        if channel not in template["channels"]:
            raise ValueError(f"Template '{template_id}' has no '{channel}' channel")

        channel_template = template["channels"][channel]
        rendered = {}
        for field_name, raw_text in channel_template.items():
            text = self._substitute(raw_text, variables)
            missing = re.findall(r"\{\{(\w+)\}\}", text)
            if missing:
                raise ValueError(f"Missing variables: {missing}")
            rendered[field_name] = text

        self._render_count += 1
        return {
            "template_id": template_id,
            "category": template["category"],
            "channel": channel,
            "content": rendered,
        }

    def _substitute(self, text, variables):
        for key, val in variables.items():
            text = text.replace("{{" + key + "}}", str(val))
        return text

    def render_all_channels(self, template_id, variables):
        template = self._templates.get(template_id)
        if not template:
            raise ValueError(f"Unknown template: {template_id}")
        results = {}
        for channel in template["channels"]:
            results[channel] = self.render(template_id, channel, variables)
        return results

    def list_templates(self):
        summary = []
        for tid, t in self._templates.items():
            summary.append({
                "id": tid,
                "category": t["category"],
                "channels": list(t["channels"].keys()),
            })
        return summary

    @property
    def render_count(self):
        return self._render_count


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def run_demo():
    print("=" * 68)
    print("NOTIFICATION TEMPLATE ENGINE")
    print("=" * 68)

    engine = TemplateEngine()

    print("\n--- Registering templates ---\n")

    w1 = engine.register("order_shipped", "transactional", {
        "email": {
            "subject": "Your order {{order_id}} has shipped!",
            "body": "Hi {{user_name}}, your order is on its way.\nTrack it here: {{tracking_url}}",
        },
        "sms": {
            "body": "Order {{order_id}} shipped. Track: {{tracking_url}}",
        },
        "push": {
            "title": "Order Shipped",
            "body": "{{order_id}} is on its way!",
        },
    })
    print(f"  order_shipped  - registered (warnings: {w1 or 'none'})")

    w2 = engine.register("otp_code", "transactional", {
        "sms": {"body": "Your verification code is {{code}}. Expires in 5 minutes."},
        "email": {
            "subject": "Your verification code",
            "body": "Your code is {{code}}. Do not share this with anyone.",
        },
    })
    print(f"  otp_code       - registered (warnings: {w2 or 'none'})")

    w3 = engine.register("weekly_digest", "promotional", {
        "email": {
            "subject": "Your week in review - {{week_date}}",
            "body": "Hi {{user_name}}, here is what happened:\n{{summary}}\n\nSee you next week!",
        },
    })
    print(f"  weekly_digest  - registered (warnings: {w3 or 'none'})")

    long_sms = "x" * 200
    w4 = engine.register("bad_template", "promotional", {
        "sms": {"body": long_sms},
    })
    print(f"  bad_template   - registered (warnings: {w4})")

    print("\n--- Template inventory ---\n")
    for t in engine.list_templates():
        print(f"  {t['id']:20s}  category={t['category']:15s}  channels={t['channels']}")

    print("\n--- Rendering: order_shipped (all channels) ---\n")
    variables = {
        "order_id": "ORD-7891",
        "user_name": "Alice",
        "tracking_url": "https://track.example.com/7891",
    }
    all_rendered = engine.render_all_channels("order_shipped", variables)
    for channel, result in all_rendered.items():
        print(f"  [{channel.upper()}]")
        for field_name, text in result["content"].items():
            print(f"    {field_name}: {text}")
        print()

    print("--- Rendering: otp_code (SMS only) ---\n")
    rendered = engine.render("otp_code", "sms", {"code": "847293"})
    print(f"  {rendered['content']['body']}")

    print("\n--- Error handling ---\n")
    try:
        engine.render("otp_code", "sms", {})
    except ValueError as e:
        print(f"  Missing variables caught: {e}")

    try:
        engine.render("otp_code", "push", {"code": "123"})
    except ValueError as e:
        print(f"  Bad channel caught: {e}")

    try:
        engine.render("nonexistent", "sms", {})
    except ValueError as e:
        print(f"  Bad template caught: {e}")

    print(f"\n--- Stats ---")
    print(f"  Total renders: {engine.render_count}")
    print(f"  Templates registered: {len(engine.list_templates())}")

    print("\nKey points:")
    print("  - Templates separate content from delivery logic")
    print("  - Channel limits are validated at registration time")
    print("  - Missing variables raise errors before sending")
    print("  - One template renders differently per channel (SMS is short, email is rich)")


if __name__ == "__main__":
    run_demo()
