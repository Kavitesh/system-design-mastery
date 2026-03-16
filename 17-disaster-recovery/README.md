# Chapter 17 - Disaster Recovery & Backup

> Your database will fail. Your datacenter will go dark. The only question is whether you've practiced recovering from it or you're doing it for the first time during an actual outage.

📖 **Reading time:** 20 minutes
# **Code labs:** 4 Python scripts
🎬 **Video:** [Coming soon]()
# **Difficulty:** Intermediate

---

## Why Disaster Recovery Matters

Most teams think about disaster recovery the way most people think about fire extinguishers - they assume someone else handled it. Then something breaks at 3 AM and everyone discovers that the "backups" haven't actually worked in six months.

DR isn't about preventing disasters. Hardware fails. Regions go offline. Someone runs `DROP TABLE` in production. DR is about how fast you recover and how much data you lose when those things happen.

Two numbers define your entire DR strategy:

- **RPO (Recovery Point Objective):** How much data can you afford to lose? If your RPO is 1 hour, you need backups at least every hour.
- **RTO (Recovery Time Objective):** How long can you be down? If your RTO is 15 minutes, you need hot standby infrastructure ready to take over.

Everything else - backup strategies, failover mechanisms, replication topologies - exists to hit those two numbers.

---

## RPO and RTO - The Two Numbers That Drive Everything

### Understanding RPO

RPO answers: "When disaster strikes, how far back in time do we rewind?"

| RPO Target | What It Means | Typical Solution |
|---|---|---|
| 0 (zero data loss) | Every committed transaction survives | Synchronous replication |
| Seconds | Lose a few recent writes | Async replication with short lag |
| Minutes | Lose the last few minutes | Frequent log shipping |
| Hours | Lose up to a day's work | Periodic snapshots |
| Days | Acceptable for archival data | Daily/weekly backups |

Zero RPO sounds great until you realize it means synchronous replication, which means every write waits for confirmation from the replica. That adds latency to every single operation. Most systems don't actually need zero RPO - they just think they do.

### Understanding RTO

RTO answers: "How long are we down before we're back?"

| RTO Target | What It Means | Typical Solution |
|---|---|---|
| Near-zero | Users barely notice | Active-active multi-region |
| Minutes | Brief, noticeable outage | Hot standby with automated failover |
| 1-4 hours | Significant but manageable | Warm standby |
| 12-24 hours | Major disruption | Cold standby, restore from backup |
| Days | Business survival risk | Offsite tape backups |

### The RPO/RTO Matrix

Here's the part most tutorials skip: RPO and RTO aren't independent. They form a cost matrix.

| | RTO: Near-zero | RTO: Minutes | RTO: Hours | RTO: Days |
|---|---|---|---|---|
| **RPO: 0** | $$$$ Multi-site active-active with sync replication | $$$ Hot standby with sync replication | N/A (contradictory) | N/A |
| **RPO: Minutes** | $$$ Active-active with async replication | $$ Hot standby with async replication | $ Warm standby | $ Cold restore |
| **RPO: Hours** | $$ Active-active (overkill) | $ Warm standby with periodic snapshots | $ Cold standby | $ Tape/offsite |
| **RPO: Days** | Wasteful | Wasteful | $ Cold standby | $ Tape/offsite |

The bottom-left quadrant is wasteful - you're paying for fast recovery but accepting massive data loss. If you can lose days of data, you don't need active-active infrastructure.

The top-right is contradictory - you can't have zero data loss if you take hours to recover from a replication failure. During those hours, the primary is accumulating un-replicated writes.

**The sweet spot for most systems:** RPO of minutes, RTO of minutes. This is achievable with async replication and automated failover at reasonable cost.

---

## Backup Strategies

Backups are your last line of defense. Replication protects against hardware failure. Backups protect against everything else - including replication faithfully copying corrupted data to every replica.

### Full Backups

A full backup copies everything. Every file, every record, every byte.

- **Pros:** Simple to restore. Self-contained. No dependency chain.
- **Cons:** Slow to create. Uses the most storage. Can't run frequently on large datasets.
- **When to use:** Weekly for most systems. Daily if your dataset is small enough.

### Incremental Backups

An incremental backup copies only what changed since the *last backup of any type*.

- **Pros:** Fast to create. Minimal storage per backup.
- **Cons:** Restoration requires the full backup plus every incremental in sequence. If any link in the chain is corrupted, you lose everything after it.
- **When to use:** Between full backups when storage is constrained.

### Differential Backups

A differential backup copies everything that changed since the *last full backup*.

- **Pros:** Faster to restore than incrementals (need only the full + latest differential). Faster to create than full backups.
- **Cons:** Gets larger over time as more changes accumulate since the last full backup.
- **When to use:** The pragmatic middle ground. Full backup weekly, differential daily.

