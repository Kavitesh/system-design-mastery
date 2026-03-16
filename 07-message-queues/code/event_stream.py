"""
event_stream.py - Kafka-Like Event Stream
===========================================
Simulated append-only event log with partitions, key-based routing, consumer
groups, offset tracking, and replay. This mirrors Kafka's core architecture
without any external dependencies.

Run:
    python event_stream.py
"""

import hashlib
import threading
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
#   Record and Partition
# ---------------------------------------------------------------------------

@dataclass
class Record:
    key: str
    value: dict
    offset: int = -1
    partition: int = -1


class Partition:
    """Append-only ordered log of records. Each record gets a sequential
    offset starting from 0. Records are never deleted - they persist for
    the lifetime of the partition (in production Kafka, retention policies
    handle cleanup).
    """

    def __init__(self, partition_id: int):
        self.partition_id = partition_id
        self._log: list[Record] = []
        self._lock = threading.Lock()

    def append(self, key: str, value: dict) -> Record:
        with self._lock:
            offset = len(self._log)
            record = Record(key=key, value=value, offset=offset, partition=self.partition_id)
            self._log.append(record)
            return record

    def read(self, offset: int, max_records: int = 10) -> list[Record]:
        with self._lock:
            return self._log[offset:offset + max_records]

    @property
    def end_offset(self) -> int:
        with self._lock:
            return len(self._log)

# ---------------------------------------------------------------------------
#   Topic
# ---------------------------------------------------------------------------

class Topic:
    """A named feed of records split across N partitions. Records are routed
    to a partition by hashing the key, so all records with the same key land
    in the same partition and stay in order.
    """

    def __init__(self, name: str, num_partitions: int = 3):
        self.name = name
        self.partitions = [Partition(i) for i in range(num_partitions)]

    def produce(self, key: str, value: dict) -> Record:
        pid = int(hashlib.md5(key.encode()).hexdigest(), 16) % len(self.partitions)
        return self.partitions[pid].append(key, value)

# ---------------------------------------------------------------------------
#   Consumer Group
# ---------------------------------------------------------------------------

class ConsumerGroup:
    """A set of consumers that coordinate to read a topic. Each partition is
    assigned to exactly one consumer in the group. Consumers track their
    own offsets and commit them back to the group.
    """

    def __init__(self, group_id: str, topic: Topic):
        self.group_id = group_id
        self.topic = topic
        self._offsets: dict[int, int] = {p.partition_id: 0 for p in topic.partitions}
        self._assignments: dict[str, list[int]] = {}
        self._lock = threading.Lock()

    def assign(self, consumer_id: str, partition_ids: list[int]):
        with self._lock:
            self._assignments[consumer_id] = partition_ids
        parts = ", ".join(str(p) for p in partition_ids)
        print(f"  [group:{self.group_id}] assigned partitions [{parts}] to {consumer_id}")

    def poll(self, consumer_id: str, max_records: int = 5) -> list[Record]:
        with self._lock:
            pids = self._assignments.get(consumer_id, [])
            records = []
            for pid in pids:
                offset = self._offsets[pid]
                batch = self.topic.partitions[pid].read(offset, max_records)
                records.extend(batch)
            return records

    def commit(self, consumer_id: str, offsets: dict[int, int]):
        with self._lock:
            for pid, offset in offsets.items():
                self._offsets[pid] = offset

    def lag(self) -> dict[int, int]:
        with self._lock:
            return {
                pid: self.topic.partitions[pid].end_offset - self._offsets[pid]
                for pid in self._offsets
            }

# ---------------------------------------------------------------------------
#   Demo
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("DEMO 1: Producing records to a partitioned topic")
    print("=" * 60)
    print()

    topic = Topic("order-events", num_partitions=3)
    events = [
        ("user-42", {"action": "order_created", "item": "laptop"}),
        ("user-17", {"action": "order_created", "item": "mouse"}),
        ("user-42", {"action": "order_paid", "amount": 999}),
        ("user-99", {"action": "order_created", "item": "keyboard"}),
        ("user-17", {"action": "order_shipped", "tracking": "TRK-5"}),
        ("user-42", {"action": "order_shipped", "tracking": "TRK-8"}),
    ]

    for key, value in events:
        rec = topic.produce(key, value)
        print(f"  [producer] key={key}  partition={rec.partition}  offset={rec.offset}  value={value}")

    print()
    print("=" * 60)
    print("DEMO 2: Consumer group reading with offset tracking")
    print("=" * 60)
    print()

    group_a = ConsumerGroup("payment-service", topic)
    group_a.assign("consumer-1", [0, 1])
    group_a.assign("consumer-2", [2])
    print()

    for cid in ["consumer-1", "consumer-2"]:
        records = group_a.poll(cid)
        if records:
            print(f"  [{cid}] read {len(records)} records:")
            new_offsets = {}
            for r in records:
                print(f"    partition={r.partition}  offset={r.offset}  key={r.key}  value={r.value}")
                new_offsets[r.partition] = r.offset + 1
            group_a.commit(cid, new_offsets)
            print(f"  [{cid}] committed offsets: {new_offsets}")
        else:
            print(f"  [{cid}] no records available")
        print()

    print("=" * 60)
    print("DEMO 3: Consumer lag monitoring")
    print("=" * 60)
    print()

    topic.produce("user-42", {"action": "order_delivered"})
    topic.produce("user-17", {"action": "order_delivered"})

    lag = group_a.lag()
    total_lag = sum(lag.values())
    print(f"  [group:{group_a.group_id}] consumer lag by partition:")
    for pid, l in sorted(lag.items()):
        print(f"    partition {pid}: {l} records behind")
    print(f"  total lag: {total_lag} records")

    print()
    print("=" * 60)
    print("DEMO 4: Independent consumer group + replay")
    print("=" * 60)
    print()

    group_b = ConsumerGroup("analytics", topic)
    group_b.assign("analytics-1", [0, 1, 2])
    records = group_b.poll("analytics-1")
    print(f"  [analytics-1] read {len(records)} records (independent of payment-service)")

    group_b.commit("analytics-1", {0: 0, 1: 0, 2: 0})
    print("  [analytics-1] reset offsets to 0 for replay")
    records = group_b.poll("analytics-1")
    print(f"  [analytics-1] replayed {len(records)} records from beginning:")
    for r in records:
        print(f"    partition={r.partition}  offset={r.offset}  key={r.key}  value={r.value}")


if __name__ == "__main__":
    main()
