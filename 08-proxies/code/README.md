# Chapter 08 - Code Lab: Proxies & Reverse Proxies

Four hands-on demos that build proxy concepts from the ground up. Each file
is standalone - run it and start sending requests.

## Prerequisites

```bash
pip install flask requests
```

Python 3.9+. No external proxy software (Nginx, Envoy) required - everything
runs as Flask apps in threads.

---

## Lab 1: Reverse Proxy with Round-Robin (`reverse_proxy.py`)

A reverse proxy that distributes requests across three backend servers using
round-robin selection.

```bash
python reverse_proxy.py
```

**What it does:**
- Starts three backends on ports 6001, 6002, 6003
- Starts a reverse proxy on port 5000
- Each request is forwarded to the next backend in the cycle
- Injects `X-Forwarded-For` and `X-Forwarded-Host` headers

**Try it:**

```bash
# Hit the proxy five times and watch it rotate through backends
curl http://localhost:5000
curl http://localhost:5000
curl http://localhost:5000
curl http://localhost:5000
curl http://localhost:5000

# Try a sub-path
curl http://localhost:5000/api/test

# POST works too
curl -X POST http://localhost:5000/data
```

**What to observe:**
- The `backend` field in the JSON response cycles through backend-1, backend-2, backend-3
- The proxy terminal shows which backend handled each request and the latency
- Backends never see the client's real IP - they see the proxy's IP unless they read `X-Forwarded-For`

---

## Lab 2: API Gateway (`api_gateway.py`)

An API gateway with authentication, rate limiting, and path-based routing to
multiple backend services.

```bash
python api_gateway.py
```

**What it does:**
- Starts a user service on port 6010 and an order service on port 6011
- Starts the gateway on port 5050
- Validates Bearer tokens before forwarding
- Enforces a rate limit of 5 requests per 10-second window
- Routes `/api/users/*` to the user service and `/api/orders/*` to the order service

**Try it:**

```bash
# Without auth - gets 401
curl http://localhost:5050/api/users

# With valid token
curl -H "Authorization: Bearer secret-token-123" http://localhost:5050/api/users
curl -H "Authorization: Bearer secret-token-123" http://localhost:5050/api/users/1
curl -H "Authorization: Bearer secret-token-123" http://localhost:5050/api/orders

# Hit the rate limit (send 7 rapid requests)
for i in $(seq 1 7); do
  curl -s -H "Authorization: Bearer secret-token-123" http://localhost:5050/api/users | python -m json.tool
done

# Unmatched path - gets 404
curl -H "Authorization: Bearer secret-token-123" http://localhost:5050/api/payments
```

**What to observe:**
- The `X-RateLimit-Remaining` response header decreases with each request
- After 5 requests, you get a 429 with a `Retry-After` header
- Wait 10 seconds and the limit resets
- The gateway strips the `/api/users` prefix before forwarding to the user service

---

## Lab 3: Caching Proxy (`caching_proxy.py`)

A reverse proxy with an in-memory response cache, TTL-based expiration, and
manual cache invalidation.

```bash
python caching_proxy.py
```

**What it does:**
- Starts a backend on port 6020 that returns product data with timestamps
- Starts the caching proxy on port 5060
- Caches GET responses for 10 seconds (configurable)
- Exposes `/_cache/stats` and `/_cache/purge` endpoints

**Try it:**

```bash
# First request - cache MISS (note the generated_at timestamp)
curl http://localhost:5060/products

# Second request - cache HIT (same timestamp, faster response)
curl http://localhost:5060/products

# Check cache stats
curl http://localhost:5060/_cache/stats

# Wait 10+ seconds, then request again - cache expired, new timestamp
sleep 11
curl http://localhost:5060/products

# Manually purge a cache entry
curl -X POST "http://localhost:5060/_cache/purge?path=/products"

# Purge all entries
curl -X POST http://localhost:5060/_cache/purge

# Individual products are cached separately
curl http://localhost:5060/products/1
curl http://localhost:5060/products/2
curl http://localhost:5060/_cache/stats
```

**What to observe:**
- The `X-Cache` response header shows HIT or MISS
- The `X-Cache-TTL` header shows remaining time before expiration
- The `generated_at` timestamp in the response proves cached responses return stale data
- Cache stats show hit rate, miss count, and active entries
- POST/PUT/DELETE requests bypass the cache

---

## Lab 4: Full Demo (`proxy_demo.py`)

An automated demo that starts everything, sends a burst of requests, and
prints a summary with distribution stats and latency.

```bash
python proxy_demo.py
```

**What it does:**
- Starts three backends with different simulated delays (0ms, 50ms, 100ms)
- Starts a proxy on port 5070
- Sends 12 requests and logs which backend handled each one
- Prints a distribution summary table with request counts and average latencies

**What to observe:**
- Requests are evenly distributed (4 each) despite different backend speeds
- Backend-C has higher latency because of its 100ms simulated delay
- Round-robin doesn't account for backend speed - it just rotates
- In production, you'd use least-connections or weighted round-robin to handle this

---

## Port Summary

| Component | Port | Script |
|-----------|------|--------|
| Reverse proxy | 5000 | `reverse_proxy.py` |
| API gateway | 5050 | `api_gateway.py` |
| Caching proxy | 5060 | `caching_proxy.py` |
| Demo proxy | 5070 | `proxy_demo.py` |
| Backends (reverse proxy) | 6001-6003 | `reverse_proxy.py` |
| User service | 6010 | `api_gateway.py` |
| Order service | 6011 | `api_gateway.py` |
| Product backend | 6020 | `caching_proxy.py` |
| Demo backends | 7001-7003 | `proxy_demo.py` |

Each script uses unique ports, so you can run them all simultaneously without
conflicts.

---

## Key Takeaways from the Labs

1. **Round-robin is simple but blind.** It doesn't know if a backend is slow or overloaded. Production proxies use health checks and smarter algorithms.

2. **Authentication at the gateway means services don't reimplement it.** The user and order services have zero auth code - the gateway handles it all.

3. **Caching eliminates redundant work.** The backend generates a timestamp to prove this - cached responses return the same timestamp until the TTL expires.

4. **X-Forwarded-For is critical.** Without it, every backend request appears to come from the proxy's IP. Rate limiting, audit logs, and geo-routing all break.

5. **These are teaching demos, not production code.** Real proxies (Nginx, Envoy, HAProxy) handle thousands of concurrent connections, TLS termination, hot reloads, and health checks. These Flask demos show the concepts without the infrastructure.
