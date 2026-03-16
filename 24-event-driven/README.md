# Chapter 24 - Event-Driven Architecture

> Stop asking "what happened?" and start reacting to what's happening. Event-driven architecture flips the entire control flow of your system inside out.

📖 [Read on Medium](#) · 🎬 [Watch on YouTube](#)

---

## What Is Event-Driven Architecture?

In a traditional request-driven system, Service A calls Service B and waits for a response. Service A knows about Service B. Service A depends on Service B being alive. Service A is tightly coupled to Service B.

Event-driven architecture breaks this coupling. Instead of calling other services directly, a service **emits an event** - a fact about something that happened - and moves on. Other services that care about that event pick it up and react independently.

```
Request-Driven (Synchronous)          Event-Driven (Asynchronous)
┌────────┐  call   ┌────────┐         ┌────────┐ emit  ┌───────────┐
│Order   │-------->│Payment │         │Order   │------>│Event Bus  │
│Service │<--------│Service │         │Service │       │           │
└────────┘ response└────────┘         └────────┘       └─────┬─────┘
     │                                                       │
     │  call   ┌────────┐                          ┌─────────┼──────────┐
     └-------->│Shipping│                          ▼         ▼          ▼
               │Service │                     ┌────────┐┌────────┐┌────────┐
               └────────┘                     │Payment ││Shipping││Email   │
                                              │Service ││Service ││Service │
                                              └────────┘└────────┘└────────┘
```

The order service doesn't know or care who's listening. Payment, shipping, and email services subscribe to the events they care about. You can add a tenth consumer next week without touching the order service.

---

## Event-Driven vs Request-Driven

| Dimension | Request-Driven | Event-Driven |
|-----------|---------------|--------------|
| Coupling | Producer knows consumer | Producer doesn't know consumers |
| Flow control | Caller waits for response | Fire and forget |
| Failure isolation | Caller fails if callee fails | Producer unaffected by consumer failures |
| Scaling | Scale the bottleneck service | Scale consumers independently |
| Debugging | Follow the call chain | Trace events across services |
| Latency | Synchronous - cumulative | Asynchronous - parallel processing |
| Data consistency | Immediate consistency | Eventual consistency |
| Complexity | Simple call graph | Event flows can be hard to follow |

Neither approach is universally better. Most real systems use both. Synchronous calls for queries where you need an immediate answer. Events for side effects that don't need to block the caller.

---

## Core Concepts

### Events

An event is an **immutable fact** about something that happened. Past tense. Not a command, not a request - a record.

- `OrderPlaced` - not `PlaceOrder`
- `PaymentReceived` - not `ProcessPayment`
- `UserRegistered` - not `RegisterUser`

This distinction matters. A command tells someone what to do. An event tells everyone what already happened. Commands have one target. Events have zero or many consumers.

```
Event Structure
┌────────────────────────────────────┐
│ event_type:  "OrderPlaced"         │
│ event_id:    "evt-a1b2c3"          │
│ timestamp:   "2024-01-15T10:30:00" │
│ source:      "order-service"       │
│ data: {                            │
│   order_id:    "ord-789"           │
│   customer_id: "cust-456"          │
│   total:       149.99              │
│   items:       ["SKU-A", "SKU-B"]  │
│ }                                  │
│ metadata: {                        │
│   correlation_id: "req-xyz"        │
│   version:        1                │
│ }                                  │
└────────────────────────────────────┘
```

Good events are self-contained. A consumer shouldn't need to call back to the producer to understand what happened.

---

### Event Bus / Event Broker

The event bus is the middleman. Producers publish events to it. Consumers subscribe to events from it. The bus handles routing, buffering, and delivery.

```
┌──────────┐     ┌───────────────────────────────┐     ┌──────────┐
│Producer A│────>│                               │────>│Consumer X│
└──────────┘     │        Event Broker            │     └──────────┘
┌──────────┐     │                               │     ┌──────────┐
│Producer B│────>│  - Routing                    │────>│Consumer Y│
└──────────┘     │  - Persistence                │     └──────────┘
┌──────────┐     │  - Delivery guarantees        │     ┌──────────┐
│Producer C│────>│  - Consumer group management  │────>│Consumer Z│
└──────────┘     └───────────────────────────────┘     └──────────┘
```

Real-world event brokers:

| Broker | Best For | Key Trait |
|--------|----------|-----------|
| **Apache Kafka** | High-throughput event streaming | Persistent log, replay capability |
| **RabbitMQ** | Traditional message queuing | Flexible routing, mature ecosystem |
| **AWS SNS/SQS** | Managed pub/sub + queuing | Zero ops, pay per message |
| **Redis Streams** | Lightweight event streaming | Fast, simple, already in your stack |
| **NATS** | Cloud-native microservices | Ultra-low latency, simple protocol |
| **Pulsar** | Multi-tenant streaming | Tiered storage, geo-replication |

Kafka dominates the event-driven space for a reason: it treats events as a persistent log you can replay, not ephemeral messages you consume and forget.

---

### Domain Events

Domain events represent meaningful business occurrences. They're the language your system speaks.

A well-designed event model mirrors the business domain:

```
E-Commerce Domain Events
├── Order
│   ├── OrderPlaced
│   ├── OrderConfirmed
│   ├── OrderShipped
│   └── OrderCancelled
├── Payment
│   ├── PaymentAuthorized
│   ├── PaymentCaptured
│   └── PaymentRefunded
├── Inventory
│   ├── StockReserved
│   ├── StockDepleted
│   └── StockReplenished
└── Customer
    ├── CustomerRegistered
    ├── AddressUpdated
    └── LoyaltyPointsEarned
```

Each event belongs to a bounded context. The order service defines `OrderPlaced`. The payment service defines `PaymentCaptured`. Nobody else gets to define or modify those events.

---

## Choreography vs Orchestration

When multiple services need to collaborate on a workflow, you have two choices: choreography or orchestration.

### Choreography

Each service listens for events and decides independently what to do. No central coordinator. Services react to each other like dancers who know the routine.

```
OrderPlaced ──> Payment Service ──> PaymentReceived
                                         │
                    ┌────────────────────┘
                    ▼
              Inventory Service ──> StockReserved
                                         │
                    ┌────────────────────┘
                    ▼
              Shipping Service ──> OrderShipped
                                         │
                    ┌────────────────────┘
                    ▼
              Notification Service ──> EmailSent
```

**Pros:** Loose coupling, easy to add new services, no single point of failure.

**Cons:** Hard to see the full workflow, debugging requires tracing events across services, complex error handling.

### Orchestration

A central orchestrator service coordinates the workflow. It tells each service what to do and tracks progress.

```
                    ┌─────────────────┐
                    │  Order          │
                    │  Orchestrator   │
                    └────────┬────────┘
                             │
            ┌────────────────┼────────────────┐
            ▼                ▼                ▼
      ┌──────────┐    ┌──────────┐    ┌──────────┐
      │ Payment  │    │Inventory │    │ Shipping │
      │ Service  │    │ Service  │    │ Service  │
      └──────────┘    └──────────┘    └──────────┘
```

**Pros:** Easy to understand the full workflow, centralized error handling, clear ownership of the process.

**Cons:** Central point of failure, tighter coupling to the orchestrator, orchestrator can become a god service.

### When to Use Which

| Scenario | Recommendation |
|----------|---------------|
| Simple workflow (2-3 steps) | Choreography |
| Complex workflow (5+ steps with conditions) | Orchestration |
| Steps must happen in strict order | Orchestration |
| Steps are independent side effects | Choreography |
| You need saga rollbacks | Orchestration (easier to manage) |
| You want maximum decoupling | Choreography |

Most mature systems use both. Choreography for simple, independent reactions. Orchestration for complex business workflows where order and error handling matter.

---

## Event Sourcing

Traditional systems store **current state**. Event sourcing stores **every event that led to the current state**.

Instead of updating a row in a database, you append an event to an immutable log. The current state is derived by replaying all events.

```
Traditional (State-Based)              Event Sourcing
┌─────────────────────┐                ┌─────────────────────────┐
│ Account: A-123      │                │ 1. AccountOpened($0)    │
│ Balance: $750       │                │ 2. MoneyDeposited($1000)│
│ Last Updated: Today │                │ 3. MoneyWithdrawn($200) │
└─────────────────────┘                │ 4. MoneyWithdrawn($50)  │
                                       │ 5. MoneyDeposited($500) │
  "What's the balance?"                │ 6. MoneyWithdrawn($500) │
  Answer: $750                         └─────────────────────────┘
                                         Replay: $0 + $1000
  "How did we get here?"                   - $200 - $50 + $500
  Answer: No idea.                         - $500 = $750

                                         "How did we get here?"
                                         Answer: Every detail.
```

### Why Event Sourcing?

1. **Complete audit trail** - You know exactly how the system got to its current state. Banking, healthcare, and compliance-heavy domains need this.

2. **Temporal queries** - "What was the account balance on March 5th?" Replay events up to that date.

3. **Event replay** - Bug in your projection logic? Fix the code, replay all events, rebuild the correct state.

4. **Debugging** - Reproduce any bug by replaying the exact sequence of events that caused it.

5. **New read models** - Need a new report? Build a new projection and replay historical events through it.

### The Cost

Event sourcing isn't free:

- **Storage grows forever** - Every event is kept. You'll need snapshotting for aggregates with thousands of events.
- **Eventual consistency** - Read models lag behind the write model.
- **Complexity** - Developers must think in events, not state mutations.
- **Schema evolution** - Old events must remain readable as your event schemas change.

---

## CQRS - Command Query Responsibility Segregation

CQRS splits your data model into two sides:

- **Write model (Command side)** - Handles creates, updates, deletes. Optimized for consistency and business rules.
- **Read model (Query side)** - Handles queries. Optimized for fast lookups with denormalized views.

```
                    ┌────────────────┐
  Commands ────────>│  Write Model   │────> Events ────┐
  (Create, Update)  │  (Normalized)  │                 │
                    └────────────────┘                 │
                                                       ▼
                                                ┌──────────────┐
                                                │  Projections │
                                                │  (Build read │
                                                │   models)    │
                                                └──────┬───────┘
                                                       │
                    ┌────────────────┐                 │
  Queries ─────────>│  Read Model    │<────────────────┘
  (Get, List, Search)│ (Denormalized) │
                    └────────────────┘
```

### Why CQRS?

Most systems have wildly different read and write patterns:

| Pattern | Writes | Reads |
|---------|--------|-------|
| E-commerce | Place order (complex validation) | Browse catalog (simple lookup) |
| Social media | Post content (small payload) | Load feed (aggregated from many sources) |
| Banking | Transfer money (strict consistency) | View statement (historical scan) |

A single model forced to serve both patterns does neither well. CQRS lets you optimize each side independently.

- Scale reads and writes separately
- Use different storage engines per side (SQL for writes, Elasticsearch for reads)
- Simplify each model - writes don't carry query concerns, reads don't carry validation logic

### CQRS + Event Sourcing

CQRS and event sourcing are often used together but they're independent patterns. You can use CQRS without event sourcing (just project changes to a read model). You can use event sourcing without CQRS (replay events to rebuild one model).

Together they're powerful: events from the write side feed projections that build read-optimized views.

---

## Event Schema Evolution

Events are immutable. You can't change a published event. But your schema will need to evolve. This is one of the hardest problems in event-driven systems.

### Strategies

| Strategy | How It Works | Trade-off |
|----------|-------------|-----------|
| **Versioned events** | `OrderPlacedV1`, `OrderPlacedV2` | Clear but consumers must handle multiple versions |
| **Upcasting** | Transform old events to new schema on read | Old events stay untouched, transformation logic grows |
| **Optional fields** | Add new fields as optional, never remove fields | Simple but schema bloats over time |
| **Schema registry** | Central registry validates event schemas | Prevents breaking changes, adds operational complexity |

The golden rule: **only make additive changes**. Add new optional fields. Never remove fields. Never rename fields. Never change field types. Treat your event schema like a public API - because it is one.

---

## Idempotent Event Handlers

Events can be delivered more than once. Network hiccups, consumer restarts, broker redeliveries - duplicate delivery is inevitable. Your handlers must be **idempotent**: processing the same event twice produces the same result.

```
Without Idempotency                 With Idempotency
┌──────────────────────┐            ┌──────────────────────┐
│ Event: PaymentReceived│           │ Event: PaymentReceived│
│ Amount: $100          │           │ ID: evt-abc-123       │
│                       │           │ Amount: $100          │
│ Handler:              │           │                       │
│   balance += 100      │           │ Handler:              │
│                       │           │   if evt-abc-123 seen:│
│ First:  balance = 100 │           │     skip (already     │
│ Dupe:   balance = 200 │ <-- BUG   │            processed) │
│                       │           │   else:               │
└──────────────────────┘            │     balance += 100    │
                                    │     mark evt-abc-123  │
                                    │            as seen    │
                                    └──────────────────────┘
```

Common idempotency techniques:

1. **Event ID tracking** - Store processed event IDs, skip duplicates
2. **Natural idempotency** - `SET balance = 750` is idempotent, `balance += 100` is not
3. **Idempotency keys** - Client-generated unique key per operation
4. **Version checks** - Only apply event if entity version matches expected version

---

## Eventual Consistency

Event-driven systems are eventually consistent by nature. The write model updates immediately. Read models update after projections process the event. There's a window where reads return stale data.

```
Timeline
────────────────────────────────────────────────────>
     │                    │              │
  Command:             Event:         Projection:
  "Place Order"        "OrderPlaced"   Read model
  Write model          published to    updated
  updated              event bus
     │                    │              │
     │<--- consistent --->│<-- stale --->│
     │                    │   window     │
```

This stale window is typically milliseconds to seconds. For most use cases, that's fine. For the ones where it's not, you have options:

- **Read-your-writes** - After a write, read from the write model (not the read model) for that user
- **Causal consistency** - Track event versions, show a loading state until the read model catches up
- **Synchronous projections** - Update the read model in the same transaction (sacrifices scalability)

---

## Real-World Event-Driven Systems

| Company | How They Use It | Scale |
|---------|----------------|-------|
| **LinkedIn** | Activity feed built on event sourcing - every action (like, share, comment) is an event replayed into personalized feeds | 900M+ members, billions of events/day |
| **Uber** | Trip lifecycle managed through events (ride requested, driver assigned, trip started, trip completed). Choreography between matching, pricing, and payments | 19M trips/day across 10,000+ cities |
| **Goldman Sachs** | Trade processing uses event sourcing for complete audit trails. Every price tick, order, and execution is an immutable event | Millions of trades, regulatory compliance |
| **Netflix** | Content delivery pipeline - encoding, quality checks, catalog updates all event-driven. Studio content goes through 40+ processing steps via events | 260M+ subscribers |
| **Shopify** | Order processing pipeline uses events to coordinate payments, inventory, shipping, notifications across merchant stores | 10%+ of US e-commerce |

---

## Comparison Table: When to Use What

| Pattern | Use When | Don't Use When |
|---------|----------|---------------|
| **Simple events** | Decoupling services, async side effects | You need synchronous responses |
| **Event sourcing** | Audit trail required, temporal queries, complex domains | Simple CRUD, high write volume with minimal reads |
| **CQRS** | Read/write patterns differ significantly, need to scale reads independently | Simple domain, small scale, team is unfamiliar |
| **Choreography** | Independent side effects, simple workflows | Complex multi-step processes, strict ordering |
| **Orchestration** | Complex workflows, saga pattern, clear error handling | Simple fire-and-forget notifications |

---

## Common Pitfalls

| Pitfall | Why It Hurts | Fix |
|---------|-------------|-----|
| Events as commands | Creates hidden coupling - producers expect specific reactions | Events describe facts, commands request actions |
| Missing idempotency | Duplicate events cause double charges, double notifications | Track processed event IDs, use natural idempotency |
| Too fine-grained events | Hundreds of tiny events per operation, high overhead | Group related changes into meaningful domain events |
| Too coarse-grained events | One giant event carries the whole world, breaks decoupling | Split by bounded context, include only relevant data |
| No event schema governance | Breaking changes crash consumers silently | Use a schema registry, enforce backward compatibility |
| Ignoring event ordering | Events processed out of order produce wrong state | Use partition keys, sequence numbers, or causal ordering |
| No dead letter queue | Failed events disappear forever | Always configure a DLQ for events that can't be processed |
| Event sourcing everything | Massive complexity for simple CRUD | Use event sourcing only where audit trail or replay matters |
| Synchronous mindset | Building request-response over events (request-reply anti-pattern) | If you need a response, make a synchronous call |

---

## Key Takeaways

1. **Events are facts, not commands** - Name them in past tense, make them self-contained, treat them as immutable contracts.

2. **Choreography for simple flows, orchestration for complex ones** - Don't dogmatically pick one. Use both where each fits.

3. **Event sourcing gives you superpowers** - Audit trails, temporal queries, and replay. But the complexity cost is real. Reserve it for domains that need it.

4. **CQRS isn't just for event sourcing** - Any system with different read/write patterns benefits from separate models.

5. **Idempotency isn't optional** - Events will be delivered more than once. Build every handler to survive duplicates.

6. **Eventual consistency is a feature, not a bug** - It enables scalability and decoupling. Design your UX around it instead of fighting it.

7. **Schema evolution is the hardest part** - Only make additive changes. Version your events. Use a schema registry in production.

---

## What's Next?

- **Chapter 25:** [Serverless Architecture](../25-serverless/) - Functions as a service, cold starts, and when serverless actually makes sense
