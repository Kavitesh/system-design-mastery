# Chapter 14 - Fault Tolerance & High Availability

> Everything fails. Hard drives die, networks partition, data centers flood. The question isn't whether your system will fail - it's whether your users will notice. Fault tolerance is the art of building systems that keep working when individual components don't.

📖 [Read on Medium](#) · 🎬 [Watch on YouTube](#)

---

## Why Fault Tolerance Matters

A single server running your application has roughly 99.9% uptime if you're lucky. That sounds good until you do the math: 0.1% downtime is 8 hours and 46 minutes per year. For an e-commerce site processing $100K/hour, that's $876K in lost revenue annually - from one server.

Now scale that to a system with 100 components. If each has 99.9% uptime independently, the probability that all 100 are up simultaneously is 0.999^100 = 90.5%. Your system is down nearly 10% of the time. That's 36.5 days per year.

Fault tolerance flips this equation. Instead of requiring everything to work, you design systems that work even when things don't.

```
Without fault tolerance:          With fault tolerance:
  System = A AND B AND C            System = A OR A' (redundant)
  All must work for                 Only one needs to work for
  system to work                    system to work

  99.9% x 99.9% x 99.9%            1 - (0.1% x 0.1%)
  = 99.7% uptime                   = 99.9999% uptime
```

---

## Availability vs Reliability vs Durability

These three terms get confused constantly. They measure different things.

| Term | Measures | Example |
|------|----------|---------|
| **Availability** | Can the system respond to requests right now? | "The API returned 200 OK" |
| **Reliability** | Does the system produce correct results over time? | "The API returned the right data every time" |
| **Durability** | Will stored data survive failures? | "My uploaded photo is still there after a disk crash" |

A system can be available but unreliable - it responds quickly but gives wrong answers 5% of the time. It can be reliable but unavailable - it always gives correct answers when it's up, but it's down every Tuesday morning for maintenance.

**Availability** is measured in "nines." **Reliability** is measured in mean time between failures (MTBF). **Durability** is measured in probability of data loss over time.

---

## The Nines of Availability (SLAs, SLOs, SLIs)

Before you can build a highly available system, you need to define what "highly available" means - in numbers.

### SLI, SLO, SLA - The Measurement Stack

```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│  SLA (Service Level Agreement)                           │
│  ├── Contract with customers                             │
│  ├── "We guarantee 99.9% uptime"                         │
│  ├── Has consequences: credits, refunds, penalties       │
│  └── Always looser than internal targets                 │
│                                                          │
│  SLO (Service Level Objective)                           │
│  ├── Internal target the team aims for                   │
│  ├── "We target 99.95% uptime" (tighter than SLA)        │
│  ├── Gives you a buffer before breaching the SLA         │
│  └── Used for engineering decisions and alerts            │
│                                                          │
│  SLI (Service Level Indicator)                           │
│  ├── The actual measured metric                          │
│  ├── "Last month uptime was 99.97%"                      │
│  ├── Feeds into dashboards and monitoring                │
│  └── Common SLIs: latency, error rate, throughput        │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### What the Nines Actually Mean

| Availability | Downtime/Year | Downtime/Month | Downtime/Week | Class |
|-------------|---------------|----------------|---------------|-------|
| 99% (two nines) | 3.65 days | 7.31 hours | 1.68 hours | Batch processing, internal tools |
| 99.9% (three nines) | 8.76 hours | 43.83 minutes | 10.08 minutes | Standard web apps |
| 99.95% | 4.38 hours | 21.92 minutes | 5.04 minutes | Business-critical apps |
| 99.99% (four nines) | 52.60 minutes | 4.38 minutes | 1.01 minutes | E-commerce, financial services |
| 99.999% (five nines) | 5.26 minutes | 25.9 seconds | 6.05 seconds | Telecom, healthcare, 911 systems |
| 99.9999% (six nines) | 31.56 seconds | 2.63 seconds | 0.6 seconds | Military, nuclear systems |

Each additional nine is roughly 10x harder and 10x more expensive to achieve. Going from 99.9% to 99.99% doesn't sound like much, but it means your total allowed downtime drops from 8.76 hours to 52.6 minutes per year. You can't even do a slow deployment in that window.

**The pragmatic take:** Most web applications should target three nines (99.9%). Four nines is worth it for payment processing and anything where downtime directly costs money per minute. Five nines is only justified for life-critical systems - and it requires fully automated recovery because humans can't respond fast enough.

---

## Failure Domains

A failure domain is the blast radius of a single failure. Understanding failure domains tells you what can break together.

```
┌──────────────────────────────────────────────────────────┐
│  Failure Domain Hierarchy                                │
│                                                          │
│  Process     ── one crash affects one instance           │
│    │                                                     │
│  Server      ── hardware failure takes down              │
│    │            all processes on that box                 │
│    │                                                     │
│  Rack        ── power supply or top-of-rack switch       │
│    │            failure kills 20-40 servers               │
│    │                                                     │
│  Data Center ── power outage, cooling failure,           │
│    │            or network cut affects thousands          │
│    │                                                     │
│  Region      ── natural disaster, major network          │
│                 partition affects all DCs in an area      │
└──────────────────────────────────────────────────────────┘
```

AWS structures this explicitly: each **Region** (us-east-1) contains multiple **Availability Zones** (us-east-1a, 1b, 1c), which are physically separate data centers with independent power, cooling, and networking. Deploying across AZs protects you from single-DC failures. Deploying across regions protects you from regional disasters.

**Rule of thumb:** Your redundancy should span at least one failure domain above the failure you're protecting against. If you're worried about server failures, replicate across racks. If you're worried about data center failures, replicate across AZs.

---

## Redundancy Patterns

Redundancy is the foundation of fault tolerance. If one thing can fail, have two. The question is how you coordinate them.

### Active-Active

All replicas handle traffic simultaneously. A load balancer distributes requests across them.

```
             ┌─────────────┐
             │Load Balancer │
             └──────┬───────┘
                    │
          ┌─────────┼─────────┐
          ▼         ▼         ▼
     ┌─────────┐ ┌─────────┐ ┌─────────┐
     │Server A │ │Server B │ │Server C │
     │ ACTIVE  │ │ ACTIVE  │ │ ACTIVE  │
     └─────────┘ └─────────┘ └─────────┘
       All three serve traffic
       If one dies, the other two absorb its load
```

**Pros:**
- Full use of all resources - no idle capacity
- Scales horizontally by adding more nodes
- No failover delay - traffic just redistributes

**Cons:**
- Stateful services need shared state or sticky sessions
- Data consistency across nodes is harder
- All nodes must be kept in sync

**Best for:** Stateless web servers, API gateways, microservices behind a load balancer.

### Active-Passive (Primary-Standby)

One replica handles all traffic. A standby sits idle, ready to take over if the primary fails.

```
     ┌─────────────┐         ┌─────────────┐
     │  Primary    │ ──────> │  Standby    │
     │  ACTIVE     │ replicate│  PASSIVE    │
     │  (serving)  │  state  │  (idle)     │
     └─────────────┘         └─────────────┘
                              Takes over when
                              primary fails
```

**Pros:**
- Simpler consistency model - one source of truth
- Standby can be a cheaper instance (cold standby)
- No split-brain risk

**Cons:**
- Wasted capacity - standby sits idle during normal operation
- Failover takes time (seconds to minutes)
- Data loss possible if replication is asynchronous

**Best for:** Databases (PostgreSQL primary-standby), stateful services, systems where consistency matters more than throughput.

### N+1 Redundancy

Run N nodes to handle your load, plus 1 extra for failures. If you need 3 servers to handle peak traffic, run 4. This is the minimum viable redundancy.

N+2 gives you room for one failure plus one maintenance operation simultaneously - important for rolling deployments.

---

## Failover Strategies

When a component fails, how does the system detect it and shift traffic?

### Heartbeat-Based Failover

The primary sends periodic "I'm alive" messages. If the standby stops receiving heartbeats, it assumes the primary is dead and takes over.

```
Normal operation:
  Primary ──♥──♥──♥──♥──♥──> Standby
            heartbeat every 5s

Failure:
  Primary ──♥──♥──✗  ✗  ✗    Standby
                  │           (no heartbeat for 15s)
                  │           "Primary is dead"
                  └──────────> Standby promotes itself
```

**The split-brain problem:** If the network between primary and standby fails (but both are still alive), the standby promotes itself. Now you have two primaries accepting writes - data corruption follows. Solutions include quorum-based decisions, fencing tokens, and STONITH ("Shoot The Other Node In The Head" - seriously, that's the real name).

### DNS-Based Failover

Update DNS records to point to a healthy server. Simple but slow - DNS TTLs mean clients may still route to the dead server for minutes.

### Load Balancer Health Checks

The load balancer actively checks backend health and removes unhealthy nodes from the rotation. This is the most common approach for stateless services.

```
Load Balancer checks /health every 10s:
  Server A: 200 OK    ✓ keep in rotation
  Server B: 200 OK    ✓ keep in rotation
  Server C: timeout   ✗ remove from rotation
  Server D: 503       ✗ remove from rotation
```

---

## Health Checks - Liveness vs Readiness

Not all health checks answer the same question. Kubernetes popularized the distinction between liveness and readiness probes, and it's useful everywhere.

### Liveness Probe

**Question:** "Is this process alive and not deadlocked?"

If a liveness check fails, the system should restart the process. The process is broken beyond recovery - kill it and start fresh.

```python
# Liveness check - is the process fundamentally working?
@app.route("/healthz")
def liveness():
    return {"status": "alive"}, 200
    # If this endpoint stops responding,
    # the process is hung - restart it
```

### Readiness Probe

**Question:** "Is this process ready to accept traffic?"

If a readiness check fails, stop sending traffic to this instance but don't restart it. The process is alive but temporarily unable to serve - maybe it's warming up a cache, loading a model, or waiting for a database connection.

```python
# Readiness check - can it serve requests right now?
@app.route("/ready")
def readiness():
    if not db.is_connected():
        return {"status": "not ready", "reason": "database unavailable"}, 503
    if not cache.is_warm():
        return {"status": "not ready", "reason": "cache warming"}, 503
    return {"status": "ready"}, 200
```

| Probe Type | Failure Action | Use Case |
|------------|---------------|----------|
| **Liveness** | Restart the process | Detect deadlocks, infinite loops, corrupted state |
| **Readiness** | Stop sending traffic | Warmup periods, dependency outages, overload |
| **Startup** | Wait longer before checking liveness | Slow-starting apps (loading large models, migrations) |

---

## Graceful Degradation

Graceful degradation means your system keeps working - at reduced functionality - rather than crashing entirely when a dependency fails. It's the difference between "the recommendation engine is down, so we show trending products instead" and "the recommendation engine is down, so the entire homepage 500s."

### Degradation Strategies

```
┌──────────────────────────────────────────────────────────┐
│  Full functionality                                      │
│  ├── Personalized recommendations                        │
│  ├── Real-time inventory counts                          │
│  ├── Dynamic pricing                                     │
│  ├── User reviews with sentiment analysis                │
│                                                          │
│  Degraded (recommendation service down)                  │
│  ├── Show trending/popular items instead                 │
│  ├── Real-time inventory counts                          │
│  ├── Dynamic pricing                                     │
│  ├── User reviews with sentiment analysis                │
│                                                          │
│  Degraded (recommendation + inventory services down)     │
│  ├── Show trending/popular items instead                 │
│  ├── Show "In Stock" / "Out of Stock" from cache         │
│  ├── Dynamic pricing                                     │
│  ├── User reviews with sentiment analysis                │
│                                                          │
│  Minimal (only core path works)                          │
│  ├── Static product catalog from cache                   │
│  ├── Shopping cart + checkout still works                 │
│  └── Everything else shows "temporarily unavailable"     │
└──────────────────────────────────────────────────────────┘
```

**Key principle:** Identify your critical path - the minimum set of operations that must work for the business to function. For an e-commerce site, that's browsing products and completing purchases. Everything else (reviews, recommendations, wishlists) is nice-to-have and should degrade gracefully.

### Fallback Patterns

| Pattern | How It Works | Example |
|---------|-------------|---------|
| **Cached fallback** | Serve stale cached data when the live source is down | Show yesterday's exchange rates when the API is down |
| **Default fallback** | Return a static default when the service is unavailable | Show generic recommendations when the ML model is down |
| **Feature toggle** | Disable non-critical features during outages | Turn off search suggestions during high load |
| **Queue and retry** | Accept the request now, process it later | Accept an order, charge the card after payment service recovers |

---

## Blast Radius Reduction

When something goes wrong, you want the explosion contained to the smallest possible area. Blast radius reduction is about drawing boundaries so that one failure doesn't cascade into a total outage.

### Cell-Based Architecture

Instead of one big system, split into independent cells that each serve a subset of users. If Cell 3 goes down, only its users are affected.

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Cell 1     │  │   Cell 2     │  │   Cell 3     │
│  Users A-H   │  │  Users I-P   │  │  Users Q-Z   │
│  Own DB      │  │  Own DB      │  │  Own DB      │
│  Own cache   │  │  Own cache   │  │  Own cache   │
│  Own servers │  │  Own servers │  │  Own servers  │
└──────────────┘  └──────────────┘  └──────────────┘
     ✓ OK              ✓ OK             ✗ DOWN
                                     Only 1/3 of users
                                     are affected
```

AWS uses this pattern internally. Each Availability Zone is an independent cell. A failure in us-east-1a doesn't propagate to us-east-1b.

### Bulkhead Pattern

Named after ship compartments that prevent flooding from spreading. Isolate components so that a failure in one doesn't consume all shared resources.

```
Without bulkheads:
  ┌────────────────────────────────┐
  │  Shared thread pool (100)      │
  │  ┌─────┐ ┌─────┐ ┌──────┐    │
  │  │Svc A│ │Svc B│ │Svc C │    │
  │  │ OK  │ │ OK  │ │ SLOW │    │
  │  └─────┘ └─────┘ └──────┘    │
  │                    ▲           │
  │  Svc C is slow, consuming     │
  │  90 of 100 threads.           │
  │  Svc A and B starve.          │
  └────────────────────────────────┘

With bulkheads:
  ┌──────────┐ ┌──────────┐ ┌──────────┐
  │ Pool: 33 │ │ Pool: 33 │ │ Pool: 33 │
  │  Svc A   │ │  Svc B   │ │  Svc C   │
  │   OK     │ │   OK     │ │  SLOW    │
  └──────────┘ └──────────┘ └──────────┘
  Svc C is slow but contained to its own pool.
  Svc A and B are unaffected.
```

---

## Chaos Engineering

You can't be confident your fault tolerance works unless you test it by actually breaking things in production. That's chaos engineering.

### Netflix Chaos Monkey

Netflix pioneered this approach in 2011. Chaos Monkey randomly kills production instances during business hours. The philosophy: if your system can't handle one random server dying on a Tuesday afternoon, it definitely can't handle a major outage at 3 AM on Black Friday.

The Simian Army expanded this concept:

| Tool | What It Does |
|------|-------------|
| **Chaos Monkey** | Randomly terminates instances |
| **Chaos Gorilla** | Simulates an entire AZ going offline |
| **Latency Monkey** | Injects artificial delays into network calls |
| **Conformity Monkey** | Finds instances that don't follow best practices |

### Running Chaos Experiments

A chaos experiment follows a scientific method:

1. **Define steady state** - "Our API returns 200 OK for 99.9% of requests with p99 latency under 200ms"
2. **Hypothesize** - "If we kill 1 of 3 API servers, the remaining 2 will absorb the load and steady state will hold"
3. **Inject failure** - Actually kill the server
4. **Observe** - Did the remaining servers absorb the load? Did any requests fail? Did latency spike?
5. **Learn** - If the hypothesis held, great. If not, fix the weakness and test again.

**Start small.** Don't begin chaos engineering by killing a database in production. Start by killing a single stateless service instance in staging. Build confidence gradually.

---

## Real-World Examples

### AWS Availability Zones

Each AWS region has 3+ AZs, each an independent data center with separate power, cooling, networking, and connectivity. Deploying across AZs is the most common approach to high availability on AWS.

```
us-east-1 Region
├── us-east-1a (AZ)  ──  Independent data center
├── us-east-1b (AZ)  ──  Independent data center
├── us-east-1c (AZ)  ──  Independent data center
└── Connected via low-latency private fiber
```

An RDS Multi-AZ deployment keeps a synchronous standby in a different AZ. If the primary AZ goes down, RDS automatically fails over to the standby - typically in under 60 seconds.

### Google's Spanner

Google Spanner achieves five nines (99.999%) availability by replicating data across multiple zones and using the Paxos consensus protocol. It's been measured at over 99.9999% in practice. The cost: every write requires a quorum of replicas to agree, which adds latency.

### GitHub's Approach

GitHub has published detailed post-mortems of their outages. A recurring theme: a database failure cascades because the application doesn't degrade gracefully. Their response has been to add more circuit breakers, read-only modes, and feature flags that let them selectively disable functionality during incidents.

---

## Common Pitfalls

| Pitfall | Why It Hurts | Fix |
|---------|-------------|-----|
| Redundancy without testing | Your failover hasn't been tested in 2 years - it probably doesn't work | Run regular failover drills and chaos experiments |
| Shared dependencies | Both "redundant" servers use the same DNS, the same config service, the same NTP server | Map your dependency tree and eliminate single points of failure |
| Cascading failures | One slow service consumes all threads and starves everything else | Use bulkheads, circuit breakers, and timeouts |
| Monitoring blind spots | The system is down but nobody knows because alerts aren't set up for that failure mode | Monitor from the user's perspective, not just server metrics |
| Treating availability as binary | "The site is up" vs "the site is down" misses partial failures | Measure availability per feature and per user segment |
| Ignoring correlated failures | "We have 3 replicas so we're safe" - but all 3 are in the same rack | Spread replicas across failure domains |
| Manual failover | Requiring a human to SSH in and run a script at 3 AM adds 15-30 minutes of downtime | Automate failover with health checks and orchestration |
| Over-engineering availability | Spending 6 months building five-nines infrastructure for an internal dashboard | Match your availability target to actual business requirements |

---

## Key Takeaways

1. **Availability is measured in nines** - each additional nine is 10x harder. Three nines (99.9%) is the sweet spot for most applications. Don't over-engineer.
2. **Redundancy needs to span failure domains** - two servers on the same rack don't protect against rack failures. Two servers in the same AZ don't protect against AZ failures.
3. **Active-active is better for stateless services, active-passive is better for databases** - pick the pattern that matches your consistency requirements.
4. **Liveness and readiness are different questions** - liveness asks "should I restart this?" Readiness asks "should I send traffic here?"
5. **Graceful degradation beats total failure every time** - serve cached data, show defaults, disable non-critical features. Keep the core path working.
6. **Test your fault tolerance or it doesn't exist** - chaos engineering isn't reckless. Untested redundancy is.
7. **Blast radius reduction is an architectural decision** - cells, bulkheads, and failure domain isolation limit the damage from any single failure.

---

## What's Next?

- **Chapter 15:** [Rate Limiting & Throttling](../15-rate-limiting/) - Protect your services from being overwhelmed by too much traffic - whether from legitimate spikes or malicious abuse.
- **Chapter 16:** [Circuit Breaker & Retry Patterns](../16-circuit-breaker/) - When a dependency is failing, stop hammering it. Circuit breakers and smart retries prevent cascading failures.
