# Networking Essentials - Code Lab

Hands-on demos that let you see TCP, DNS, HTTP, and WebSockets in action.

## What's Included

| File | Description |
|------|-------------|
| `tcp_handshake_demo.py` | Visualizes a TCP three-way handshake between client and server |
| `dns_lookup.py` | Performs DNS resolution and shows the full record breakdown |
| `http_inspector.py` | Makes HTTP requests and displays headers, timing, and status codes |
| `websocket_chat.py` | A minimal WebSocket chat server and client demo |
| `latency_comparison.py` | Measures and compares real-world latency of different operations |

## Prerequisites

```bash
pip install flask requests websockets
```

## Running the Demos

### 1. TCP Handshake Demo

Starts a TCP server and client, logs every step of the connection:

```bash
python tcp_handshake_demo.py
```

### 2. DNS Lookup

Resolves a domain and prints all record types:

```bash
python dns_lookup.py google.com
python dns_lookup.py myapp.com
```

### 3. HTTP Inspector

Makes a request and shows the full HTTP conversation:

```bash
python http_inspector.py https://httpbin.org/get
python http_inspector.py https://httpbin.org/status/404
```

### 4. WebSocket Chat

Run the server, then connect with one or more clients:

```bash
# Terminal 1 - start WebSocket server
python websocket_chat.py server

# Terminal 2 - connect as a client
python websocket_chat.py client

# Terminal 3 - connect as another client
python websocket_chat.py client
```

### 5. Latency Comparison

Measures real latency for DNS, TCP, HTTP, and disk operations:

```bash
python latency_comparison.py
```
