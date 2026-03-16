"""
URL Shortener Service
=====================
A complete Flask-based URL shortener using base62 encoding and SQLite.
Supports creating short URLs, redirecting, custom aliases, expiration,
and per-link click stats. This is the core service from Chapter 31.

Run: python url_shortener.py
"""

import sqlite3
import string
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, redirect, g

app = Flask(__name__)
DATABASE = "urls.db"
BASE_URL = "http://localhost:5000"

ALPHABET = string.digits + string.ascii_letters  # 0-9, a-z, A-Z = 62 chars


# ---------------------------------------------------------------------------
# Base62 encoding - converts an integer counter to a short alphanumeric code
# ---------------------------------------------------------------------------

def base62_encode(num: int) -> str:
    if num == 0:
        return ALPHABET[0]
    chars = []
    while num > 0:
        chars.append(ALPHABET[num % 62])
        num //= 62
    return "".join(reversed(chars))


def base62_decode(code: str) -> int:
    num = 0
    for char in code:
        num = num * 62 + ALPHABET.index(char)
    return num


# ---------------------------------------------------------------------------
# Database setup and helpers
# ---------------------------------------------------------------------------

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db:
        db.close()


def init_db():
    conn = sqlite3.connect(DATABASE)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            short_code TEXT UNIQUE NOT NULL,
            long_url TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT,
            click_count INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS clicks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            short_code TEXT NOT NULL,
            clicked_at TEXT NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            referrer TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_short_code ON urls(short_code);
        CREATE INDEX IF NOT EXISTS idx_clicks_code ON clicks(short_code);
    """)
    conn.close()


# ---------------------------------------------------------------------------
# Counter-based ID generation with base62 encoding
# ---------------------------------------------------------------------------

COUNTER_OFFSET = 100000  # start codes at 6 digits for aesthetics


def generate_short_code(db) -> str:
    cursor = db.execute("SELECT MAX(id) FROM urls")
    max_id = cursor.fetchone()[0] or 0
    return base62_encode(max_id + 1 + COUNTER_OFFSET)


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

@app.route("/api/v1/urls", methods=["POST"])
def create_short_url():
    data = request.get_json()
    if not data or not data.get("long_url"):
        return jsonify({"error": "long_url is required"}), 400

    long_url = data["long_url"]
    custom_alias = data.get("custom_alias")
    ttl_days = data.get("ttl_days", 365 * 5)

    db = get_db()
    now = datetime.utcnow()
    expires_at = now + timedelta(days=ttl_days)

    if custom_alias:
        existing = db.execute(
            "SELECT short_code FROM urls WHERE short_code = ?", (custom_alias,)
        ).fetchone()
        if existing:
            return jsonify({"error": f"Alias '{custom_alias}' is already taken"}), 409
        short_code = custom_alias
    else:
        short_code = generate_short_code(db)

    db.execute(
        "INSERT INTO urls (short_code, long_url, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (short_code, long_url, now.isoformat(), expires_at.isoformat()),
    )
    db.commit()

    return jsonify({
        "short_url": f"{BASE_URL}/{short_code}",
        "short_code": short_code,
        "long_url": long_url,
        "expires_at": expires_at.isoformat(),
    }), 201


@app.route("/<short_code>")
def redirect_url(short_code):
    db = get_db()
    row = db.execute(
        "SELECT long_url, expires_at FROM urls WHERE short_code = ?", (short_code,)
    ).fetchone()

    if not row:
        return jsonify({"error": "Short URL not found"}), 404

    if row["expires_at"]:
        expires = datetime.fromisoformat(row["expires_at"])
        if datetime.utcnow() > expires:
            return jsonify({"error": "This short URL has expired"}), 410

    db.execute(
        "UPDATE urls SET click_count = click_count + 1 WHERE short_code = ?",
        (short_code,),
    )
    db.execute(
        "INSERT INTO clicks (short_code, clicked_at, ip_address, user_agent, referrer) VALUES (?, ?, ?, ?, ?)",
        (
            short_code,
            datetime.utcnow().isoformat(),
            request.remote_addr,
            request.headers.get("User-Agent", ""),
            request.headers.get("Referer", ""),
        ),
    )
    db.commit()

    return redirect(row["long_url"], code=302)


@app.route("/api/v1/urls/<short_code>/stats")
def get_stats(short_code):
    db = get_db()
    row = db.execute(
        "SELECT short_code, long_url, created_at, expires_at, click_count FROM urls WHERE short_code = ?",
        (short_code,),
    ).fetchone()

    if not row:
        return jsonify({"error": "Short URL not found"}), 404

    recent_clicks = db.execute(
        "SELECT clicked_at, ip_address, referrer FROM clicks WHERE short_code = ? ORDER BY clicked_at DESC LIMIT 10",
        (short_code,),
    ).fetchall()

    return jsonify({
        "short_code": row["short_code"],
        "long_url": row["long_url"],
        "created_at": row["created_at"],
        "expires_at": row["expires_at"],
        "click_count": row["click_count"],
        "recent_clicks": [
            {"clicked_at": c["clicked_at"], "ip": c["ip_address"], "referrer": c["referrer"]}
            for c in recent_clicks
        ],
    })


@app.route("/api/v1/urls/<short_code>", methods=["DELETE"])
def delete_url(short_code):
    db = get_db()
    result = db.execute("DELETE FROM urls WHERE short_code = ?", (short_code,))
    db.execute("DELETE FROM clicks WHERE short_code = ?", (short_code,))
    db.commit()

    if result.rowcount == 0:
        return jsonify({"error": "Short URL not found"}), 404
    return "", 204


# ---------------------------------------------------------------------------
# Demo: create some sample URLs on startup
# ---------------------------------------------------------------------------

def seed_demo_data():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.execute("SELECT COUNT(*) FROM urls")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

    now = datetime.utcnow()
    expires = (now + timedelta(days=365)).isoformat()
    samples = [
        ("github", "https://github.com/trending", now.isoformat(), expires),
        ("python", "https://docs.python.org/3/tutorial/index.html", now.isoformat(), expires),
        ("flask", "https://flask.palletsprojects.com/en/stable/", now.isoformat(), expires),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO urls (short_code, long_url, created_at, expires_at) VALUES (?, ?, ?, ?)",
        samples,
    )
    conn.commit()
    conn.close()
    print(f"  Seeded {len(samples)} demo URLs: /github, /python, /flask")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    init_db()
    seed_demo_data()
    print(f"URL Shortener running at {BASE_URL}")
    app.run(debug=True, port=5000)
