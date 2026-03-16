# Chapter 23 - Monolith vs Microservices

> The most over-debated question in software architecture - and the answer is almost always "it depends on where you are in your journey."

📖 [Read on Medium](#) · 🎬 [Watch on YouTube](#)

---

## Why This Debate Matters

Every team will face this decision. Start wrong and you'll either strangle under a tangled monolith or drown in a sea of microservices you weren't ready to operate.

The monolith vs microservices debate isn't about which is "better." It's about which trade-offs match your team size, operational maturity, and business stage. Most teams pick microservices for the wrong reasons - they hear "Netflix does it" and assume it's the right call for their 5-person startup.

Here's the uncomfortable truth: **most companies should start with a monolith.** Even the companies famous for microservices started that way.

---

## The Monolith

A monolith is a single deployable unit. All your features - users, orders, payments, notifications - live in one codebase and deploy together.

```
┌──────────────────────────────────────────┐
│              Monolith App                │
│                                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│  │  Users   │ │  Orders  │ │ Products │ │
│  │  Module  │ │  Module  │ │  Module  │ │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ │
│       │             │            │       │
│       └─────────────┼────────────┘       │
│                     │                    │
│              ┌──────┴──────┐             │
│              │  Shared DB  │             │
│              └─────────────┘             │
└──────────────────────────────────────────┘
```

### Monolith Advantages

| Advantage | Why It Matters |
|-----------|---------------|
| Simple development | One repo, one build, one deploy |
| Easy debugging | Stack traces span the whole app |
| No network hops between modules | Function calls, not HTTP requests |
| ACID transactions | One database, real transactions |
| Easy refactoring | IDE can rename across the whole codebase |
| Low operational overhead | One thing to monitor, one thing to deploy |

### Monolith Disadvantages

| Disadvantage | Why It Hurts |
|-------------|-------------|
| Deployment coupling | A one-line change deploys the entire app |
| Scaling is all-or-nothing | Can't scale the orders module independently |
| Technology lock-in | Stuck with one language and framework |
| Team coupling | Developers step on each other's code |
| Growing complexity | After 500K lines, nobody understands all of it |
| Long build/test times | Everything builds together, everything tests together |

---

## Microservices

Microservices split your application into independently deployable services, each owning a specific business capability.

```
┌──────────┐    ┌──────────┐    ┌──────────┐
│  User    │    │  Order   │    │ Product  │
│  Service │    │  Service │    │  Service │
│  :5001   │    │  :5002   │    │  :5003   │
└────┬─────┘    └────┬─────┘    └────┬─────┘
     │               │              │
┌────┴─────┐    ┌────┴─────┐    ┌────┴─────┐
│ Users DB │    │Orders DB │    │Products  │
│          │    │          │    │   DB     │
└──────────┘    └──────────┘    └──────────┘
```

### Microservices Advantages

| Advantage | Why It Matters |
|-----------|---------------|
| Independent deployment | Ship the order service without touching users |
| Independent scaling | Scale the search service to 20 instances while auth stays at 2 |
| Technology freedom | Use Python for ML, Go for performance, Node for real-time |
| Team autonomy | Each team owns a service end-to-end |
| Fault isolation | User service crashing doesn't take down orders |
| Smaller codebases | Each service is small enough to understand fully |

### Microservices Disadvantages

| Disadvantage | Why It Hurts |
|-------------|-------------|
| Distributed system complexity | Network failures, partial failures, eventual consistency |
| Operational overhead | N services = N things to deploy, monitor, and debug |
| Data consistency | No cross-service ACID transactions |
| Testing difficulty | Integration tests require multiple services running |
| Service communication latency | HTTP calls are 1000x slower than function calls |
| Debugging across services | Distributed tracing, correlation IDs, log aggregation |

---

## The Decision Matrix

Don't pick microservices because they're trendy. Pick them when the trade-offs make sense.

| Factor | Choose Monolith | Choose Microservices |
|--------|----------------|---------------------|
| Team size | < 20 engineers | > 40 engineers with clear domain teams |
| Product maturity | Early stage, still finding product-market fit | Stable product, well-understood domains |
| Domain knowledge | Unclear boundaries, still learning | Well-defined bounded contexts |
| Deployment needs | Weekly releases are fine | Multiple deploys per day, per team |
| Scale requirements | Uniform traffic patterns | Wildly different scaling needs per feature |
| Operational maturity | No DevOps team, basic monitoring | CI/CD, container orchestration, observability |

**My strong opinion:** if you can't articulate exactly where your service boundaries should be, you're not ready for microservices. Bad boundaries are worse than no boundaries.

---

## Decomposition Strategies

When you do decide to split, how you draw the lines determines everything.

### By Business Capability

Map services to what the business does, not what the code does.

```
Business Capabilities:
├── User Management       -> User Service
├── Product Catalog       -> Product Service
├── Order Processing      -> Order Service
├── Payment Processing    -> Payment Service
├── Shipping/Fulfillment  -> Shipping Service
└── Notifications         -> Notification Service
```

This works well because business capabilities are stable. The way a company manages users doesn't change just because you refactored the database layer.

### By Subdomain (Domain-Driven Design)

Use DDD to identify bounded contexts. Each bounded context becomes a service candidate.

```
┌─────────────────────────────────────────────────────────┐
│                    E-Commerce Domain                    │
│                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │   Identity   │  │   Catalog   │  │   Ordering  │    │
│  │   Context    │  │   Context   │  │   Context   │    │
│  │             │  │             │  │             │    │
│  │  - User     │  │  - Product  │  │  - Order    │    │
│  │  - Auth     │  │  - Category │  │  - Cart     │    │
│  │  - Profile  │  │  - Search   │  │  - Checkout │    │
│  └─────────────┘  └─────────────┘  └─────────────┘    │
│                                                         │
│  ┌─────────────┐  ┌─────────────┐                      │
│  │   Payment   │  │  Shipping   │                      │
│  │   Context   │  │   Context   │                      │
│  │             │  │             │                      │
│  │  - Charge   │  │  - Tracking │                      │
│  │  - Refund   │  │  - Delivery │                      │
│  │  - Invoice  │  │  - Returns  │                      │
│  └─────────────┘  └─────────────┘                      │
└─────────────────────────────────────────────────────────┘
```

The key insight: a "User" in the Identity context has different attributes than a "User" in the Ordering context. Identity cares about email and password. Ordering cares about shipping address and payment method. They can diverge.

---

## Service Boundaries and Bounded Contexts

Getting boundaries wrong is the #1 cause of microservices failure. Bad boundaries create a **distributed monolith** - all the complexity of both architectures with the benefits of neither.

### Signs Your Boundaries Are Wrong

- Deploying Service A always requires deploying Service B
- Multiple services read/write the same database table
- A single business operation requires synchronous calls to 5+ services
- Teams constantly coordinate changes across service boundaries
- You have "shared" libraries that every service imports

### Boundary Heuristics

1. **Can this service be developed by one team?** If a service needs three teams to change it, it's too big or wrong-shaped.
2. **Can this service be deployed independently?** If deploying it always requires deploying another service, merge them.
3. **Does this service have its own data?** If two services share a database table, they're probably one service.
4. **Is the interface stable?** If the contract between two services changes every sprint, the boundary is wrong.

---

## Inter-Service Communication

Services need to talk. The two fundamental patterns are synchronous and asynchronous.

### Synchronous (Request-Response)

```
Order Service                    Product Service
     │                                │
     │── GET /products/42 ──────────> │
     │                                │ (check inventory)
     │ <── 200 OK {stock: 15} ────── │
     │                                │
```

- **Protocols:** REST/HTTP, gRPC
- **Pros:** Simple mental model, immediate response
- **Cons:** Temporal coupling (both services must be up), cascading failures, latency chains

### Asynchronous (Event-Driven)

```
Order Service           Message Queue          Inventory Service
     │                       │                        │
     │── OrderPlaced ──────> │                        │
     │                       │── OrderPlaced ────────>│
     │   (doesn't wait)      │                        │ (updates stock)
     │                       │ <── StockUpdated ───── │
```

- **Protocols:** Message queues (RabbitMQ, Kafka), event buses
- **Pros:** Loose coupling, resilience, services can be down temporarily
- **Cons:** Eventual consistency, harder to debug, message ordering challenges

### When to Use Which

| Scenario | Pattern | Why |
|----------|---------|-----|
| UI needs data now | Sync | User is waiting for a response |
| Placing an order | Async | Don't block the user while inventory updates |
| Service-to-service queries | Sync (gRPC) | Low latency, type safety |
| Event notifications | Async | Multiple consumers, decoupled |
| Long-running workflows | Async | Saga pattern, compensating transactions |

---

## The API Gateway Pattern

When you have 20 microservices, you don't want the client calling all 20 directly. An API gateway is a single entry point that routes, aggregates, and handles cross-cutting concerns.

```
                    ┌──────────────┐
   Client ────────> │  API Gateway │
                    │              │
                    │  - Routing   │
                    │  - Auth      │
                    │  - Rate Limit│
                    │  - Aggregate │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────┴──┐  ┌─────┴──┐  ┌─────┴──┐
        │ Users  │  │ Orders │  │Products│
        └────────┘  └────────┘  └────────┘
```

**What the gateway handles:**
- Request routing to the right service
- Response aggregation (combine data from multiple services into one response)
- Authentication and authorization
- Rate limiting
- Response caching
- Protocol translation (REST externally, gRPC internally)

**What the gateway should NOT do:**
- Business logic (that belongs in services)
- Data transformation beyond simple mapping
- Become a "god service" that everything depends on

---

## The Strangler Fig Migration Pattern

Nobody goes from monolith to microservices in a weekend. The strangler fig pattern lets you migrate incrementally.

Named after strangler fig trees that grow around existing trees and eventually replace them.

```
Phase 1: Monolith handles everything
┌──────────────────────────┐
│         Monolith         │
│  Users | Orders | Products│
└──────────────────────────┘

Phase 2: Extract one service, route traffic
┌──────────────┐    ┌──────────┐
│   Monolith   │    │ Product  │
│ Users|Orders │    │ Service  │
└──────────────┘    └──────────┘
       ▲                 ▲
       └────── Proxy ────┘
           (routes /products to new service)

Phase 3: Continue extracting
┌──────────┐  ┌──────────┐  ┌──────────┐
│  User    │  │  Order   │  │ Product  │
│  Service │  │  Service │  │  Service │
└──────────┘  └──────────┘  └──────────┘

Phase 4: Monolith is gone (or just a thin shell)
```

**Migration rules:**
1. Start with the service that has the clearest boundaries
2. Run old and new in parallel with feature flags
3. Migrate reads first, then writes
4. Keep the old code path as a fallback until you trust the new one
5. Don't try to extract everything at once - one service at a time

---

## Service Discovery

In a dynamic environment where services scale up and down, hardcoding URLs is a recipe for pain. Service discovery solves "where is Service X right now?"

### Client-Side Discovery

```
┌────────┐    1. Query     ┌──────────────┐
│ Client │ ──────────────> │   Service    │
│        │                 │   Registry   │
│        │ <────────────── │              │
│        │   2. Return     └──────────────┘
│        │      addresses       ▲   ▲
│        │                      │   │
│        │   3. Call directly    │   │ Register
│        │ ──────────┐    ┌─────┘   │
└────────┘           │    │         │
                ┌────┴────┴──┐ ┌────┴────┐
                │ Service A  │ │Service A│
                │ Instance 1 │ │Instance 2│
                └────────────┘ └─────────┘
```

### Server-Side Discovery

```
┌────────┐          ┌───────────────┐
│ Client │ ───────> │ Load Balancer │
└────────┘          │ (queries      │
                    │  registry)    │
                    └───────┬───────┘
                            │
                ┌───────────┼───────────┐
                │           │           │
          ┌─────┴──┐  ┌────┴───┐  ┌────┴───┐
          │ Svc A  │  │ Svc A  │  │ Svc A  │
          │ Inst 1 │  │ Inst 2 │  │ Inst 3 │
          └────────┘  └────────┘  └────────┘
```

**Tools:** Consul, etcd, ZooKeeper, Kubernetes DNS (built-in), Eureka

---

## Data Ownership - Database Per Service

This is the rule that hurts the most but matters the most: **each service owns its data.**

```
 Shared Database (Anti-Pattern)          Database Per Service
┌──────────┐  ┌──────────┐             ┌──────────┐  ┌──────────┐
│ Service A│  │ Service B│             │ Service A│  │ Service B│
└────┬─────┘  └────┬─────┘             └────┬─────┘  └────┬─────┘
     │              │                       │              │
     └──────┬───────┘                  ┌────┴─────┐  ┌────┴─────┐
            │                          │  DB - A  │  │  DB - B  │
     ┌──────┴──────┐                   └──────────┘  └──────────┘
     │  Shared DB  │
     └─────────────┘
     (coupling!)                       (independence!)
```

### Why This Matters

- **Shared DB = hidden coupling.** Service B changes a column, Service A breaks.
- **Schema changes require coordination.** You just recreated the monolith deployment problem.
- **Can't scale independently.** Service A needs a graph database, Service B needs a key-value store.

### How Services Share Data Without Sharing Databases

1. **API calls** - Service A asks Service B for data via its API
2. **Event streaming** - Service B publishes events, Service A maintains its own read model
3. **Data duplication** - Each service stores a copy of the data it needs (eventual consistency)

---

## The Distributed Monolith Anti-Pattern

This is what happens when you split into microservices but do it wrong. You get all the operational complexity of microservices with none of the benefits.

### Symptoms

| Symptom | What's Wrong |
|---------|-------------|
| Can't deploy one service without deploying others | Services are coupled at the deployment level |
| Shared database between services | Data coupling defeats independent scaling |
| Lock-step releases | Teams can't move independently |
| Synchronous chains of 5+ services | A single request fans out into a fragile chain |
| Shared "core" library with business logic | Logic coupling through shared code |
| One team owns multiple services | Organizational boundary doesn't match service boundary |

### How to Avoid It

1. Enforce database-per-service from day one
2. Use async communication where possible
3. Align teams to services (Conway's Law works both ways)
4. Make services genuinely deployable in isolation
5. Limit shared libraries to infrastructure concerns (logging, metrics) not business logic

---

## The Modular Monolith - The Middle Ground

There's a third option that doesn't get enough attention: **the modular monolith.** It's a monolith with strictly enforced module boundaries.

```
┌──────────────────────────────────────────┐
│           Modular Monolith               │
│                                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│  │  Users   │ │  Orders  │ │ Products │ │
│  │  Module  │ │  Module  │ │  Module  │ │
│  │          │ │          │ │          │ │
│  │ public   │ │ public   │ │ public   │ │
│  │  API     │ │  API     │ │  API     │ │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ │
│       │             │            │       │
│  Modules communicate through defined     │
│  internal APIs, NOT direct DB access     │
│                                          │
│              ┌──────────┐                │
│              │    DB    │                │
│              └──────────┘                │
└──────────────────────────────────────────┘
```

Shopify runs a massive modular monolith. They enforced module boundaries inside their Rails app so strictly that each module could theoretically be extracted into a service - but they choose not to because a monolith is simpler to operate at their scale.

**Benefits:**
- Strong boundaries without network overhead
- Can extract modules into services later if needed
- One deployment, one database, simple operations
- Enforced through code structure, not infrastructure

---

## Real-World Examples

### Amazon - Monolith to Microservices (2001-2006)

Amazon's original monolith was called "Obidos." As the team grew past hundreds of engineers, deployments became nightmares. They broke into small, two-pizza teams, each owning a service. This was before "microservices" was even a term.

**Key lesson:** They split because teams couldn't move independently, not because of scaling.

### Netflix - Full Microservices (2008-2012)

Netflix migrated from a monolithic Java app to hundreds of microservices on AWS after a major database corruption in 2008 took down the service for 3 days. They built most of the tooling the industry now relies on - Eureka (service discovery), Hystrix (circuit breakers), Zuul (API gateway).

**Key lesson:** They invested massively in tooling before and during the migration. Without that tooling, microservices at their scale would have been impossible.

### Shopify - Modular Monolith (2016-present)

Instead of going to microservices, Shopify enforced strict module boundaries inside their Ruby on Rails monolith. They created a tool called Packwerk that enforces dependency rules between modules at the code level.

**Key lesson:** You can get 80% of microservices' organizational benefits without the operational cost.

### Amazon Prime Video - Back to Monolith (2023)

Amazon Prime Video's monitoring team famously moved from microservices back to a monolith, reducing costs by 90%. Their distributed pipeline had too much inter-service communication overhead for their specific workload.

**Key lesson:** Architecture decisions aren't permanent. The right choice depends on the specific workload, and it can change over time.

---

## Common Pitfalls

| Pitfall | Why It Happens | Fix |
|---------|---------------|-----|
| Splitting too early | "Netflix does it" syndrome | Start monolith, split when team/domain boundaries are clear |
| Wrong service boundaries | Splitting by technical layer instead of business capability | Use DDD bounded contexts, not "API service" and "DB service" |
| Shared database | Feels easier than data duplication | Enforce database-per-service, use events for data sharing |
| No observability | Didn't invest in tooling before splitting | Set up distributed tracing, centralized logging, metrics first |
| Synchronous everything | Didn't think about failure modes | Use async messaging for operations that don't need immediate response |
| Nano-services | Went too small, every function is a service | Merge related services, aim for team-sized services |
| No API versioning | Breaking changes cascade | Version your APIs, maintain backward compatibility |
| Ignoring Conway's Law | Org structure doesn't match architecture | Align teams to services, or accept that your architecture will mirror your org chart |

---

## Key Takeaways

1. **Start with a monolith** unless you have a very specific reason not to. Monoliths are not legacy - they're simple.
2. **Microservices are an organizational scaling strategy**, not a technical one. You split when teams need independence, not when code is "too big."
3. **Boundaries are everything.** Bad service boundaries create a distributed monolith - the worst of both worlds.
4. **Database-per-service is non-negotiable** for true microservices. Shared databases kill independence.
5. **The modular monolith is underrated.** Enforce boundaries in code before you enforce them with network calls.
6. **Invest in tooling before splitting.** You need CI/CD, observability, and service discovery before you need microservices.
7. **Architecture is not permanent.** Amazon Prime Video went back to a monolith. That's not failure - that's engineering maturity.

---

## What's Next?

- **Chapter 24:** [Event-Driven Architecture](../24-event-driven/) - Designing systems around events instead of requests
- **Chapter 25:** [API Design](../25-api-design/) - REST, GraphQL, gRPC, and choosing the right API style
