# System Design Mastery

> A comprehensive, visual, and hands-on guide to mastering system design - from fundamentals to real-world architectures.

```
  ┌─────────────────────────────────────────────────────────┐
  │                  SYSTEM DESIGN MASTERY                  │
  │                                                         │
  │   Fundamentals ──▶ Data at Scale ──▶ Reliability        │
  │        │                                    │           │
  │        ▼                                    ▼           │
  │   Distributed  ──▶  Architecture  ──▶  Case Studies     │
  │    Systems          Patterns                            │
  └─────────────────────────────────────────────────────────┘
```

## What Is System Design?

System design is the process of defining the architecture, components, and interactions of a system to meet specific requirements. It is how engineers decide the structure of software that serves millions of users, handles terabytes of data, and stays available 24/7.

When you open Instagram, a single tap triggers a chain of events - a load balancer routes your request, an app server processes it, a cache serves the data if available, otherwise a database is queried, images are pulled from a CDN, and a response is assembled and sent back in under 200 milliseconds. Designing that entire flow - deciding where each piece lives, how they communicate, what happens when something fails - that is system design.

### Why Does It Matter?

- **Interviews** - System design rounds are a make-or-break part of senior engineering interviews at top companies. You are expected to design systems like URL shorteners, chat apps, or video platforms on a whiteboard in 45 minutes.
- **Real-world engineering** - Knowing how to pick the right database, when to add a cache, how to shard data, or why you need a message queue is what separates a coder from an architect.
- **Scale thinking** - Code that works for 100 users breaks at 100,000. System design teaches you to think about load, failure, latency, and cost before writing a single line of code.

### Who Should Learn This?

- Developers preparing for **system design interviews**
- Engineers transitioning from writing code to **designing architecture**
- Backend developers who want to understand **how large-scale systems actually work**
- Anyone curious about how apps like YouTube, Uber, or WhatsApp handle billions of requests

### How This Repo Is Structured

This repo takes a building-block approach. You start with the fundamentals (scaling, networking, databases), layer on advanced concepts (replication, consensus, event-driven architecture), and finish by designing real-world systems from scratch. Each chapter gives you theory, diagrams, and working code you can run locally.

---

## What's Inside

Each chapter includes:

| Resource | Description |
|----------|-------------|
| **Concept Guide** | In-depth explanation with Mermaid diagrams and visual illustrations |
| **Code Lab** | Working demo code you can run, modify, and learn from |
| **Medium Article** | Polished blog post (linked from chapter README) |
| **YouTube Video** | Video walkthrough (linked from chapter README) |

## Table of Contents

### Part I  - Fundamentals & Building Blocks

| # | Topic |
|---|-------|
| 01 | [Scalability Basics](01-scalability-basics/) 
| 02 | [Networking Essentials](02-networking-essentials/) 
| 03 | [APIs & Communication Patterns](03-apis-and-communication/) 
| 04 | [Databases  - SQL & NoSQL](04-databases/) 
| 05 | [Caching Strategies](05-caching/) 
| 06 | [Load Balancing](06-load-balancing/) 
| 07 | [Message Queues & Event Streaming](07-message-queues/) 
| 08 | [Proxies & Reverse Proxies](08-proxies/) 

### Part II  - Data at Scale

| # | Topic |
|---|-------|
| 09 | [Data Partitioning & Sharding](09-sharding/) 
| 10 | [Database Replication](10-replication/) 
| 11 | [CAP Theorem & Consistency Models](11-cap-theorem/) 
| 12 | [Data Storage & Object Stores](12-data-storage/) 
| 13 | [Search & Indexing](13-search-indexing/) 

### Part III  - Reliability & Resilience

| # | Topic |
|---|-------|
| 14 | [Fault Tolerance & High Availability](14-fault-tolerance/) 
| 15 | [Rate Limiting & Throttling](15-rate-limiting/) 
| 16 | [Circuit Breaker & Retry Patterns](16-circuit-breaker/) 
| 17 | [Disaster Recovery & Backup](17-disaster-recovery/) 

### Part IV  - Distributed Systems Concepts

| # | Topic |
|---|-------|
| 18 | [Distributed Consensus](18-consensus/) 
| 19 | [Distributed Transactions](19-distributed-transactions/) 
| 20 | [Consistent Hashing](20-consistent-hashing/) 
| 21 | [Bloom Filters & Probabilistic Data Structures](21-bloom-filters/) 
| 22 | [Clocks & Ordering](22-clocks-ordering/) 

### Part V  - Architecture Patterns

| # | Topic |
|---|-------|
| 23 | [Monolith vs Microservices](23-microservices/) 
| 24 | [Event-Driven Architecture](24-event-driven/) 
| 25 | [Serverless Architecture](25-serverless/) 
| 26 | [Service Mesh & Sidecar Pattern](26-service-mesh/) 
| 27 | [Data Pipelines & ETL](27-data-pipelines/) 

### Part VI  - Security & Observability

| # | Topic |
|---|-------|
| 28 | [Authentication & Authorization](28-auth/) 
| 29 | [Encryption & Data Security](29-encryption/) 
| 30 | [Monitoring, Logging & Observability](30-observability/) 

### Part VII  - Real-World System Designs

| # | System |
|---|--------|
| 31 | [Design a URL Shortener](31-url-shortener/) 
| 32 | [Design a Rate Limiter](32-design-rate-limiter/) 
| 33 | [Design a Chat System](33-chat-system/) 
| 34 | [Design a News Feed](34-news-feed/) 
| 35 | [Design a Video Streaming Platform](35-video-streaming/) 
| 36 | [Design a Notification System](36-notification-system/) 
| 37 | [Design a Distributed Cache](37-distributed-cache/) 
| 38 | [Design a Search Autocomplete](38-autocomplete/) 
| 39 | [Design a File Storage System](39-file-storage/) 
| 40 | [Design a Ticket Booking System](40-ticket-booking/) 

## How to Use This Repo

```
1.  Follow the chapters in order  - each builds on the previous
2.  Read the concept guide (README.md) first
3.  Run the code lab to see concepts in action
4.  Read the linked Medium article for a condensed version
5.  Watch the linked YouTube video for a walkthrough
```

## Folder Structure

```
system-design-mastery/
│
├── README.md                  ← You are here
│
├── 01-scalability-basics/
│   ├── README.md              ← Concept guide with diagrams (includes links to Medium & YouTube)
│   └── code/
│       ├── README.md          ← Setup & run instructions
│       └── ...                ← Demo source code
│
├── 02-networking-essentials/
│   ├── ...
│
└── ... (40 chapters)
```

## Tech Stack Used in Code Labs

| Technology | Used For |
|------------|----------|
| Python | Algorithms, simulations, quick demos |
| Node.js | API servers, real-time systems |
| Docker | Containerized multi-service demos |
| Redis | Caching, rate limiting, pub/sub examples |
| PostgreSQL | SQL & replication demos |
| Kafka | Message queue & streaming examples |
| Nginx | Load balancing & proxy demos |

## Who Is This For

- Engineers preparing for **system design interviews**
- Developers moving from coding to **architecture** roles
- Anyone who wants to understand **how large-scale systems work**
- Content creators looking for **system design teaching material**

## Contributing

Contributions are welcome! If you find errors, want to add examples, or improve diagrams  - feel free to open an issue or submit a PR.

## License

This project is licensed under the [MIT License](LICENSE).

---

**Star this repo** if you find it useful  - it helps others discover it too.
