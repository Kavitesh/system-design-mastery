"""
Event Triggers - Serverless Event-Driven Execution
====================================================
Simulates four serverless event sources: S3 file uploads, HTTP API calls,
scheduled cron jobs, and SQS queue messages. Each triggers isolated function
handlers with realistic event payloads.

Usage:
    python event_triggers.py
"""

import time
import random
import json
import threading
from datetime import datetime, timedelta
from collections import defaultdict

# ---------------------------------------------------------------------------
# Event Bus - Routes events to registered handlers
# ---------------------------------------------------------------------------

class EventBus:
    def __init__(self):
        self.handlers = defaultdict(list)
        self.event_log = []
        self.invocation_count = 0
        self.errors = 0

    def register(self, event_type, handler):
        self.handlers[event_type].append(handler)

    def emit(self, event_type, payload):
        event = {
            "event_id": f"evt-{random.randint(100000, 999999)}",
            "type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "payload": payload,
        }

        handlers = self.handlers.get(event_type, [])
        if not handlers:
            print(f"  [WARN] No handler for event type: {event_type}")
            return

        for handler in handlers:
            self.invocation_count += 1
            start = time.time()
            try:
                result = handler(event)
                elapsed = (time.time() - start) * 1000
                print(f"  [OK  ] {event['event_id']} | {event_type:<18} "
                      f"-> {handler.__name__:<28} | {elapsed:>6.1f}ms | {result}")
            except Exception as e:
                elapsed = (time.time() - start) * 1000
                self.errors += 1
                print(f"  [FAIL] {event['event_id']} | {event_type:<18} "
                      f"-> {handler.__name__:<28} | {elapsed:>6.1f}ms | {e}")

            self.event_log.append({**event, "handler": handler.__name__})

    def summary(self):
        print(f"\n{'='*65}")
        print(f"  Event Bus Summary")
        print(f"{'='*65}")
        print(f"  Total events processed:  {self.invocation_count}")
        print(f"  Errors:                  {self.errors}")
        print(f"  Registered event types:  {len(self.handlers)}")
        by_type = defaultdict(int)
        for e in self.event_log:
            by_type[e["type"]] += 1
        for t, c in sorted(by_type.items(), key=lambda x: -x[1]):
            print(f"    {t:<22} {c} invocations")
        print(f"{'='*65}")


# ---------------------------------------------------------------------------
# S3 Upload Handlers
# ---------------------------------------------------------------------------

def resize_image(event):
    bucket = event["payload"]["bucket"]
    key = event["payload"]["key"]
    size = event["payload"]["size_bytes"]
    time.sleep(random.uniform(0.05, 0.15))

    sizes = {"thumb": "150x150", "medium": "800x600", "large": "1920x1080"}
    generated = random.choice(list(sizes.keys()))
    return f"Resized {key} to {sizes[generated]} ({size//1024}KB -> {size//4096}KB)"


def extract_metadata(event):
    key = event["payload"]["key"]
    time.sleep(random.uniform(0.02, 0.05))
    metadata = {
        "format": key.split(".")[-1].upper(),
        "dimensions": f"{random.randint(800,4000)}x{random.randint(600,3000)}",
        "color_space": random.choice(["sRGB", "Adobe RGB", "P3"]),
    }
    return f"Metadata for {key}: {json.dumps(metadata)}"


def run_moderation(event):
    key = event["payload"]["key"]
    time.sleep(random.uniform(0.1, 0.3))
    score = random.uniform(0, 1)
    status = "FLAGGED" if score > 0.85 else "APPROVED"
    return f"Moderation {key}: {status} (confidence: {score:.2f})"


# ---------------------------------------------------------------------------
# HTTP API Handlers
# ---------------------------------------------------------------------------

def api_get_user(event):
    user_id = event["payload"]["path_params"]["user_id"]
    time.sleep(random.uniform(0.01, 0.03))
    users = {"u-1": "Alice", "u-2": "Bob", "u-3": "Carol"}
    name = users.get(user_id, "Unknown")
    return f"200 OK - {json.dumps({'id': user_id, 'name': name})}"


def api_create_order(event):
    body = event["payload"]["body"]
    time.sleep(random.uniform(0.02, 0.06))
    order_id = f"ord-{random.randint(1000, 9999)}"
    return f"201 Created - order {order_id} for user {body['user_id']}: ${body['amount']}"


# ---------------------------------------------------------------------------
# Scheduled (Cron) Handlers
# ---------------------------------------------------------------------------

def generate_daily_report(event):
    time.sleep(random.uniform(0.05, 0.1))
    metrics = {
        "active_users": random.randint(1200, 5000),
        "requests": random.randint(50000, 200000),
        "errors": random.randint(10, 150),
        "p99_latency_ms": random.randint(80, 500),
    }
    return f"Daily report: {json.dumps(metrics)}"


def cleanup_expired_sessions(event):
    time.sleep(random.uniform(0.03, 0.08))
    deleted = random.randint(50, 500)
    return f"Cleaned {deleted} expired sessions"


