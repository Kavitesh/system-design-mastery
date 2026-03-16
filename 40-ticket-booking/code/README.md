# Ticket Booking System - Code Lab

Hands-on demos for the core mechanics of a ticket booking platform: seat inventory, temporary holds, concurrency control, and fair queuing.

## What's Included

| File | Description |
|------|-------------|
| `booking_system.py` | Flask API with events, seats, holds, and booking endpoints |
| `seat_lock.py` | Temporary seat reservation engine with automatic expiry (no Redis required) |
| `concurrency_test.py` | Spawns concurrent booking attempts to demonstrate locking behavior |
| `waiting_queue.py` | Fair FIFO waiting queue with position tracking and batch admission |

## Prerequisites

```bash
pip install flask requests
```

No Redis or external database required - all demos use in-memory state so you can run them instantly.

## Running the Demos

### 1. Booking System API

Full Flask API for browsing events, selecting seats, and completing bookings:

```bash
python booking_system.py
```

Then in another terminal:

```bash
# List events
curl http://localhost:5000/events

# View available seats for an event
curl http://localhost:5000/events/evt-1/seats

# Hold a seat (7-minute timer starts)
curl -X POST http://localhost:5000/hold \
  -H "Content-Type: application/json" \
  -d '{"event_id": "evt-1", "seat_id": "A1", "user_id": "user-42"}'

# Confirm the booking
curl -X POST http://localhost:5000/book \
  -H "Content-Type: application/json" \
  -d '{"event_id": "evt-1", "seat_id": "A1", "user_id": "user-42"}'
```

### 2. Seat Lock Engine

Standalone demo of the hold timer mechanism with automatic expiry:

```bash
python seat_lock.py
```

Runs a self-contained scenario showing seat holds, expiry, and contention handling.

### 3. Concurrency Test

Launches multiple threads attempting to book the same seats simultaneously:

```bash
python concurrency_test.py
```

Watch how locking prevents double-booking even under heavy contention.

### 4. Waiting Queue

Fair queuing system for high-demand events with position tracking:

```bash
python waiting_queue.py
```

Simulates users joining a queue and being admitted in controlled batches.

## Architecture Notes

These demos simulate what a production system would use Redis and PostgreSQL for. The patterns are identical - atomic locks, version-based concurrency control, sorted-set queuing - just backed by Python's `threading.Lock` and in-memory dicts instead of external infrastructure.
