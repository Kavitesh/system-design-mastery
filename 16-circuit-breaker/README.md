# Chapter 16 - Circuit Breaker & Retry Patterns

> Every distributed system fails. The difference between a minor blip and a full-blown outage is whether your services keep hammering a dead dependency or gracefully back off.

📖 Read the full article on Medium: *coming soon*
🎬 Watch the video explanation: *coming soon*

---

## Why Services Need Self-Preservation

Here's a scenario that plays out at every company eventually. Service A calls Service B. Service B gets slow - maybe a database connection pool is exhausted, maybe it's doing a deployment. Service A keeps sending requests. Each request ties up a thread waiting for a response that won't come. Service A's thread pool fills up. Now Service A can't handle *any* requests - not even the ones that don't involve Service B. Service C depends on Service A, so it starts failing too. Within minutes, one sluggish database has taken down your entire platform.

This is a **cascading failure**, and it's the default behavior of most systems. You have to actively prevent it.

Three patterns form the core of service resilience:

| Pattern | What It Does | Analogy |
|---------|-------------|---------|
| **Circuit Breaker** | Stops calling a failing service | Electrical circuit breaker tripping |
| **Retry with Backoff** | Retries failed calls with increasing delays | Knocking on a door, waiting longer each time |
| **Bulkhead** | Isolates failures to prevent spread | Watertight compartments on a ship |

These aren't academic exercises. Netflix built Hystrix around these patterns after repeated outages in the late 2000s. Every major cloud provider's SDK implements them. If you're building distributed systems, you'll use these patterns whether you know it or not.

---

## The Circuit Breaker Pattern

### The Core Idea

A circuit breaker wraps calls to an external service and monitors failures. When failures exceed a threshold, the breaker "trips" - it stops making calls entirely and fails fast. After a timeout period, it lets a single test request through. If that succeeds, the breaker resets. If it fails, the breaker stays open.

This is directly inspired by electrical circuit breakers. When current exceeds safe levels, the breaker trips to prevent a fire. You don't keep shoving electricity through a short circuit.

### Three States

```
    ┌─────────────────────────────────────────────────┐
    │                                                 │
    ▼                                                 │
┌────────┐   failure threshold   ┌────────┐   timeout   ┌───────────┐
│ CLOSED │ ──────exceeded──────> │  OPEN  │ ──expires──> │ HALF-OPEN │
│        │                       │        │              │           │
│ Normal │                       │ Fail   │              │ Testing   │
│ flow   │                       │ fast   │              │ recovery  │
└────────┘                       └────────┘              └───────────┘
    ▲                                                        │  │
    │              success                                   │  │
    └────────────────────────────────────────────────────────┘  │
                                                                │
    ┌───────────────────────────────────────────────────────────┘
    │              failure
    ▼
┌────────┐
│  OPEN  │
└────────┘
```

**CLOSED** - Everything is normal. Requests flow through to the downstream service. The breaker tracks recent failures. When the failure count exceeds a configured threshold (say, 5 failures in 60 seconds), it transitions to OPEN.

**OPEN** - The breaker has tripped. All requests fail immediately without even attempting to reach the downstream service. This is the "fail fast" behavior that prevents thread pool exhaustion and cascading failures. After a configured timeout (say, 30 seconds), it transitions to HALF-OPEN.

**HALF-OPEN** - The breaker is testing whether the downstream service has recovered. It allows one (or a small number of) requests through. If the test request succeeds, the breaker transitions back to CLOSED. If it fails, the breaker goes back to OPEN and the timeout resets.

### Key Configuration Parameters

| Parameter | Typical Value | What It Controls |
|-----------|--------------|-----------------|
| `failure_threshold` | 5 | Number of failures before the breaker opens |
| `reset_timeout` | 30 seconds | How long to wait before testing recovery |
| `success_threshold` | 1-3 | Successful calls in half-open before closing |
| `timeout` | 5 seconds | How long to wait for a response |
| `failure_rate_threshold` | 50% | Alternative - trip on failure percentage |

### What Counts as a Failure?

This is where teams mess up. Not every error should trip the circuit breaker.

**Should trip the breaker:**
- Connection timeouts (service is unreachable)
- HTTP 500, 502, 503 errors (service is broken)
- Socket exceptions (network issues)