### Comparison

| Property | Full | Incremental | Differential |
|---|---|---|---|
| Backup speed | Slowest | Fastest | Middle |
| Storage used | Most | Least | Grows over time |
| Restore speed | Fastest | Slowest (chain) | Middle |
| Restore complexity | Simple | Complex (all links needed) | Moderate |
| Risk if one backup corrupts | Lose that backup only | Lose everything after corruption | Lose that differential only |

**My recommendation:** Full weekly + differential daily + transaction log backups every 15 minutes. This gives you RPO of 15 minutes with manageable storage costs and reasonable restore times.

---

## DR Strategies - From Cheap to Bulletproof

### Strategy 1: Backup and Restore (Cold DR)

The simplest strategy. Take backups, store them offsite, restore when disaster strikes.

- **RPO:** Hours to days (depends on backup frequency)
- **RTO:** Hours to days (depends on data size and restore speed)
- **Cost:** $ (just backup storage)

This is the bare minimum. If your business can tolerate being down for a day, this works. For a side project or internal tool, it's perfectly fine.

### Strategy 2: Pilot Light

Keep the minimal core infrastructure running in a DR region - database replicas and maybe a few critical services. Everything else is turned off. When disaster strikes, you spin up the remaining infrastructure around the "pilot light."

- **RPO:** Minutes (async replication to the replica)
- **RTO:** 30-60 minutes (time to spin up the remaining infra)
- **Cost:** $$ (running database replicas 24/7 + on-demand compute)

Think of it like a gas furnace pilot light - the flame is always burning, but the furnace isn't running until you need heat.

### Strategy 3: Warm Standby

A scaled-down but complete copy of your production environment runs in the DR region. It's handling no traffic, but it's running and ready.

- **RPO:** Minutes (async replication)
- **RTO:** 10-30 minutes (scale up the standby and redirect traffic)
- **Cost:** $$$ (running a full environment at reduced capacity)

### Strategy 4: Hot Standby (Active-Passive)

A full-scale copy of production runs in the DR region. It's ready to take 100% of traffic immediately. Only one region serves traffic at a time.

- **RPO:** Seconds to minutes (async replication with short lag)
- **RTO:** Minutes (DNS failover or load balancer switch)
- **Cost:** $$$$ (double the infrastructure, only half is serving traffic)

### Strategy 5: Multi-Site Active-Active

Multiple regions serve production traffic simultaneously. If one region fails, the others absorb its traffic. There's no "failover" - just capacity redistribution.

- **RPO:** Near-zero to zero (depends on replication mode)
- **RTO:** Near-zero (traffic automatically routes to healthy regions)
- **Cost:** $$$$$ (multiple full production environments, complex data consistency)

This is what Netflix, Google, and AWS's own services use. It's also dramatically more complex to build and operate than any other strategy. Don't do this unless your business truly requires near-zero downtime.

### Strategy Comparison

| Strategy | RPO | RTO | Cost | Complexity |
|---|---|---|---|---|
| Backup/Restore | Hours-Days | Hours-Days | $ | Low |
| Pilot Light | Minutes | 30-60 min | $$ | Medium |
| Warm Standby | Minutes | 10-30 min | $$$ | Medium-High |
| Hot Standby | Seconds-Min | Minutes | $$$$ | High |
| Active-Active | Near-zero | Near-zero | $$$$$ | Very High |

---

## Data Replication for DR

Replication is the mechanism that keeps your DR site in sync with production. The replication mode you choose directly determines your RPO.

### Synchronous Replication

Every write is confirmed by both the primary and the replica before the application gets an acknowledgment.

```
Client -> Primary -> Replica (write confirmed) -> Primary (ack) -> Client (success)
```

- **RPO:** Zero. If the primary dies, the replica has every committed transaction.
- **Tradeoff:** Every write pays the round-trip latency to the replica. Cross-region, that's 50-200ms per write.

Use this when data loss is truly unacceptable - financial transactions, medical records, legal documents.

### Asynchronous Replication

The primary confirms writes immediately, then replicates in the background.

```
Client -> Primary (ack) -> Client (success)
                 \-> Replica (eventually)
```

- **RPO:** Seconds to minutes, depending on replication lag.
- **Tradeoff:** The replica is always slightly behind. If the primary dies, you lose the un-replicated tail.

This is the right choice for 90% of systems. The write performance is better, and losing a few seconds of data during a regional failure is acceptable for most applications.

### Semi-Synchronous Replication

A compromise. Writes are confirmed when at least one replica acknowledges, but not all replicas.

- **RPO:** Near-zero (one replica is always up to date).
- **Tradeoff:** Better performance than full sync, but still adds some latency.

MySQL's semi-synchronous replication and PostgreSQL's synchronous_standby_names work this way.

---

## Geo-Redundancy

