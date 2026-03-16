"""
WebSocket Chat Server
=====================
Bidirectional real-time chat. Messages are broadcast to all
connected clients over a persistent WebSocket connection.

Run: python websocket_chat.py
Connect: python websocket_client.py
"""

import asyncio
import websockets
import json
from datetime import datetime

connected = set()
history = []


async def handle_client(ws):
    client_id = f"user_{id(ws) % 10000}"
    connected.add(ws)
    print(f"  [+] {client_id} connected ({len(connected)} total)")

    await ws.send(json.dumps({
        "type": "system",
        "message": f"Welcome {client_id}! {len(connected)} user(s) online.",
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    }))

    # Send last 10 messages so new users have context
    for msg in history[-10:]:
        await ws.send(json.dumps(msg))

    await broadcast({
        "type": "system",
        "message": f"{client_id} joined the chat",
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    }, exclude=ws)

    try:
        async for raw in ws:
            data = json.loads(raw)
            msg = {
                "type": "chat",
                "user": client_id,
                "message": data.get("message", ""),
                "timestamp": datetime.now().strftime("%H:%M:%S"),
            }

            history.append(msg)
            if len(history) > 50:
                history.pop(0)

            print(f"  [{client_id}] {data.get('message', '')}")
            await broadcast(msg)

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        connected.discard(ws)
        await broadcast({
            "type": "system",
            "message": f"{client_id} left the chat",
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        })
        print(f"  [-] {client_id} disconnected ({len(connected)} total)")


async def broadcast(message, exclude=None):
    targets = [c for c in connected if c != exclude]
    if targets:
        payload = json.dumps(message)
        await asyncio.gather(*[c.send(payload) for c in targets])


async def main():
    print(f"\n  WebSocket Chat running on ws://localhost:5003")
    print(f"  Connect: python websocket_client.py")
    print(f"  Or from browser console:")
    print(f'    ws = new WebSocket("ws://localhost:5003")')
    print(f'    ws.onmessage = e => console.log(JSON.parse(e.data))')
    print(f'    ws.send(JSON.stringify({{message: "Hello!"}}))')
    print(f"\n  Waiting for connections...\n")

    async with websockets.serve(handle_client, "localhost", 5003):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
