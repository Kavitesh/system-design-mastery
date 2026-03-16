# APIs & Communication Patterns - Code Lab

Hands-on demos for REST, GraphQL, SSE, WebSockets, and Webhooks.

## What's Included

| File | Description |
|------|-------------|
| `rest_api.py` | CRUD API with pagination, versioning, proper status codes |
| `graphql_api.py` | GraphQL server with nested queries and mutations |
| `sse_server.py` | Server-Sent Events stock ticker (real-time push) |
| `websocket_chat.py` | WebSocket chat server (bidirectional real-time) |
| `websocket_client.py` | Terminal chat client for the WebSocket server |
| `webhook_demo.py` | Webhook registration, delivery with retries, HMAC verification |
| `api_comparison.py` | Side-by-side comparison of all patterns (no server needed) |

## Prerequisites

```bash
pip install flask requests graphql-core websockets
```

## Running the Demos

### 1. API Pattern Comparison (start here)

No server needed - prints a formatted comparison of all patterns:

```bash
python api_comparison.py
```

### 2. REST API

A standard CRUD API for managing books:

```bash
python rest_api.py

# In another terminal:
curl http://localhost:5000/api/v1/books
curl -X POST http://localhost:5000/api/v1/books \
     -H "Content-Type: application/json" \
     -d '{"title": "DDIA", "author": "Kleppmann", "year": 2017}'
```

### 3. GraphQL API

Query exactly the fields you need - no over-fetching:

```bash
python graphql_api.py

# In another terminal - get only titles (no other fields):
curl -X POST http://localhost:5001/graphql \
     -H "Content-Type: application/json" \
     -d '{"query": "{ books { title } }"}'

# Nested query - book with author in one request:
curl -X POST http://localhost:5001/graphql \
     -H "Content-Type: application/json" \
     -d '{"query": "{ book(id: \"b1\") { title, author { name, country } } }"}'
```

### 4. SSE Stock Ticker

Watch live stock prices pushed from server to client:

```bash
python sse_server.py

# Open http://localhost:5002 in your browser for the live UI
# Or see the raw event stream:
curl -N http://localhost:5002/events
```

### 5. WebSocket Chat

Full-duplex bidirectional messaging:

```bash
# Terminal 1 - start server
python websocket_chat.py

# Terminal 2 - connect as user 1
python websocket_client.py

# Terminal 3 - connect as user 2
python websocket_client.py
```

### 6. Webhook Demo

Event-driven notifications with HMAC signature verification:

```bash
python webhook_demo.py

# Trigger a payment (webhook fires automatically):
curl -X POST http://localhost:5004/payments/charge \
     -H "Content-Type: application/json" \
     -d '{"amount": 99.99, "customer": "alice"}'
```