def rotate_api_keys(event):
    time.sleep(random.uniform(0.02, 0.05))
    rotated = random.randint(1, 10)
    return f"Rotated {rotated} API keys expiring within 24h"


# ---------------------------------------------------------------------------
# Queue Message Handlers
# ---------------------------------------------------------------------------

def process_order(event):
    message = event["payload"]["message"]
    time.sleep(random.uniform(0.03, 0.08))
    order_id = message["order_id"]
    steps = ["validated", "payment_charged", "inventory_reserved", "confirmation_sent"]
    completed = random.randint(2, len(steps))
    return f"Order {order_id}: completed {completed}/{len(steps)} steps"


def send_notification(event):
    message = event["payload"]["message"]
    time.sleep(random.uniform(0.01, 0.04))
    channel = message.get("channel", "email")
    recipient = message.get("recipient", "unknown")
    return f"Notification sent via {channel} to {recipient}"


def update_search_index(event):
    message = event["payload"]["message"]
    time.sleep(random.uniform(0.02, 0.06))
    doc_id = message.get("document_id", "doc-???")
    action = message.get("action", "upsert")
    return f"Search index: {action} document {doc_id}"


# ---------------------------------------------------------------------------
# Main Simulation
# ---------------------------------------------------------------------------

def main():
    print("Event Triggers - Serverless Event-Driven Execution")

    bus = EventBus()

    bus.register("s3:ObjectCreated", resize_image)
    bus.register("s3:ObjectCreated", extract_metadata)
    bus.register("s3:ObjectCreated", run_moderation)
    bus.register("apigateway:GET", api_get_user)
    bus.register("apigateway:POST", api_create_order)
    bus.register("schedule:daily", generate_daily_report)
    bus.register("schedule:hourly", cleanup_expired_sessions)
    bus.register("schedule:daily", rotate_api_keys)
    bus.register("sqs:order-queue", process_order)
    bus.register("sqs:notification-queue", send_notification)
    bus.register("sqs:search-index-queue", update_search_index)

    # --- S3 upload events ---
    print("\n--- S3 File Upload Events (fan-out to 3 functions) ---")
    uploads = [
        {"bucket": "user-photos", "key": "uploads/photo_001.jpg", "size_bytes": 2_400_000},
        {"bucket": "user-photos", "key": "uploads/photo_002.png", "size_bytes": 5_100_000},
        {"bucket": "user-photos", "key": "uploads/avatar_003.webp", "size_bytes": 180_000},
    ]
    for upload in uploads:
        bus.emit("s3:ObjectCreated", upload)

    # --- HTTP API events ---
    print("\n--- API Gateway HTTP Events ---")
    bus.emit("apigateway:GET", {
        "method": "GET", "path": "/users/u-1",
        "path_params": {"user_id": "u-1"}, "query": {},
    })
    bus.emit("apigateway:GET", {
        "method": "GET", "path": "/users/u-3",
        "path_params": {"user_id": "u-3"}, "query": {},
    })
    bus.emit("apigateway:POST", {
        "method": "POST", "path": "/orders",
        "path_params": {}, "body": {"user_id": "u-1", "item": "Widget", "amount": 29.99},
    })

    # --- Scheduled events ---
    print("\n--- Scheduled (Cron) Events ---")
    bus.emit("schedule:daily", {"schedule": "cron(0 6 * * *)", "trigger_time": "06:00 UTC"})
    bus.emit("schedule:hourly", {"schedule": "rate(1 hour)", "trigger_time": "14:00 UTC"})

    # --- Queue message events ---
    print("\n--- SQS Queue Message Events ---")
    queue_messages = [
        ("sqs:order-queue", {"order_id": "ord-5501", "user_id": "u-1", "total": 79.99}),
        ("sqs:order-queue", {"order_id": "ord-5502", "user_id": "u-2", "total": 149.00}),
        ("sqs:notification-queue", {"recipient": "alice@example.com", "channel": "email",
                                     "template": "order_confirmation"}),
        ("sqs:notification-queue", {"recipient": "+1555123456", "channel": "sms",
                                     "template": "shipping_update"}),
        ("sqs:search-index-queue", {"document_id": "prod-8801", "action": "upsert",
                                     "fields": ["title", "price", "category"]}),
        ("sqs:search-index-queue", {"document_id": "prod-4422", "action": "delete"}),
    ]
    for queue_name, message in queue_messages:
        bus.emit(queue_name, {"queue": queue_name, "message": message,
                              "approximate_receive_count": random.randint(1, 3)})

    # --- Rapid-fire burst (simulates traffic spike) ---
    print("\n--- Traffic Burst (10 concurrent API calls) ---")
    for i in range(10):
        user_id = f"u-{random.randint(1, 3)}"
        bus.emit("apigateway:GET", {
            "method": "GET", "path": f"/users/{user_id}",
            "path_params": {"user_id": user_id}, "query": {},
        })

    bus.summary()


if __name__ == "__main__":
    main()
