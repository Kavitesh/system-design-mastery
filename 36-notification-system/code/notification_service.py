"""
Notification Service API
========================
Flask server that accepts notification requests, validates them,
checks user preferences, and routes to the appropriate channel.
Simulates email, SMS, and push delivery with in-memory storage.

Start the server:
    python notification_service.py
"""

import uuid
import time
from datetime import datetime

from flask import Flask, request, jsonify

app = Flask(__name__)

# ---------------------------------------------------------------------------
# In-memory stores (would be Redis + DB in production)
# ---------------------------------------------------------------------------

NOTIFICATIONS = {}
USER_CONTACTS = {
    "u_001": {
        "email": "alice@example.com", "email_verified": True,
        "phone": "+15550101", "phone_verified": True,
        "device_tokens": [{"token": "apns_abc123", "platform": "ios"}],
    },
    "u_002": {
        "email": "bob@example.com", "email_verified": True,
        "phone": "+15550102", "phone_verified": False,
        "device_tokens": [{"token": "fcm_def456", "platform": "android"}],
    },
    "u_003": {
        "email": "carol@example.com", "email_verified": True,
        "phone": "+15550103", "phone_verified": True,
        "device_tokens": [],
    },
}

TEMPLATES = {
    "order_shipped": {
        "category": "transactional",
        "email": {"subject": "Order {{order_id}} shipped!", "body": "Track here: {{tracking_url}}"},
        "sms": {"body": "Order {{order_id}} shipped. Track: {{tracking_url}}"},
        "push": {"title": "Order Shipped", "body": "{{order_id}} is on its way!"},
    },
    "new_follower": {
        "category": "social",
        "email": {"subject": "{{follower_name}} followed you", "body": "Check out their profile."},
        "sms": {"body": "{{follower_name}} just followed you!"},
        "push": {"title": "New Follower", "body": "{{follower_name}} followed you"},
    },
    "promo_sale": {
        "category": "promotional",
        "email": {"subject": "{{discount}}% off everything!", "body": "Sale ends {{end_date}}."},
        "sms": {"body": "{{discount}}% off! Ends {{end_date}}. Reply STOP to opt out."},
        "push": {"title": "Flash Sale", "body": "{{discount}}% off - limited time!"},
    },
}

RATE_LIMITS = {"email": 20, "sms": 5, "push": 15}
RATE_WINDOW = 3600

rate_counters = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def render_template(template_channel, variables):
    rendered = {}
    for key, val in template_channel.items():
        for var_name, var_val in variables.items():
            val = val.replace("{{" + var_name + "}}", str(var_val))
        rendered[key] = val
    return rendered


def check_rate_limit(user_id, channel):
    key = f"{user_id}:{channel}"
    now = time.time()
    if key not in rate_counters:
        rate_counters[key] = []
    rate_counters[key] = [t for t in rate_counters[key] if now - t < RATE_WINDOW]
    if len(rate_counters[key]) >= RATE_LIMITS.get(channel, 10):
        return False
    rate_counters[key].append(now)
    return True


def simulate_send(channel, contact, rendered):
    """Simulate sending via a provider. Returns delivery status."""
    if channel == "email":
        return {"provider": "SES", "recipient": contact["email"], "status": "delivered", "message": rendered}
    elif channel == "sms":
        if not contact.get("phone_verified"):
            return {"provider": "Twilio", "recipient": contact.get("phone"), "status": "failed", "reason": "unverified phone"}
        return {"provider": "Twilio", "recipient": contact["phone"], "status": "delivered", "message": rendered}
    elif channel == "push":
        if not contact.get("device_tokens"):
            return {"provider": "APNs/FCM", "status": "failed", "reason": "no device tokens"}
        return {"provider": "FCM", "tokens": contact["device_tokens"], "status": "delivered", "message": rendered}
    return {"status": "failed", "reason": f"unknown channel: {channel}"}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/notify", methods=["POST"])
def send_notification():
    data = request.json or {}
    user_id = data.get("user_id")
    template_id = data.get("template_id")
    channel = data.get("channel")
    variables = data.get("variables", {})

    if not all([user_id, template_id, channel]):
        return jsonify({"error": "user_id, template_id, and channel are required"}), 400

    if user_id not in USER_CONTACTS:
        return jsonify({"error": f"unknown user: {user_id}"}), 404

    if template_id not in TEMPLATES:
        return jsonify({"error": f"unknown template: {template_id}"}), 404

    template = TEMPLATES[template_id]
    if channel not in template:
        return jsonify({"error": f"template '{template_id}' has no {channel} channel"}), 400

    if not check_rate_limit(user_id, channel):
        notif_id = str(uuid.uuid4())[:8]
        NOTIFICATIONS[notif_id] = {
            "id": notif_id, "user_id": user_id, "template_id": template_id,
            "channel": channel, "status": "rate_limited",
            "created_at": datetime.now().isoformat(),
        }
        return jsonify({"id": notif_id, "status": "rate_limited", "message": "too many notifications"}), 429

    rendered = render_template(template[channel], variables)
    contact = USER_CONTACTS[user_id]
    result = simulate_send(channel, contact, rendered)

    notif_id = str(uuid.uuid4())[:8]
    NOTIFICATIONS[notif_id] = {
        "id": notif_id, "user_id": user_id, "template_id": template_id,
        "channel": channel, "status": result["status"],
        "rendered": rendered, "delivery": result,
        "created_at": datetime.now().isoformat(),
    }

    status_code = 202 if result["status"] == "delivered" else 500
    return jsonify({"id": notif_id, **result}), status_code


@app.route("/status/<notif_id>")
def get_status(notif_id):
    if notif_id not in NOTIFICATIONS:
        return jsonify({"error": "notification not found"}), 404
    return jsonify(NOTIFICATIONS[notif_id])


@app.route("/history/<user_id>")
def get_history(user_id):
    user_notifs = [n for n in NOTIFICATIONS.values() if n["user_id"] == user_id]
    user_notifs.sort(key=lambda n: n["created_at"], reverse=True)
    return jsonify({"user_id": user_id, "count": len(user_notifs), "notifications": user_notifs[:20]})


@app.route("/templates")
def list_templates():
    summary = {}
    for tid, t in TEMPLATES.items():
        summary[tid] = {"category": t["category"], "channels": [c for c in t if c != "category"]}
    return jsonify(summary)


@app.route("/stats")
def stats():
    by_status = {}
    by_channel = {}
    for n in NOTIFICATIONS.values():
        by_status[n["status"]] = by_status.get(n["status"], 0) + 1
        by_channel[n["channel"]] = by_channel.get(n["channel"], 0) + 1
    return jsonify({"total": len(NOTIFICATIONS), "by_status": by_status, "by_channel": by_channel})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Notification Service running on http://localhost:5000")
    app.run(port=5000, debug=False)
