# Chapter 33 - Code Lab: Chat System

Hands-on demos for chat system internals: WebSocket messaging, message persistence, and presence tracking.

## Files

| File | Purpose | Key Concepts |
|---|---|---|
| `chat_server.py` | WebSocket chat server with rooms and presence | WebSocket, fan-out, connection registry |
| `chat_client.py` | Terminal chat client | WebSocket client, async I/O |
| `message_store.py` | SQLite message storage with threading and pagination | Sequence numbers, conversation partitioning |
| `presence_service.py` | Heartbeat-based presence tracking | TTL-based status, heartbeat protocol |

## Setup

```bash
pip install websockets
```

Python 3.8+ required. The `websockets` library is the only external dependency. `message_store.py` and `presence_service.py` use only the standard library.

## Running the Chat Server + Client

**Terminal 1 - Start the server:**

```bash
python chat_server.py
```

**Terminal 2 - Connect a client:**

```bash
python chat_client.py
```

**Terminal 3 - Connect another client:**

```bash
python chat_client.py
```

The client prompts for a username and room name. Users in the same room see each other's messages in real time.

### Client Commands

| Command | Action |
|---|---|
| `/users` | List online users in the current room |
| `/history` | Show last 20 messages in the room |
| `/quit` | Disconnect and exit |
| anything else | Send as a chat message |

## Running Standalone Demos

**Message store demo (no server needed):**

```bash
python message_store.py
```

Creates an in-memory SQLite database, simulates two conversations with multiple messages, and demonstrates pagination - fetching messages in reverse chronological order with cursor-based navigation.

**Presence service demo (no server needed):**

```bash
python presence_service.py
```

Simulates users connecting, sending heartbeats, and going offline. Demonstrates TTL-based expiration and status transitions.

## Architecture Notes

These demos simplify the production design from the chapter README:

- SQLite stands in for Cassandra (same query patterns, smaller scale)
- In-memory dicts replace Redis (same data structures)
- Single-process server replaces distributed chat server fleet
- No Kafka - messages go directly from server to store

The core patterns are identical: sequence numbers for ordering, conversation-partitioned storage, heartbeat-based presence, and WebSocket fan-out for delivery.
