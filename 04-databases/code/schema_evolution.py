"""
Schema Evolution - SQL vs NoSQL
================================
Demonstrates how relational and document models handle schema
changes differently. SQL requires explicit ALTER TABLE migrations.
Document stores accept new shapes immediately but push the burden
to application code that reads old documents.

Run: python schema_evolution.py
"""

import sqlite3
import json
import os

SQL_DB = "schema_evo.db"


# ---------------------------------------------------------------------------
# SQL schema evolution (ALTER TABLE migrations)
# ---------------------------------------------------------------------------

def demo_sql_evolution():
    print("=" * 60)
    print("SQL SCHEMA EVOLUTION (migrations)")
    print("=" * 60)

    if os.path.exists(SQL_DB):
        os.remove(SQL_DB)
    conn = sqlite3.connect(SQL_DB)

    print("\nV1: Initial schema - users with name and email")
    conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)")
    conn.execute("INSERT INTO users VALUES (1, 'Alice', 'alice@dev.io')")
    conn.execute("INSERT INTO users VALUES (2, 'Bob', 'bob@dev.io')")
    conn.commit()

    for row in conn.execute("SELECT * FROM users"):
        print(f"  {row}")

    print("\nV2: Add phone column (ALTER TABLE - requires migration)")
    conn.execute("ALTER TABLE users ADD COLUMN phone TEXT DEFAULT 'unknown'")
    conn.execute("INSERT INTO users VALUES (3, 'Charlie', 'c@dev.io', '+1-555-0199')")
    conn.commit()

    print("  Existing rows get the default value:")
    for row in conn.execute("SELECT * FROM users"):
        print(f"  {row}")

    print("\nV3: Add created_at with a default timestamp")
    conn.execute("ALTER TABLE users ADD COLUMN created_at TEXT DEFAULT '2025-01-01'")
    conn.commit()

    print("  Every row now has 5 columns, even old ones:")
    for row in conn.execute("SELECT * FROM users"):
        print(f"  {row}")

    print("\n  SQL trade-off: schema changes are explicit and uniform.")
    print("  Every row conforms to the same shape. ALTER TABLE can lock")
    print("  large tables for seconds or minutes in production.")

    conn.close()
    os.remove(SQL_DB)


# ---------------------------------------------------------------------------
# Document store schema evolution (no migrations)
# ---------------------------------------------------------------------------

def demo_document_evolution():
    print("\n" + "=" * 60)
    print("DOCUMENT STORE SCHEMA EVOLUTION (no migrations)")
    print("=" * 60)

    collection = []

    print("\nV1: Insert users with name and email")
    collection.append({"_id": 1, "name": "Alice", "email": "alice@dev.io", "_version": 1})
    collection.append({"_id": 2, "name": "Bob", "email": "bob@dev.io", "_version": 1})
    for doc in collection:
        print(f"  {json.dumps(doc)}")

    print("\nV2: New users get a phone field - old ones don't")
    collection.append({
        "_id": 3, "name": "Charlie", "email": "c@dev.io",
        "phone": "+1-555-0199", "_version": 2,
    })

    print("  Now the collection has mixed shapes:")
    for doc in collection:
        has_phone = "phone" in doc
        print(f"  id={doc['_id']} v{doc['_version']} has_phone={has_phone}")

    print("\nV3: New users also get a preferences sub-document")
    collection.append({
        "_id": 4, "name": "Diana", "email": "d@dev.io",
        "phone": "+1-555-0200",
        "preferences": {"theme": "dark", "lang": "en"},
        "_version": 3,
    })

    print("  Three different document shapes coexist:")
    for doc in collection:
        print(f"  id={doc['_id']} v{doc['_version']} fields={list(doc.keys())}")

    print("\n  Reading old documents requires defensive code:")
    for doc in collection:
        phone = doc.get("phone", "N/A")
        theme = doc.get("preferences", {}).get("theme", "default")
        print(f"  {doc['name']}: phone={phone}, theme={theme}")

    print("\n  Document trade-off: zero-downtime schema changes, but your")
    print("  application must handle every version of the document shape.")
    print("  'Schemaless' really means 'schema-on-read.'")


# ---------------------------------------------------------------------------
# Side-by-side comparison
# ---------------------------------------------------------------------------

def comparison():
    print("\n" + "=" * 60)
    print("SIDE-BY-SIDE COMPARISON")
    print("=" * 60)

    print(f"\n  {'Aspect':<25} {'SQL (ALTER TABLE)':<25} {'Document (no migration)'}")
    print(f"  {'-'*25} {'-'*25} {'-'*25}")
    print(f"  {'Add a column/field':<25} {'ALTER TABLE + default':<25} {'Just insert new shape'}")
    print(f"  {'Rename a column':<25} {'Migration script':<25} {'Write both names in app'}")
    print(f"  {'Remove a column':<25} {'DROP COLUMN migration':<25} {'Stop writing it'}")
    print(f"  {'Downtime risk':<25} {'Possible on large tables':<25} {'None'}")
    print(f"  {'Data consistency':<25} {'Every row same shape':<25} {'Mixed shapes in storage'}")
    print(f"  {'Validation':<25} {'DB enforces constraints':<25} {'App must validate'}")
    print(f"  {'Debugging ease':<25} {'Schema is documentation':<25} {'Must inspect documents'}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    demo_sql_evolution()
    demo_document_evolution()
    comparison()


if __name__ == "__main__":
    main()
