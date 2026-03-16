"""
Webhook Demo
============
Simulates a payment service that sends webhook notifications.
Includes subscriber registration, HMAC signature verification,
and delivery with exponential backoff retries.

Run: python webhook_demo.py
Then: curl -X POST http://localhost:5004/payments/charge \
           -H "Content-Type: application/json" \
           -d '{"amount": 99.99, "customer": "alice"}'
"""

from flask import Flask, request, jsonify
import requests
import hashlib
import hmac
import json
import time
import threading
import uuid

app = Flask(__name__)

WEBHOOK_SECRET = "super-secret-key"
subscribers = {}
events_log = []


# ---------------------------------------------------------------------------
# Signing & delivery
# ---------------------------------------------------------------------------

def sign_payload(payload_str):
    return hmac.new(
        WEBHOOK_SECRET.encode(),
        payload_str.encode(),
        hashlib.sha256,
    ).hexdigest()


def deliver_webhook(sub_id, url, event):
    """POST the event to the subscriber's URL with retries."""
    payload = json.dumps(event)
    signature = sign_payload(payload)
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": f"sha256={signature}",
        "X-Webhook-Event": event["type"],
        "X-Webhook-ID": event["id"],
    }

    for attempt in range(3):
        try:
            resp = requests.post(url, data=payload, headers=headers, timeout=5)
            if 200 <= resp.status_code < 300:
                print(f"  [OK] Delivered to {url} (attempt {attempt + 1})")
                return True
            print(f"  [WARN] {url} returned {resp.status_code} (attempt {attempt + 1})")
        except requests.exceptions.RequestException as e:
            print(f"  [FAIL] {url} - {e} (attempt {attempt + 1})")

        if attempt < 2:
            wait = 2 ** attempt  # 1s, 2s
            print(f"  [RETRY] Waiting {wait}s...")
            time.sleep(wait)

    print(f"  [DEAD] Gave up on {url} after 3 attempts")
    return False


# ---------------------------------------------------------------------------
# Webhook registration
# ---------------------------------------------------------------------------

@app.route("/webhooks/subscribe", methods=["POST"])
def subscribe():
    data = request.get_json()
    if not data or "url" not in data:
        return jsonify({"error": "url is required"}), 400

    sub_id = str(uuid.uuid4())[:8]
    subscribers[sub_id] = {
        "id": sub_id,
        "url": data["url"],
        "events": data.get("events", ["*"]),
    }

    return jsonify({"id": sub_id, "url": data["url"]}), 201


@app.route("/webhooks/subscribers", methods=["GET"])
def list_subscribers():
    return jsonify(list(subscribers.values()))


# ---------------------------------------------------------------------------
# Payment endpoint (triggers webhooks)
# ---------------------------------------------------------------------------

@app.route("/payments/charge", methods=["POST"])
def charge():
    data = request.get_json() or {}

    event = {
        "id": f"evt_{uuid.uuid4().hex[:12]}",
        "type": "payment.completed",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "data": {
            "amount": data.get("amount", 49.99),
            "currency": "USD",
            "customer": data.get("customer", "cust_123"),
            "status": "succeeded",
        },
    }
    events_log.append(event)

    # Fire webhooks in background
    for sub in subscribers.values():
        if "*" in sub["events"] or event["type"] in sub["events"]:
            t = threading.Thread(target=deliver_webhook, args=(sub["id"], sub["url"], event))
            t.daemon = True
            t.start()

    return jsonify({
        "payment": "processed",
        "event_id": event["id"],
        "webhooks_notified": len(subscribers),
    })


# ---------------------------------------------------------------------------
# Webhook receiver (simulates YOUR app getting the callback)
# ---------------------------------------------------------------------------

@app.route("/my-app/webhook", methods=["POST"])
def receive_webhook():
    signature = request.headers.get("X-Webhook-Signature", "")
    expected = f"sha256={sign_payload(request.data.decode())}"

    if not hmac.compare_digest(signature, expected):
        print("  [SECURITY] Invalid signature - rejecting!")
        return jsonify({"error": "invalid signature"}), 401

    data = request.get_json()
    print(f"\n  ====================================")
    print(f"  WEBHOOK RECEIVED!")
    print(f"  Event:  {request.headers.get('X-Webhook-Event')}")
    print(f"  ID:     {request.headers.get('X-Webhook-ID')}")
    print(f"  Amount: ${data['data']['amount']}")
    print(f"  Status: {data['data']['status']}")
    print(f"  Signature: VALID")
    print(f"  ====================================\n")

    return jsonify({"received": True}), 200


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "service": "Webhook Demo",
        "steps": [
            "1. Register webhook: POST /webhooks/subscribe",
            "2. Trigger payment: POST /payments/charge",
            "3. Watch the webhook arrive at your callback URL",
        ],
    })


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"\n  Webhook Demo running at http://localhost:5004")

    def auto_register():
        time.sleep(1)
        try:
            resp = requests.post(
                "http://localhost:5004/webhooks/subscribe",
                json={"url": "http://localhost:5004/my-app/webhook", "events": ["*"]},
            )
            print(f"  Auto-registered receiver: {resp.json()['id']}")
            print(f"\n  Trigger a payment:")
            print(f'    curl -X POST http://localhost:5004/payments/charge \\')
            print(f'         -H "Content-Type: application/json" \\')
            print(f"         -d '{{\"amount\": 99.99, \"customer\": \"alice\"}}'")
            print()
        except Exception:
            print("  (Register manually via POST /webhooks/subscribe)")

    threading.Thread(target=auto_register, daemon=True).start()
    app.run(port=5004, debug=False)
