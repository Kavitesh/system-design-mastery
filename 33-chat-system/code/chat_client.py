"""
Chat Client - Terminal WebSocket Chat Client
==============================================
Connects to the chat server, joins a room, and provides a terminal
interface for sending and receiving messages. Runs send and receive
loops concurrently using asyncio.
"""

import asyncio
import json
import sys
from datetime import datetime

try:
    import websockets
except ImportError:
    print("Install websockets: pip install websockets")
    raise SystemExit(1)

SERVER_URI = "ws://localhost:8765"

# ---------------------------------------------------------------------------
#  Display formatting
# ---------------------------------------------------------------------------

def format_timestamp(ts):
    return datetime.fromtimestamp(ts).strftime("%H:%M:%S")


def display_message(data):
    msg_type = data.get("type")
    if msg_type == "chat":
        ts = format_timestamp(data["timestamp"])
        print(f"\r  [{ts}] {data['sender']}: {data['text']}")
    elif msg_type == "system":
        print(f"\r  * {data['text']}")
    elif msg_type == "presence":
        status = data["status"]
        user = data["user"]
        count = len(data.get("online_users", []))
        print(f"\r  * {user} is now {status} ({count} online)")
    elif msg_type == "history":
        print("\r  --- Recent messages ---")
        for msg in data.get("messages", []):
            ts = format_timestamp(msg["timestamp"])
            print(f"\r  [{ts}] {msg['sender']}: {msg['text']}")
        print("\r  --- End of history ---")


# ---------------------------------------------------------------------------
#  Receive loop
# ---------------------------------------------------------------------------

async def receive_messages(ws):
    try:
        async for raw in ws:
            try:
                data = json.loads(raw)
                display_message(data)
                print("> ", end="", flush=True)
            except json.JSONDecodeError:
                pass
    except websockets.ConnectionClosed:
        print("\r  * Disconnected from server")


# ---------------------------------------------------------------------------
#  Send loop
# ---------------------------------------------------------------------------

async def send_messages(ws):
    loop = asyncio.get_event_loop()
    try:
        while True:
            text = await loop.run_in_executor(None, lambda: input("> "))
            text = text.strip()
            if not text:
                continue
            if text == "/quit":
                await ws.send(json.dumps({"action": "message", "text": "/quit"}))
                await ws.close()
                break
            await ws.send(json.dumps({"action": "message", "text": text}))
    except (EOFError, KeyboardInterrupt):
        await ws.close()
    except websockets.ConnectionClosed:
        pass


# ---------------------------------------------------------------------------
#  Connection setup
# ---------------------------------------------------------------------------

async def main():
    print("chat_client: connecting to", SERVER_URI)

    try:
        username = input("Username: ").strip()
        room = input("Room [general]: ").strip() or "general"
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        return

    if not username:
        print("Username required.")
        return

    try:
        async with websockets.connect(SERVER_URI) as ws:
            raw = await ws.recv()
            data = json.loads(raw)
            display_message(data)

            join_msg = json.dumps({"action": "join", "username": username, "room": room})
            await ws.send(join_msg)

            recv_task = asyncio.create_task(receive_messages(ws))
            send_task = asyncio.create_task(send_messages(ws))

            done, pending = await asyncio.wait(
                [recv_task, send_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    except ConnectionRefusedError:
        print("Could not connect. Is chat_server.py running?")
    except Exception as e:
        print(f"Connection error: {e}")

    print("Bye.")


if __name__ == "__main__":
    asyncio.run(main())