Geo-redundancy means your DR site is in a different geographic region - not just a different availability zone in the same data center campus.

### Why Geography Matters

Availability zones within a region protect against single-facility failures - power outages, cooling failures, network switch deaths. But they don't protect against regional disasters:

- Natural disasters (earthquakes, hurricanes, floods)
- Regional power grid failures
- Fiber cuts affecting an entire metro area
- Government-mandated shutdowns

For true DR, your backup site needs to be hundreds of miles away. AWS us-east-1 and us-west-2. Azure East US and West US. Different power grids, different network paths, different natural disaster risk profiles.

### The Latency Tax

Geographic distance means network latency. Light in fiber travels at roughly 200km/ms. Cross-country (US east to west coast) is about 60-80ms round trip. Cross-Atlantic is 80-120ms.

This latency affects:

- **Synchronous replication:** Every write gets 60-80ms slower. Often unacceptable.
- **Asynchronous replication:** Background process, so users don't notice. But you accumulate more replication lag, increasing RPO.
- **Application requests during failover:** Users connecting to the farther-away DR region will have higher latency.

The practical answer for most systems: use async replication for geo-redundant DR, accept an RPO of a few seconds, and use DNS-based routing to minimize user-facing latency after failover.

---

## Backup Verification and Testing

The most common DR failure mode isn't "we didn't have backups." It's "our backups didn't actually work."

### The Backup Verification Checklist

1. **Restore testing:** Actually restore from your backups regularly. Monthly at minimum, weekly if you can.
2. **Data integrity checks:** Verify checksums. Compare row counts. Run sanity queries on restored data.
3. **Timing:** Measure how long restores actually take. If your RTO is 1 hour and restores take 4 hours, you have a problem.
4. **End-to-end testing:** Don't just restore the database. Bring up the full application stack against the restored data and verify it works.
5. **Backup monitoring:** Alert when backups fail, when they take longer than expected, and when they're smaller than expected (a sudden drop in backup size often means data is missing).

### DR Drills

Netflix popularized this with Chaos Monkey, but you don't need to randomly kill production servers to test DR. What you need is scheduled, deliberate failover testing:

- **Tabletop exercises:** Walk through the DR runbook on paper. "If us-east-1 went down right now, what would we do?" You'll find gaps.
- **Planned failovers:** Actually fail over to the DR site during a maintenance window. Then fail back. Do this quarterly.
- **Partial failure testing:** Kill a single service's primary instance and verify the standby takes over correctly.
- **Backup restore drills:** Pick a random backup from the last month. Restore it. Verify the data.

**If you haven't tested your DR plan, you don't have a DR plan.** You have a DR wish.

---

## Runbook Automation

A runbook is a step-by-step procedure for handling incidents, including DR failovers. Manual runbooks are error-prone under stress. Automated runbooks are reliable.

### What to Automate

| Step | Manual Risk | Automation Approach |
|---|---|---|
| Detect failure | Slow, depends on someone noticing | Health checks with automated alerting |
| Decide to failover | Decision paralysis, committee meetings | Pre-defined thresholds, automated trigger |
| Execute failover | Typos, missed steps, wrong order | Scripted orchestration |
| Verify failover | Forgotten checks | Automated smoke tests |
| Notify stakeholders | Forgotten or delayed | Automated status page updates |
| Failback | Same risks as failover | Same automation, reverse direction |

### The Failover Decision Problem

Automated failover sounds great, but there's a critical edge case: split-brain. If the monitoring system can't reach the primary, is the primary down or is the network between the monitor and the primary broken?

If you automatically fail over on network partition, you now have two active primaries both accepting writes. Reconciling divergent writes after a split-brain is one of the hardest problems in distributed systems.

Solutions:

- **Quorum-based detection:** Use multiple monitors in different locations. Only fail over if a majority agree the primary is unreachable.
- **STONITH (Shoot The Other Node In The Head):** Before activating the standby, actively fence the primary - cut its network access, power it off, or revoke its ability to accept writes.
- **Manual approval gate:** Automate everything except the final "go" decision. A human reviews the evidence and clicks a button.

Most production systems use the third option. Automation handles detection, preparation, and execution - but a human makes the call.

---

## Real-World Examples

### Netflix - Multi-Region Active-Active

Netflix runs active-active across three AWS regions (us-east-1, us-west-2, eu-west-1). Key decisions:

- **Stateless services** are deployed identically in all three regions. Any region can handle any request.
- **Data is partitioned by user.** Each user's data lives primarily in one region, with async replication to the others.
- **Zuul (their API gateway)** routes users to the closest region. If a region fails, it reroutes to the next closest.
- **Chaos engineering** (Chaos Monkey, Chaos Kong) regularly simulates regional failures in production.

