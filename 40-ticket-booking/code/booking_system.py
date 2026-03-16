"""
Ticket Booking System API
=========================
Flask API demonstrating core ticket booking mechanics: browse events,
view seat maps, hold seats with a timer, and confirm bookings.

Uses in-memory state to keep it standalone - production would use
PostgreSQL + Redis.

Usage:
  python booking_system.py
  curl http://localhost:5000/events
"""

import uuid
import time
import threading
from flask import Flask, jsonify, request

app = Flask(__name__)

# ---------------------------------------------------------------------------
# In-memory data store (simulates PostgreSQL + Redis)
# ---------------------------------------------------------------------------

HOLD_DURATION = 420  # 7 minutes in seconds
MAX_HOLDS_PER_USER = 6
lock = threading.Lock()

EVENTS = {
    "evt-1": {
        "id": "evt-1",
        "title": "Coldplay - Music of the Spheres",
        "venue": "Wembley Stadium",
        "city": "London",
        "date": "2026-07-15T19:00:00Z",
        "status": "on_sale",
    },
    "evt-2": {
        "id": "evt-2",
        "title": "Stand-Up Comedy Night",
        "venue": "The Comedy Store",
        "city": "Mumbai",
        "date": "2026-04-20T20:00:00Z",
        "status": "on_sale",
    },
}

def _generate_seats(event_id, sections):
    seats = {}
    for section, (rows, seats_per_row, price) in sections.items():
        for r in range(1, rows + 1):
            for s in range(1, seats_per_row + 1):
                seat_id = f"{section}{r}-{s}"
                seats[seat_id] = {
                    "id": seat_id,
                    "event_id": event_id,
                    "section": section,
                    "row": r,
                    "seat": s,
                    "price": price,
                    "status": "available",
                    "held_by": None,
                    "held_until": None,
                    "version": 0,
                }
    return seats

SEATS = {
    "evt-1": _generate_seats("evt-1", {
        "A": (3, 10, 250.00),
        "B": (3, 10, 150.00),
        "C": (4, 10, 75.00),
    }),
    "evt-2": _generate_seats("evt-2", {
        "A": (2, 8, 50.00),
        "B": (3, 8, 30.00),
    }),
}

BOOKINGS = {}

# ---------------------------------------------------------------------------
# Hold expiry sweeper
# ---------------------------------------------------------------------------

def _sweep_expired_holds():
    while True:
        time.sleep(10)
        now = time.time()
        with lock:
            for event_seats in SEATS.values():
                for seat in event_seats.values():
                    if seat["status"] == "held" and seat["held_until"] and seat["held_until"] < now:
                        seat["status"] = "available"
                        seat["held_by"] = None
                        seat["held_until"] = None

sweeper = threading.Thread(target=_sweep_expired_holds, daemon=True)
sweeper.start()

# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------

@app.route("/events")
def list_events():
    return jsonify(list(EVENTS.values()))


@app.route("/events/<event_id>/seats")
def get_seats(event_id):
    if event_id not in SEATS:
        return jsonify({"error": "Event not found"}), 404

    event_seats = SEATS[event_id]
    summary = {"available": 0, "held": 0, "booked": 0}
    seats_out = []

    for seat in event_seats.values():
        summary[seat["status"]] += 1
        seats_out.append({
            "id": seat["id"],
            "section": seat["section"],
            "row": seat["row"],
            "seat": seat["seat"],
            "price": seat["price"],
            "status": seat["status"],
        })

    return jsonify({"event_id": event_id, "summary": summary, "seats": seats_out})


@app.route("/hold", methods=["POST"])
def hold_seat():
    data = request.json
    event_id = data.get("event_id")
    seat_id = data.get("seat_id")
    user_id = data.get("user_id")

    if not all([event_id, seat_id, user_id]):
        return jsonify({"error": "event_id, seat_id, and user_id required"}), 400

    if event_id not in SEATS or seat_id not in SEATS[event_id]:
        return jsonify({"error": "Event or seat not found"}), 404

    with lock:
        # Check per-user hold limit
        user_holds = sum(
            1 for es in SEATS.get(event_id, {}).values()
            if es["held_by"] == user_id and es["status"] == "held"
        )
        if user_holds >= MAX_HOLDS_PER_USER:
            return jsonify({"error": f"Maximum {MAX_HOLDS_PER_USER} holds per user"}), 429

        seat = SEATS[event_id][seat_id]
        if seat["status"] != "available":
            return jsonify({"error": "Seat not available", "current_status": seat["status"]}), 409

        # Atomic hold - equivalent to Redis SET NX EX
        seat["status"] = "held"
        seat["held_by"] = user_id
        seat["held_until"] = time.time() + HOLD_DURATION
        seat["version"] += 1

    return jsonify({
        "message": "Seat held successfully",
        "seat_id": seat_id,
        "held_until": seat["held_until"],
        "hold_duration_seconds": HOLD_DURATION,
    })


@app.route("/release", methods=["POST"])
def release_seat():
    data = request.json
    event_id = data.get("event_id")
    seat_id = data.get("seat_id")
    user_id = data.get("user_id")

    with lock:
        seat = SEATS.get(event_id, {}).get(seat_id)
        if not seat:
            return jsonify({"error": "Seat not found"}), 404
        if seat["held_by"] != user_id:
            return jsonify({"error": "You don't hold this seat"}), 403

        seat["status"] = "available"
        seat["held_by"] = None
        seat["held_until"] = None

    return jsonify({"message": "Seat released", "seat_id": seat_id})


@app.route("/book", methods=["POST"])
def book_seat():
    data = request.json
    event_id = data.get("event_id")
    seat_id = data.get("seat_id")
    user_id = data.get("user_id")

    with lock:
        seat = SEATS.get(event_id, {}).get(seat_id)
        if not seat:
            return jsonify({"error": "Seat not found"}), 404
        if seat["status"] != "held" or seat["held_by"] != user_id:
            return jsonify({"error": "You must hold this seat before booking"}), 409

        # Check hold hasn't expired
        if seat["held_until"] < time.time():
            seat["status"] = "available"
            seat["held_by"] = None
            seat["held_until"] = None
            return jsonify({"error": "Hold expired - seat released"}), 410

        # Confirm booking - equivalent to DB INSERT + UPDATE
        booking_id = f"bk-{uuid.uuid4().hex[:8]}"
        seat["status"] = "booked"
        seat["version"] += 1

        BOOKINGS[booking_id] = {
            "id": booking_id,
            "user_id": user_id,
            "event_id": event_id,
            "seat_id": seat_id,
            "price": seat["price"],
            "status": "confirmed",
            "booked_at": time.time(),
        }

    return jsonify({
        "message": "Booking confirmed",
        "booking": BOOKINGS[booking_id],
    })


@app.route("/bookings/<user_id>")
def user_bookings(user_id):
    user_bks = [b for b in BOOKINGS.values() if b["user_id"] == user_id]
    return jsonify({"user_id": user_id, "bookings": user_bks})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    total = sum(len(s) for s in SEATS.values())
    print(f"Ticket Booking API running - {len(EVENTS)} events, {total} seats loaded")
    app.run(port=5000, debug=False)
