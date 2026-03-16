"""
Message Store - SQLite-Based Chat Message Persistence
======================================================
Conversation-partitioned message storage with monotonic sequence numbers
and cursor-based pagination. Models the same access patterns as Cassandra
in production: write messages, read by conversation in reverse order.
"""

import sqlite3
import uuid
import time
from datetime import datetime

# ---------------------------------------------------------------------------
#  Database setup
# ---------------------------------------------------------------------------

def create_connection(db_path=":memory:"):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            conversation_id TEXT NOT NULL,
            sequence_num    INTEGER NOT NULL,
            message_id      TEXT NOT NULL,
            sender_id       TEXT NOT NULL,
            content         TEXT NOT NULL,
            content_type    INTEGER DEFAULT 0,
            created_at      REAL NOT NULL,
            status          INTEGER DEFAULT 0,
            PRIMARY KEY (conversation_id, sequence_num)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            conversation_id TEXT PRIMARY KEY,
            conv_type       TEXT NOT NULL,
            next_seq        INTEGER DEFAULT 1,
            created_at      REAL NOT NULL
        )
    """)
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
#  Conversation helpers
# ---------------------------------------------------------------------------

def get_dm_conversation_id(user_a, user_b):
    """Deterministic conversation ID for 1-on-1 chats."""
    pair = sorted([user_a, user_b])
    raw = f"{pair[0]}:{pair[1]}"
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, raw))


def ensure_conversation(conn, conversation_id, conv_type="dm"):
    row = conn.execute(
        "SELECT conversation_id FROM conversations WHERE conversation_id = ?",
        (conversation_id,)
    ).fetchone()
    if not row:
        conn.execute(
            "INSERT INTO conversations (conversation_id, conv_type, next_seq, created_at) VALUES (?, ?, 1, ?)",
            (conversation_id, conv_type, time.time())
        )
        conn.commit()


# ---------------------------------------------------------------------------
#  Write path
# ---------------------------------------------------------------------------

def send_message(conn, conversation_id, sender_id, content, content_type=0):
    """Insert a message and return its assigned sequence number."""
    row = conn.execute(
        "SELECT next_seq FROM conversations WHERE conversation_id = ?",
        (conversation_id,)
    ).fetchone()
    if not row:
        raise ValueError(f"Conversation {conversation_id} not found")

    seq = row["next_seq"]
    message_id = str(uuid.uuid4())
    now = time.time()

    conn.execute(
        """INSERT INTO messages
           (conversation_id, sequence_num, message_id, sender_id, content, content_type, created_at, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, 0)""",
        (conversation_id, seq, message_id, sender_id, content, content_type, now)
    )
    conn.execute(
        "UPDATE conversations SET next_seq = ? WHERE conversation_id = ?",
        (seq + 1, conversation_id)
    )
    conn.commit()
    return seq, message_id


# ---------------------------------------------------------------------------
#  Read path - paginated
# ---------------------------------------------------------------------------

def get_messages(conn, conversation_id, before_seq=None, limit=20):
    """Fetch messages in reverse chronological order with cursor pagination."""
    if before_seq is None:
        row = conn.execute(
            "SELECT next_seq FROM conversations WHERE conversation_id = ?",
            (conversation_id,)
        ).fetchone()
        before_seq = row["next_seq"] if row else 1

    rows = conn.execute(
        """SELECT * FROM messages
           WHERE conversation_id = ? AND sequence_num < ?
           ORDER BY sequence_num DESC
           LIMIT ?""",
        (conversation_id, before_seq, limit)
    ).fetchall()
    return list(reversed(rows))


def get_messages_after(conn, conversation_id, after_seq, limit=100):
    """Fetch messages after a sequence number - used for offline sync."""
    rows = conn.execute(
        """SELECT * FROM messages
           WHERE conversation_id = ? AND sequence_num > ?
           ORDER BY sequence_num ASC
           LIMIT ?""",
        (conversation_id, after_seq, limit)
    ).fetchall()
    return rows


# ---------------------------------------------------------------------------
#  Status updates
# ---------------------------------------------------------------------------

def mark_delivered(conn, conversation_id, sequence_num):
    conn.execute(
        "UPDATE messages SET status = 1 WHERE conversation_id = ? AND sequence_num = ?",
        (conversation_id, sequence_num)
    )
    conn.commit()


def mark_read(conn, conversation_id, up_to_seq):
    """Mark all messages up to a sequence number as read."""
    conn.execute(
        "UPDATE messages SET status = 2 WHERE conversation_id = ? AND sequence_num <= ? AND status < 2",
        (conversation_id, up_to_seq)
    )
    conn.commit()


# ---------------------------------------------------------------------------
#  Demo
# ---------------------------------------------------------------------------

STATUS_LABELS = {0: "sent", 1: "delivered", 2: "read"}

def format_msg(row):
    ts = datetime.fromtimestamp(row["created_at"]).strftime("%H:%M:%S")
    status = STATUS_LABELS.get(row["status"], "unknown")
    return f"  [seq={row['sequence_num']}] {ts} {row['sender_id']}: {row['content']} ({status})"


if __name__ == "__main__":
    print("message_store: chat persistence demo")

    conn = create_connection()

    alice, bob, carol = "alice", "bob", "carol"
    dm_id = get_dm_conversation_id(alice, bob)
    group_id = str(uuid.uuid4())

    ensure_conversation(conn, dm_id, "dm")
    ensure_conversation(conn, group_id, "group")

    print(f"\n--- 1-on-1 conversation (alice <-> bob) ---")
    print(f"conversation_id: {dm_id[:12]}...")

    send_message(conn, dm_id, alice, "Hey Bob, are you free for lunch?")
    send_message(conn, dm_id, bob, "Sure! Where are you thinking?")
    send_message(conn, dm_id, alice, "That new ramen place on 5th")
    send_message(conn, dm_id, bob, "Perfect, see you at noon")
    seq5, _ = send_message(conn, dm_id, alice, "Sounds good!")

    mark_delivered(conn, dm_id, seq5)
    mark_read(conn, dm_id, 3)

    messages = get_messages(conn, dm_id)
    for msg in messages:
        print(format_msg(msg))

    print(f"\n--- Group conversation ---")
    print(f"conversation_id: {group_id[:12]}...")

    for i in range(1, 16):
        sender = [alice, bob, carol][i % 3]
        send_message(conn, group_id, sender, f"Group message #{i}")

    print("\nPage 1 (most recent 5):")
    page1 = get_messages(conn, group_id, limit=5)
    for msg in page1:
        print(format_msg(msg))

    cursor = page1[0]["sequence_num"]
    print(f"\nPage 2 (before seq={cursor}, next 5):")
    page2 = get_messages(conn, group_id, before_seq=cursor, limit=5)
    for msg in page2:
        print(format_msg(msg))

    print(f"\n--- Offline sync demo ---")
    print("Client was offline after seq=2, fetching missed messages:")
    missed = get_messages_after(conn, dm_id, after_seq=2)
    for msg in missed:
        print(format_msg(msg))

    print(f"\n--- Stats ---")
    total = conn.execute("SELECT COUNT(*) as cnt FROM messages").fetchone()["cnt"]
    convs = conn.execute("SELECT COUNT(*) as cnt FROM conversations").fetchone()["cnt"]
    print(f"  Total messages: {total}")
    print(f"  Conversations:  {convs}")

    conn.close()
