"""
Chat Server - WebSocket-Based Chat With Rooms and Presence
===========================================================
Multi-room chat server using the websockets library. Tracks connected
users, broadcasts messages within rooms, maintains message history,
and reports online presence. This is the server-side analog of a
single chat server node in the distributed architecture.
"""

import asyncio
import json
import time
from collections import defaultdict
from datetime import datetime

try:
    import websockets
except ImportError:
    print("Install websockets: pip install websockets")
    raise SystemExit(1)

HOST = "localhost"
PORT = 8765
MAX_HISTORY = 100

# ---------------------------------------------------------------------------
#  Server state (in production these live in Redis)
# ---------------------------------------------------------------------------

rooms = defaultdict(set)               # room_name -> set of (websocket, username)
history = defaultdict(list)            # room_name -> list of message dicts
user_connections = {}                  # username -> websocket
online_since = {}                      # username -> connect timestamp

# ---------------------------------------------------------------------------
#  Message helpers
# ---------------------------------------------------------------------------

def make_message(msg_type, **kwargs):
    return json.dumps({"type": msg_type, **kwargs})


def system_msg(text):
    return make_message("system", text=text, timestamp=time.time())


def chat_msg(sender, text, room):
    return make_message("chat", sender=sender, text=text, room=room, timestamp=time.time())


def presence_msg(user, status, online_users):
    return make_message("presence", user=user, status=status, online_users=online_users)


# ---------------------------------------------------------------------------
#  Broadcast
# ---------------------------------------------------------------------------

async def broadcast(room, message, exclude=None):
    targets = [ws for ws, _ in rooms[room] if ws != exclude]
    if targets:
        await asyncio.gather(*[ws.send(message) for ws in targets], return_exceptions=True)


async def send_to(ws, message):
    try:
        await ws.send(message)
    except websockets.ConnectionClosed:
        pass


# ---------------------------------------------------------------------------
#  Room management
# ---------------------------------------------------------------------------

def get_online_in_room(room):
    return [username for _, username in rooms[room]]


async def join_room(ws, username, room):
    rooms[room].add((ws, username))
    user_connections[username] = ws
    online_since[username] = time.time()

    online = get_online_in_room(room)
    await broadcast(room, presence_msg(username, "online", online))

    recent = history[room][-20:]
    if recent:
        await send_to(ws, make_message("history", messages=recent))

    await send_to(ws, system_msg(f"Joined #{room}. {len(online)} user(s) online."))


async def leave_room(ws, username, room):
    rooms[room].discard((ws, username))
    user_connections.pop(username, None)
    online_since.pop(username, None)

    if rooms[room]:
        online = get_online_in_room(room)
        await broadcast(room, presence_msg(username, "offline", online))
    else:
        del rooms[room]


# ---------------------------------------------------------------------------
#  Command handling
# ---------------------------------------------------------------------------

async def handle_command(ws, username, room, command):
    cmd = command.strip().lower()
    if cmd == "/users":
        online = get_online_in_room(room)
        user_list = ", ".join(online) if online else "(empty)"
        await send_to(ws, system_msg(f"Online in #{room}: {user_list}"))
    elif cmd == "/history":
        recent = history[room][-20:]
        if recent:
            await send_to(ws, make_message("history", messages=recent))
        else:
            await send_to(ws, system_msg("No message history yet."))
    elif cmd == "/quit":
        await send_to(ws, system_msg("Goodbye."))
        await ws.close()
    else:
        await send_to(ws, system_msg(f"Unknown command: {cmd}"))


# ---------------------------------------------------------------------------
#  Connection handler
# ---------------------------------------------------------------------------

async def handle_client(ws):
    username = None
    room = None
    try:
        await send_to(ws, system_msg("Send JOIN message: {\"action\":\"join\",\"username\":\"...\",\"room\":\"...\"}"))
        async for raw in ws:
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await send_to(ws, system_msg("Invalid JSON"))
                continue

            action = data.get("action", "message")

            if action == "join" and not username:
                username = data.get("username", "").strip()
                room = data.get("room", "general").strip()
                if not username:
                    await send_to(ws, system_msg("Username required"))
                    continue
                if username in user_connections:
                    await send_to(ws, system_msg(f"Username '{username}' already taken"))
                    username = None
                    continue
                await join_room(ws, username, room)

            elif action == "message" and username:
                text = data.get("text", "").strip()
                if not text:
                    continue
                if text.startswith("/"):
                    await handle_command(ws, username, room, text)
                else:
                    msg = chat_msg(username, text, room)
                    msg_dict = json.loads(msg)
                    history[room].append(msg_dict)
                    if len(history[room]) > MAX_HISTORY:
                        history[room] = history[room][-MAX_HISTORY:]
                    await broadcast(room, msg)

            elif not username:
                await send_to(ws, system_msg("Join a room first"))

    except websockets.ConnectionClosed:
        pass
    finally:
        if username and room:
            await leave_room(ws, username, room)


# ---------------------------------------------------------------------------
#  Entry point
# ---------------------------------------------------------------------------

async def main():
    print(f"chat_server: listening on ws://{HOST}:{PORT}")
    async with websockets.serve(handle_client, HOST, PORT):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
