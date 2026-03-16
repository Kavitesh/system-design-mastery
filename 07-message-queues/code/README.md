# Chapter 07 - Code Lab: Message Queues & Event Streaming

Hands-on Python demos that build the core messaging patterns from scratch -
no Kafka or RabbitMQ installation required.

## Prerequisites

- Python 3.9+
- No external dependencies (all demos use the standard library)

## Lab Files

| File | What It Demonstrates |
|------|---------------------|
| `message_queue.py` | In-memory message queue with producer/consumer pattern and acknowledgments |
| `pub_sub.py` | Pub/sub system with topics, multiple subscribers, and fan-out delivery |
| `event_stream.py` | Kafka-like event log with partitions, consumer groups, and offset tracking |
| `dead_letter_queue.py` | Retry logic with dead letter queue for failed messages |

## Running the Labs

Each file is standalone. Run them directly:

```bash
python message_queue.py
python pub_sub.py
python event_stream.py
python dead_letter_queue.py
```

## Lab 1 - Message Queue (`message_queue.py`)

Builds a point-to-point message queue where multiple consumers compete for
messages. Messages require explicit acknowledgment - if a consumer crashes
before acking, the message goes back on the queue.

Key concepts:
- Producer/consumer decoupling
- Competing consumers (work distribution)
- Message acknowledgment and redelivery
- FIFO ordering within a single queue

## Lab 2 - Pub/Sub (`pub_sub.py`)

Implements a publish/subscribe broker with named topics. Producers publish to
topics, and every subscriber on that topic receives a copy. This is fan-out
delivery - one message in, N copies out.

Key concepts:
- Topic-based routing
- Fan-out to multiple subscribers
- Subscriber independence (each gets its own copy)
- Subscription management

## Lab 3 - Event Stream (`event_stream.py`)

Simulates Kafka's core architecture: topics split into partitions, messages
routed by partition key, consumer groups that coordinate partition assignment,
and offset-based position tracking with replay support.

Key concepts:
- Append-only partitioned log
- Key-based partition routing
- Consumer groups and partition assignment
- Offset tracking and commit
- Replay from arbitrary offset

## Lab 4 - Dead Letter Queue (`dead_letter_queue.py`)

Demonstrates what happens when messages can't be processed. Messages that fail
repeatedly get moved to a dead letter queue after exhausting retries, keeping
the main queue healthy while preserving the failed messages for investigation.

Key concepts:
- Retry with configurable max attempts
- Exponential backoff between retries
- Dead letter queue for poison messages
- DLQ inspection and replay