**Should NOT trip the breaker:**
- HTTP 400 (bad request - that's your bug, not theirs)
- HTTP 404 (not found - also your problem)
- HTTP 429 (rate limited - use backoff, not a breaker)
- Business logic errors (invalid input, validation failures)

If you trip the breaker on 400 errors, a single bad request will shut down all traffic to that service. I've seen this happen in production. It's not fun.

### Fail-Fast Benefits

When the circuit is open, requests fail in microseconds instead of waiting for a timeout. Let's put numbers on this:

- **Without circuit breaker:** 100 requests/sec * 30-second timeout = 3,000 threads blocked
- **With circuit breaker:** 100 requests/sec * instant failure = 0 threads blocked

That's the difference between your service staying up and joining the cascading failure party.

---

## Retry Patterns

Retrying failed requests sounds simple. It's not. Naive retries cause more outages than they prevent.

### Simple Retry (Usually Wrong)

```
attempt 1: fail
attempt 2: fail (immediately)
attempt 3: fail (immediately)
give up
```

The problem: if a service is struggling under load, immediately retrying adds *more* load. You're making the problem worse. If 1,000 clients all retry immediately, the failing service goes from 1,000 requests/sec to 3,000 requests/sec. Congratulations, you've created a retry storm.

### Exponential Backoff (Better)

```
attempt 1: fail
wait 1 second
attempt 2: fail
wait 2 seconds
attempt 3: fail
wait 4 seconds
attempt 4: fail
wait 8 seconds
attempt 5: success!
```

Each retry waits twice as long as the previous one. This gives the failing service time to recover. AWS, Google Cloud, and Azure all require exponential backoff in their API clients.

The formula is straightforward:

```
delay = base_delay * (2 ^ attempt_number)
```

With a 1-second base delay: 1s, 2s, 4s, 8s, 16s, 32s...

Always cap the maximum delay. Nobody wants to wait 17 minutes (2^10 seconds) for a retry.

### Exponential Backoff with Jitter (Best)

Exponential backoff has a subtle problem: **thundering herd**. If 1,000 clients all start retrying at the same time with the same backoff schedule, they'll all retry at exactly the same moments - 1 second later, then 2 seconds later, then 4 seconds later. The service gets hammered in synchronized bursts.

Jitter adds randomness to the delay:

```
delay = base_delay * (2 ^ attempt_number) * random(0.5, 1.5)
```

Now those 1,000 clients spread their retries across the entire window instead of hitting at the same instant. AWS recommends this approach in their architecture best practices. It's not optional for high-traffic systems.

### Three Jitter Strategies

| Strategy | Formula | Use Case |
|----------|---------|----------|
| **Full jitter** | `random(0, base * 2^attempt)` | Most aggressive spread |
| **Equal jitter** | `base * 2^attempt / 2 + random(0, base * 2^attempt / 2)` | Guaranteed minimum wait |
| **Decorrelated jitter** | `min(cap, random(base, prev_delay * 3))` | Each retry independent |

AWS's analysis showed **full jitter** produces the best results for most scenarios - it completes all work with the fewest total calls.

### When NOT to Retry

- **Non-idempotent operations** - Retrying a payment charge could double-bill a customer. Only retry operations that are safe to repeat.
- **Authentication failures** - A 401 won't magically succeed on retry. You need a new token.
- **Validation errors** - The same bad input will fail every time.
- **Circuit breaker is open** - If the breaker has tripped, retrying is pointless.

---

## The Bulkhead Pattern

### Ship Compartments for Software

A bulkhead on a ship is a watertight wall dividing the hull into compartments. If one compartment floods, the others stay dry. The ship doesn't sink because of a single breach.

In software, a bulkhead isolates resource pools so one failing dependency can't consume all available resources.

### Thread Pool Isolation

The most common bulkhead implementation uses separate thread pools for each downstream service:

```
┌─────────────────────────────────────────────────┐
│                  Your Service                    │
│                                                  │
│  ┌─────────────┐ ┌─────────────┐ ┌────────────┐ │
│  │ Payment Pool │ │ Inventory   │ │ Email Pool │ │
│  │ (10 threads) │ │ Pool (15)   │ │ (5 threads)│ │
│  │              │ │             │ │            │ │
│  │ ██████░░░░  │ │ █████░░░░░░ │ │ ███░░      │ │
│  └──────┬──────┘ └──────┬──────┘ └─────┬──────┘ │
│         │               │              │         │
└─────────┼───────────────┼──────────────┼─────────┘
          ▼               ▼              ▼
    ┌──────────┐   ┌──────────┐   ┌──────────┐
    │ Payment  │   │Inventory │   │  Email   │
    │ Service  │   │ Service  │   │ Service  │
    └──────────┘   └──────────┘   └──────────┘
```

If the Payment Service goes down and all 10 threads in its pool get stuck waiting, Inventory and Email keep working with their own pools. Without bulkheads, all 30 threads would be shared, and a slow Payment Service could consume them all.

### Semaphore Isolation

A lighter-weight alternative to thread pools. Instead of dedicated threads, you use a semaphore (counter) to limit concurrent calls:

```python
# Max 10 concurrent calls to payment service
payment_semaphore = Semaphore(10)

if payment_semaphore.try_acquire():
    try:
        call_payment_service()
    finally:
        payment_semaphore.release()
else:
    raise BulkheadFullException("Payment pool exhausted")
```

| Approach | Pros | Cons |
|----------|------|------|
| **Thread pool** | True isolation, timeout support | Higher memory, context switching |
| **Semaphore** | Lightweight, less overhead | No timeout support, shared threads |

Netflix Hystrix used thread pool isolation by default. Resilience4j (its successor) defaults to semaphore isolation because it's more efficient for reactive/async architectures.

### Sizing Bulkheads

This is more art than science, but here's a starting formula:

```
pool_size = peak_requests_per_second * p99_latency_seconds * safety_margin
```

Example: 50 req/s * 0.2s latency * 2 (safety) = 20 threads

Start there, then tune based on actual metrics. Oversized pools waste memory. Undersized pools reject legitimate traffic.

---

## Timeout Patterns

Timeouts are the simplest resilience pattern and the most commonly botched.

### The Golden Rule

**Every outbound call needs a timeout.** Every HTTP request, every database query, every message queue publish. If you don't set a timeout, you're trusting that the remote service will always respond promptly. That trust will be betrayed.

### Timeout Budget

In a chain of service calls, timeouts need to account for the full chain:

```
Client ──(5s timeout)──> Service A ──(3s timeout)──> Service B ──(2s timeout)──> Database
```

Service A's timeout (3s) must be less than the client's timeout (5s). If Service A waits 3 seconds for Service B, it still has time to return a response or fallback before the client gives up.

If you set all timeouts to the same value (say, 30 seconds), the client times out at 30s, but Service A is still waiting for Service B, which is still waiting for the database. You've wasted resources on work that nobody wants anymore.

### Connection Timeout vs. Read Timeout

These are different things and should be configured separately:

| Timeout Type | What It Measures | Typical Value |
|-------------|-----------------|---------------|
| **Connection timeout** | Time to establish TCP connection | 1-3 seconds |
| **Read timeout** | Time to receive response data | 5-30 seconds |

A connection timeout of 30 seconds is almost always wrong. If a service doesn't accept your connection in 3 seconds, it's probably dead. Waiting longer just delays the inevitable.

---

## Fallback Strategies

When a call fails (and the circuit breaker is open or retries are exhausted), you need a plan B.

### Common Fallback Approaches

**1. Default values** - Return a reasonable default. A product recommendation service goes down? Show the top 10 most popular items instead.

**2. Cached data** - Return the last known good response. A pricing service is unavailable? Use the price from 5 minutes ago. It's probably still correct.

**3. Degraded functionality** - Skip the feature entirely. Can't load user reviews? Show the product page without reviews. The user can still buy.

**4. Fallback service** - Call an alternative provider. Primary payment processor down? Route to the backup processor.

**5. Queue for later** - Accept the request and process it asynchronously. Can't send the email right now? Put it in a queue and send it when the service recovers.

### The Fallback Decision Matrix

| Scenario | Recommended Fallback | Why |
|----------|---------------------|-----|
| Read operation, data rarely changes | Cached value | Stale data is better than no data |
| Read operation, data changes often | Default value | Old data could be misleading |
| Write operation, idempotent | Queue for retry | Don't lose the write |
| Write operation, non-idempotent | Fail with clear error | Don't risk duplicates |
| Critical operation (payment) | Fail with clear error | Never guess on money |

---

## Combining Patterns

These patterns work best together. Here's how they compose:

```
Incoming Request
      │
      ▼
┌──────────────┐
│   Bulkhead   │──── Pool full? ──> Fallback
│  (isolate)   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│Circuit Breaker│──── Open? ──> Fallback
│  (protect)   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│    Retry     │──── Max retries? ──> Fallback
│  (persist)   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Timeout    │──── Timed out? ──> Count as failure
│  (bound)     │
└──────┬───────┘
       │
       ▼
  Downstream
   Service
```

The order matters:

1. **Bulkhead first** - Reject before consuming resources
2. **Circuit breaker second** - Fail fast if the service is known to be down
3. **Retry third** - Try multiple times within the breaker's allowance
4. **Timeout last** - Bound each individual attempt

If you put retry outside the circuit breaker, retries won't count as additional failures. If you put the bulkhead inside the circuit breaker, you've already allocated resources before deciding to fail fast.

---

## Real-World Implementations

### Netflix Hystrix (Retired but Influential)

Hystrix defined the circuit breaker pattern for microservices. Key design decisions:

- Thread pool isolation by default (bulkhead)
- Rolling window for failure counting (last 10 seconds, not all-time)
- Request collapsing (batch multiple requests into one)
- Real-time metrics dashboard

Netflix retired Hystrix in 2018 but its ideas live on in every resilience library.

### Resilience4j (Current Standard for Java)

The spiritual successor to Hystrix with a more modular design:

- Decorator pattern instead of command pattern
- Semaphore isolation by default
- Works with reactive streams
- Smaller footprint - use only the patterns you need

### Python Ecosystem

Python doesn't have a single dominant resilience library, but several good options exist:

- **tenacity** - The go-to retry library. Excellent decorator API.
- **pybreaker** - Circuit breaker implementation.
- **aiobreaker** - Async circuit breaker for asyncio.
- **Built-in** - For learning, building your own is straightforward (see our code lab).

---

## Common Pitfalls

### 1. Retrying Non-Idempotent Operations

If your retry logic re-sends a payment charge and the first request actually succeeded (but the response was lost), you've just double-charged a customer. Only retry operations where repeating them is safe.

### 2. Shared Circuit Breakers

If Service A has two endpoints - one healthy, one broken - a single circuit breaker for all of Service A will block calls to the healthy endpoint. Use per-endpoint (or per-operation) breakers.

### 3. Testing Only the Happy Path

Your circuit breaker works perfectly in unit tests but you've never tested it under real failure conditions. Use chaos engineering tools (Chaos Monkey, Gremlin, Litmus) to intentionally break things in staging.

### 4. Forgetting the Monitoring

A circuit breaker that trips silently is almost useless. You need alerts when breakers open, dashboards showing breaker states, and metrics on fallback usage. If you don't know it's happening, you can't fix the root cause.

### 5. Circuit Breaker Thrashing

If the reset timeout is too short and the downstream service recovers slowly, the breaker will cycle rapidly between OPEN and HALF-OPEN. Each half-open test adds load to the struggling service. Set reasonable timeouts and consider increasing them on repeated failures.

### 6. Retry Amplification

In a chain A -> B -> C, if each service retries 3 times, a failure at C generates 3 retries from B, each of which generates 3 retries from A. That's 3 * 3 = 9 calls from a single user request. With longer chains, this grows exponentially. Only retry at one layer - usually the outermost.

---

## Key Takeaways

1. **Circuit breakers prevent cascading failures** by failing fast when a dependency is down.

2. **Always use exponential backoff with jitter** for retries. Naive retries cause retry storms that make outages worse.

3. **Bulkheads isolate failures** so one bad dependency can't take down your entire service.

4. **Every external call needs a timeout.** No exceptions. No "the service is fast so it doesn't need one."

5. **These patterns compose** - use them together in the right order: bulkhead, circuit breaker, retry, timeout.

6. **Have a fallback strategy** for every external dependency. Cached data, defaults, degraded functionality - anything is better than a 500 error.

7. **Monitor your resilience patterns.** A circuit breaker you don't monitor is a circuit breaker you don't know is tripped.

---

## What's Next?

- **Chapter 17:** [Disaster Recovery & Backup](../17-disaster-recovery/) - When prevention fails and you need to recover from actual disasters - RTO, RPO, backup strategies, and failover procedures.
