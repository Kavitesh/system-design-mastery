"""
API Pattern Comparison
======================
Side-by-side comparison of REST, GraphQL, gRPC, and real-time
communication patterns. No server needed - just run it.

Run: python api_comparison.py
"""


def main():
    print("""
======================================================================
  API & COMMUNICATION PATTERNS - SIDE-BY-SIDE COMPARISON
======================================================================

----------------------------------------------------------------------
  1. REST vs GraphQL - Fetching a user with their orders
----------------------------------------------------------------------

  REST (3 HTTP requests, potential over-fetching):

    Request 1: GET /api/v1/users/42
    Response:  { "id": 42, "name": "Alice", "email": "...",
                 "bio": "...", "avatar": "...", ... }

    Request 2: GET /api/v1/users/42/orders
    Response:  [{ "id": 1, "total": 59.99, "items": [...],
                 "shipping": {...}, "billing": {...}, ... }]

    Request 3: GET /api/v1/users/42/profile
    Response:  { "theme": "dark", "language": "en", ... }

    Total: 3 round trips, lots of unused fields returned


  GraphQL (1 HTTP request, exact fields):

    Request:  POST /graphql
    Body:     { "query": "{
                  user(id: 42) {
                    name
                    orders { total }
                  }
                }" }

    Response: { "user": {
                  "name": "Alice",
                  "orders": [{ "total": 59.99 }]
                } }

    Total: 1 round trip, only the fields you asked for

----------------------------------------------------------------------
  2. REST+JSON vs gRPC+Protobuf - Message size comparison
----------------------------------------------------------------------

  REST + JSON (~120 bytes):
    { "id": 42, "name": "Alice", "email": "alice@example.com",
      "orders_count": 5, "active": true }

  gRPC + Protobuf (~35 bytes):
    [binary: 08 2A 12 05 41 6C 69 63 65 1A 11 ...]

  Protobuf schema (.proto file):
    message User {
      int32 id = 1;
      string name = 2;
      string email = 3;
      int32 orders_count = 4;
      bool active = 5;
    }

  Result: ~3.4x smaller payload, faster serialization

----------------------------------------------------------------------
  3. Real-Time Patterns - How the server reaches the client
----------------------------------------------------------------------""")

    patterns = [
        ("Short Polling", "Client -> Server", "Simple dashboards, status checks"),
        ("Long Polling",  "Client -> Server", "Basic chat, notifications"),
        ("SSE",           "Server -> Client", "Live feeds, stock tickers"),
        ("WebSocket",     "Bidirectional",    "Chat, gaming, collaboration"),
        ("Webhook",       "Server -> Server", "Payment callbacks, CI/CD triggers"),
    ]

    print(f"\n  {'Pattern':<15} {'Direction':<20} {'Best for'}")
    print(f"  {'-------':<15} {'---------':<20} {'--------'}")
    for name, direction, use in patterns:
        print(f"  {name:<15} {direction:<20} {use}")

    print("""
----------------------------------------------------------------------
  4. Decision Flowchart - Which pattern should you use?
----------------------------------------------------------------------

  Start here:
  |
  +-- Need real-time updates?
  |   |
  |   +-- Bidirectional? -----------> WebSocket
  |   +-- Server-to-client only? ---> SSE
  |   +-- Between backend services? > Webhook
  |
  +-- Request-response?
  |   |
  |   +-- Internal microservices? --> gRPC
  |   +-- Complex nested data? -----> GraphQL
  |   +-- Simple CRUD / public API? > REST
  |
  +-- When in doubt ----------------> REST

----------------------------------------------------------------------
  5. Quick Performance Reference
----------------------------------------------------------------------""")

    rows = [
        ("REST",      "Medium",   "Medium", "JSON",   "Low"),
        ("GraphQL",   "Medium",   "Medium", "JSON",   "Medium"),
        ("gRPC",      "Low",      "High",   "Binary", "Medium"),
        ("WebSocket", "Very Low", "High",   "Any",    "High"),
        ("SSE",       "Low",      "Medium", "Text",   "Low"),
        ("Webhook",   "Varies",   "Varies", "JSON",   "Medium"),
    ]

    print(f"\n  {'Pattern':<15} {'Latency':<12} {'Throughput':<12} {'Payload':<10} {'Complexity'}")
    print(f"  {'-------':<15} {'-------':<12} {'----------':<12} {'-------':<10} {'----------'}")
    for row in rows:
        print(f"  {row[0]:<15} {row[1]:<12} {row[2]:<12} {row[3]:<10} {row[4]}")

    print("\n======================================================================\n")


if __name__ == "__main__":
    main()
