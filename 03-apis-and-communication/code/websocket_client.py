"""
WebSocket Chat Client
=====================
Connects to the chat server and lets you send/receive messages.

Start the server first:  python websocket_chat.py
Then run this client:    python websocket_client.py
"""

import asyncio
import websockets
import json


async def chat_client():
    uri = "ws://localhost:5003"
    print(f"  Connecting to {uri}...")

    try:
        async with websockets.connect(uri) as ws:
            print("  Connected! Type messages and press Enter. (Ctrl+C to quit)\n")

            async def receive():
                async for raw in ws:
                    msg = json.loads(raw)
                    if msg["type"] == "system":
                        print(f"  ** {msg['message']} **")
                    else:
                        print(f"  [{msg['timestamp']}] {msg['user']}: {msg['message']}")

            async def send():
                loop = asyncio.get_event_loop()
                while True:
                    message = await loop.run_in_executor(None, input, "")
                    if message.strip():
                        await ws.send(json.dumps({"message": message.strip()}))

            await asyncio.gather(receive(), send())

    except ConnectionRefusedError:
        print("  Could not connect. Is the server running?")
        print("  Start it first: python websocket_chat.py")
    except KeyboardInterrupt:
        print("\n  Disconnected.")


if __name__ == "__main__":
    asyncio.run(chat_client())
