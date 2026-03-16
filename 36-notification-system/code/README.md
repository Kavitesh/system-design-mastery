# Design a Notification System - Code Lab

Hands-on Python demos covering the core components of a notification system: API layer, priority queue with retries, template engine, and user preference management.

## What's Included

| File | Description |
|------|-------------|
| `notification_service.py` | Flask API supporting email, SMS, and push channels |
| `notification_queue.py` | Priority queue with retry logic and exponential backoff |
| `template_engine.py` | Template system with variable substitution and channel formatting |
| `preference_manager.py` | User notification preferences with channel opt-in/opt-out |

## Prerequisites

```bash
pip install flask
```

## Running the Demos

### 1. Notification Service API

A Flask server exposing endpoints to send notifications, check status, and view history:

```bash
python notification_service.py
```

Test with curl:
```bash
# Send a notification
curl -X POST http://localhost:5000/notify \
  -H "Content-Type: application/json" \
  -d '{"user_id": "u_001", "template_id": "order_shipped", "channel": "email", "variables": {"order_id": "ORD-789", "tracking_url": "https://track.example.com/789"}}'

# Check notification status
curl http://localhost:5000/status/NOTIFICATION_ID

# View user notification history
curl http://localhost:5000/history/u_001
```

### 2. Priority Queue with Retries

Simulates a notification priority queue with four priority levels, exponential backoff, and failure handling:

```bash
python notification_queue.py
```

### 3. Template Engine

Demonstrates template creation, variable substitution, and multi-channel rendering:

```bash
python template_engine.py
```

### 4. Preference Manager

User preference management with per-channel and per-category controls, quiet hours, and engagement scoring:

```bash
python preference_manager.py
```
