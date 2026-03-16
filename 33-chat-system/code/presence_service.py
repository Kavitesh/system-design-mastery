"""
Presence Service - Heartbeat-Based Online/Offline Tracking
===========================================================
Tracks user presence status using TTL-based expiration. In production
this runs on Redis with key expiration. Here we simulate the same
logic with in-memory dictionaries and manual time checks.
"""

import time
import threading
from datetime import datetime

# ---------------------------------------------------------------------------
#  Configuration
# ---------------------------------------------------------------------------

HEARTBEAT_INTERVAL = 5      # seconds between heartbeats
HEARTBEAT_TIMEOUT = 12      # seconds before marking offline
AWAY_THRESHOLD = 8           # seconds of no heartbeat before "away"
CLEANUP_INTERVAL = 3         # seconds between expiration sweeps

# ---------------------------------------------------------------------------
#  Presence store (replaces Redis in production)
# ---------------------------------------------------------------------------

class PresenceStore:
    """In-memory presence tracker with TTL-based expiration."""

    def __init__(self):
        self._users = {}       # user_id -> {status, last_seen, device, server_id}
        self._lock = threading.Lock()
        self._listeners = []

    def connect(self, user_id, device="desktop", server_id="chat-server-1"):
        with self._lock:
            prev_status = self._users.get(user_id, {}).get("status")
            self._users[user_id] = {
                "status": "online",
                "last_seen": time.time(),
                "device": device,
                "server_id": server_id,
                "connected_at": time.time(),
            }
            if prev_status != "online":
                self._notify(user_id, "online")

    def heartbeat(self, user_id):
        with self._lock:
            if user_id not in self._users:
                return False
            prev_status = self._users[user_id]["status"]
            self._users[user_id]["last_seen"] = time.time()
            self._users[user_id]["status"] = "online"
            if prev_status != "online":
                self._notify(user_id, "online")
            return True

    def disconnect(self, user_id):
        with self._lock:
            if user_id in self._users:
                self._users[user_id]["status"] = "offline"
                self._users[user_id]["last_seen"] = time.time()
                self._notify(user_id, "offline")

    def get_status(self, user_id):
        with self._lock:
            entry = self._users.get(user_id)
            if not entry:
                return {"status": "offline", "last_seen": None}
            return {
                "status": entry["status"],
                "last_seen": entry["last_seen"],
                "device": entry.get("device"),
            }

    def get_online_users(self):
        with self._lock:
            return [uid for uid, info in self._users.items() if info["status"] == "online"]

    def expire_stale(self):
        """Check for users whose heartbeat has timed out."""
        now = time.time()
        transitions = []
        with self._lock:
            for user_id, info in self._users.items():
                elapsed = now - info["last_seen"]
                if info["status"] == "online" and elapsed > AWAY_THRESHOLD:
                    info["status"] = "away"
                    transitions.append((user_id, "away"))
                elif info["status"] == "away" and elapsed > HEARTBEAT_TIMEOUT:
                    info["status"] = "offline"
                    transitions.append((user_id, "offline"))
        for user_id, new_status in transitions:
            self._notify(user_id, new_status)

    def add_listener(self, callback):
        self._listeners.append(callback)

    def _notify(self, user_id, new_status):
        for cb in self._listeners:
            cb(user_id, new_status)


# ---------------------------------------------------------------------------
#  Background expiration thread
# ---------------------------------------------------------------------------

class ExpirationDaemon:
    """Periodically sweeps for stale heartbeats."""

    def __init__(self, store):
        self._store = store
        self._running = False
        self._thread = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _run(self):
        while self._running:
            self._store.expire_stale()
            time.sleep(CLEANUP_INTERVAL)


# ---------------------------------------------------------------------------
#  Demo simulation
# ---------------------------------------------------------------------------

def format_time(ts):
    if ts is None:
        return "never"
    return datetime.fromtimestamp(ts).strftime("%H:%M:%S")


def presence_event(user_id, new_status):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"  [{ts}] PRESENCE: {user_id} -> {new_status}")


if __name__ == "__main__":
    print("presence_service: heartbeat tracking demo")

    store = PresenceStore()
    store.add_listener(presence_event)
    daemon = ExpirationDaemon(store)
    daemon.start()

    print("\n--- Phase 1: Users connect ---")
    store.connect("alice", device="mobile", server_id="chat-server-1")
    store.connect("bob", device="desktop", server_id="chat-server-2")
    store.connect("carol", device="web", server_id="chat-server-1")
    time.sleep(0.5)

    online = store.get_online_users()
    print(f"  Online users: {online}")

    print("\n--- Phase 2: Heartbeats keep alice and bob alive ---")
    for i in range(3):
        time.sleep(HEARTBEAT_INTERVAL)
        store.heartbeat("alice")
        store.heartbeat("bob")
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"  [{ts}] Heartbeat sent by alice and bob (round {i+1})")

    print("\n--- Phase 3: Carol stops sending heartbeats ---")
    print("  Waiting for carol to go away, then offline...")
    time.sleep(AWAY_THRESHOLD + 1)
    carol_status = store.get_status("carol")
    print(f"  Carol status: {carol_status['status']} (last seen: {format_time(carol_status['last_seen'])})")

    time.sleep(HEARTBEAT_TIMEOUT - AWAY_THRESHOLD + 1)
    carol_status = store.get_status("carol")
    print(f"  Carol status: {carol_status['status']} (last seen: {format_time(carol_status['last_seen'])})")

    print("\n--- Phase 4: Bob disconnects explicitly ---")
    store.disconnect("bob")
    bob_status = store.get_status("bob")
    print(f"  Bob status: {bob_status['status']} (last seen: {format_time(bob_status['last_seen'])})")

    print("\n--- Phase 5: Query all statuses ---")
    for user_id in ["alice", "bob", "carol", "dave"]:
        status = store.get_status(user_id)
        print(f"  {user_id:8s} -> {status['status']:8s} (last seen: {format_time(status['last_seen'])})")

    online = store.get_online_users()
    print(f"\n  Online now: {online}")

    daemon.stop()
    print("\nDone.")