Netflix's approach works because streaming video is tolerant of eventual consistency. Your watchlist being 30 seconds behind isn't a disaster. If you're building a financial trading platform, this architecture doesn't directly apply.

### AWS Disaster Recovery Patterns

AWS publishes four DR patterns that map to the strategies we discussed:

1. **Backup and Restore** - S3 cross-region replication for backups, CloudFormation templates for rebuilding infrastructure
2. **Pilot Light** - RDS read replicas in DR region, AMIs ready to launch, Route 53 health checks
3. **Warm Standby** - Scaled-down Auto Scaling groups in DR region, database replication active
4. **Multi-Site Active-Active** - Full production in both regions, DynamoDB Global Tables or Aurora Global Database

The progression matches the RPO/RTO vs. cost tradeoff exactly. Most AWS customers are somewhere between Pilot Light and Warm Standby.

### GitHub - 2018 MySQL Incident

In October 2018, GitHub went down for 24 hours due to a 43-second network partition between their primary and secondary datacenters. The sequence:

1. A network maintenance event caused a brief partition.
2. The MySQL orchestrator promoted a secondary to primary in the other datacenter.
3. When the network healed, both datacenters had divergent writes.
4. Reconciling those writes took 24 hours of careful manual work.

The lesson: automated failover without proper split-brain prevention can make disasters worse, not better. GitHub later rebuilt their MySQL infrastructure with better fencing and more conservative failover thresholds.

---

## Common Pitfalls

### 1. Testing Backups but Never Restores

Creating a backup is half the job. If you've never restored from it, you don't know if it works. Every backup strategy needs a corresponding restore procedure that's been tested.

### 2. Ignoring Application State

Your DR plan covers the database. Great. But what about:

- File uploads stored on local disk?
- In-memory caches that need warming?
- Background job queues with pending work?
- Configuration that's managed outside your deployment pipeline?
- Third-party API keys and secrets?

DR means recovering the entire system, not just the database.

### 3. Forgetting About DNS TTL

You fail over to the DR site and update DNS to point to the new region. But your DNS records have a 1-hour TTL, so clients keep connecting to the dead primary for up to an hour.

Set low TTLs (60-300 seconds) on records involved in failover before you need them. Don't wait until the disaster to discover your TTL is too high.

### 4. No Failback Plan

Failing over is step one. Failing back to the original primary after it's repaired is step two - and it's often harder. You need to re-sync data that accumulated on the DR site back to the original primary, then switch traffic again without downtime.

### 5. RPO/RTO Mismatch with Business Requirements

Engineering sets RPO to 24 hours because it's cheap. The business assumes they'll lose zero data because "we have backups." These conversations need to happen before the disaster, not during.

### 6. Single-Region Backups

Storing backups in the same region as your primary defeats the purpose. If the region goes down, your backups go down with it. Always replicate backups to at least one other geographic region.

### 7. Underestimating Restore Time

"We have 5 TB of backups in S3." Great. How long does it take to download and restore 5 TB? At 1 Gbps, that's about 11 hours just for the transfer. Add database restore time on top. If your RTO is 2 hours, you have a math problem.

---

## Key Takeaways

1. **RPO and RTO drive everything.** Define them with your business stakeholders before choosing a DR strategy. Technical decisions without business context are guesses.

2. **Backups and replication serve different purposes.** Replication protects against hardware failure. Backups protect against data corruption, accidental deletion, and replication faithfully copying bad data everywhere.

3. **Match your DR strategy to your actual requirements.** Active-active multi-region is impressive engineering but costs 3-5x more than warm standby. Most systems don't need it.

4. **Test your DR plan regularly.** An untested DR plan is a DR theory. Schedule quarterly failover drills and monthly backup restore tests.

5. **Automate the runbook, gate the decision.** Automate failure detection, failover execution, and verification. But keep a human in the loop for the "should we actually fail over?" decision to prevent split-brain scenarios.

6. **Geography matters.** Same-region replicas don't protect against regional failures. Cross-region replication is the minimum for true DR.

---

## Code Labs

Explore the [code labs](./code/) for hands-on DR and backup simulations:

| Lab | File | What You'll Learn |
|---|---|---|
| Backup Strategies | `backup_strategies.py` | Full, incremental, and differential backup simulation with size/time comparisons |
| RPO/RTO Calculator | `rpo_rto_calculator.py` | Interactive calculator for RPO/RTO tradeoffs across DR strategies |
| DR Simulation | `dr_simulation.py` | Simulates disaster scenarios and recovery with different DR strategies |
| Failover Orchestrator | `failover_orchestrator.py` | Automated failover with health monitoring and region switching |

---

## What's Next?

- **Chapter 18:** [Distributed Consensus](../18-distributed-consensus/)
- **Chapter 19:** [API Gateway & BFF Patterns](../19-api-gateway-bff/)
