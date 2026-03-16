"""
WebSocket Chat Demo
===================
A minimal WebSocket chat server and client demonstrating
full-duplex communication - both sides can send anytime.

Run:
  # Terminal 1 - start server
  python websocket_chat.py server

  # Terminal 2 - connect as a client
  python websocket_chat.py client

  # Terminal 3 - another client (messages broadcast to all)
  python websocket_chat.py client
"""

import sys
import asyncio
import json
import time

import websockets


HOST = "localhost"
PORT = 8765
CLIENTS = set()


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

async def handle_client(websocket):
    CLIENTS.add(websocket)
    client_id = f"User-{id(websocket) % 10000}"
    print(f"[SERVER] {client_id} connected ({len(CLIENTS)} total clients)")

    # Notify everyone about new user
    join_msg = json.dumps({
        "type": "system",
        "message": f"{client_id} joined the chat",
        "timestamp": time.time()
    })
    await broadcast(join_msg, exclude=None)

    try:
        async for raw_message in websocket:
            data = json.loads(raw_message)
            print(f"[SERVER] {client_id}: {data.get('message', '')}")

            # Broadcast to all clients
            broadcast_msg = json.dumps({
                "type": "chat",
                "from": client_id,
                "message": data.get("message", ""),
                "timestamp": time.time()
            })
            await broadcast(broadcast_msg, exclude=websocket)

    except websockets.ConnectionClosed:
        pass
    finally:
        CLIENTS.discard(websocket)
        print(f"[SERVER] {client_id} disconnected ({len(CLIENTS)} remaining)")

        leave_msg = json.dumps({
            "type": "system",
            "message": f"{client_id} left the chat",
            "timestamp": time.time()
        })
        await broadcast(leave_msg, exclude=None)


async def broadcast(message: str, exclude=None):
    for client in CLIENTS.copy():
        if client != exclude:
            try:
                await client.send(message)
            except websockets.ConnectionClosed:
                CLIENTS.discard(client)


async def run_server():
    print("=" * 55)
    print("  WEBSOCKET CHAT SERVER")
    print("=" * 55)
    print(f"\nListening on ws://{HOST}:{PORT}")
    print("Waiting for clients to connect...\n")
    print("How WebSockets differ from HTTP:")
    print("  - HTTP: client sends request, server sends response (half-duplex)")
    print("  - WebSocket: both sides send anytime (full-duplex)")
    print("  - Connection stays open - no repeated handshakes")
    print("-" * 55)
    print()

    async with websockets.serve(handle_client, HOST, PORT):
        await asyncio.Future()  # Run forever


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

async def run_client():
    print("=" * 55)
    print("  WEBSOCKET CHAT CLIENT")
    print("=" * 55)
    print(f"\nConnecting to ws://{HOST}:{PORT}...")

    try:
        async with websockets.connect(f"ws://{HOST}:{PORT}") as ws:
            print("Connected! Type messages and press Enter.")
            print("Type 'quit' to disconnect.\n")

            # Task to receive messages
            async def receive():
                try:
                    async for raw in ws:
                        data = json.loads(raw)
                        if data["type"] == "system":
                            print(f"  ** {data['message']} **")
                        else:
                            print(f"  [{data['from']}]: {data['message']}")
                except websockets.ConnectionClosed:
                    print("\nServer closed the connection.")

            # Task to send messages
            async def send():
                loop = asyncio.get_event_loop()
                while True:
                    message = await loop.run_in_executor(None, input)
                    if message.lower() == "quit":
                        print("Disconnecting...")
                        await ws.close()
                        break
                    msg = json.dumps({"message": message})
                    await ws.send(msg)

            # Run both concurrently
            receive_task = asyncio.create_task(receive())
            send_task = asyncio.create_task(send())
            await asyncio.wait(
                [receive_task, send_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

    except ConnectionRefusedError:
        print(f"\nCould not connect to ws://{HOST}:{PORT}")
        print("Make sure the server is running: python websocket_chat.py server")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python websocket_chat.py server   # Start the chat server")
        print("  python websocket_chat.py client   # Connect as a client")
        return

    mode = sys.argv[1].lower()

    if mode == "server":
        asyncio.run(run_server())
    elif mode == "client":
        asyncio.run(run_client())
    else:
        print(f"Unknown mode: {mode}. Use 'server' or 'client'.")


if __name__ == "__main__":
    main()
