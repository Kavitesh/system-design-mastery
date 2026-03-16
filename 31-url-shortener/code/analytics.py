"""
URL Shortener Analytics
=======================
Simulates click traffic for shortened URLs and builds an analytics
dashboard showing clicks over time, top referrers, geographic
distribution, and device breakdown. Demonstrates the kind of data
a production URL shortener collects asynchronously via Kafka.

Run: python analytics.py
"""

import random
import sqlite3
from datetime import datetime, timedelta

DB_FILE = ":memory:"

REFERRERS = [
    "https://twitter.com", "https://facebook.com", "https://reddit.com",
    "https://linkedin.com", "https://news.ycombinator.com", "direct",
    "https://google.com", "https://t.co", "https://slack.com",
]
COUNTRIES = [("US", 40), ("GB", 12), ("DE", 8), ("IN", 10), ("BR", 7),
             ("CA", 6), ("FR", 5), ("JP", 4), ("AU", 4), ("Other", 4)]
DEVICES = [("Mobile/iOS", 35), ("Mobile/Android", 30), ("Desktop/Windows", 18),
           ("Desktop/Mac", 12), ("Tablet/iPad", 5)]
SHORT_URLS = [
    ("promo1", "https://store.example.com/summer-sale", 50),
    ("blog42", "https://blog.example.com/system-design-guide", 30),
    ("docs", "https://docs.example.com/api/v2/reference", 10),
    ("signup", "https://app.example.com/register?ref=email", 7),
    ("demo", "https://app.example.com/live-demo", 3),
]


# ---------------------------------------------------------------------------
# Database setup and click simulation
# ---------------------------------------------------------------------------

def init_db(conn: sqlite3.Connection):
    conn.execute("""CREATE TABLE clicks (
        id INTEGER PRIMARY KEY AUTOINCREMENT, short_code TEXT NOT NULL,
        clicked_at TEXT NOT NULL, referrer TEXT, country TEXT, device TEXT
    )""")


def weighted_choice(items_with_weights: list[tuple]) -> str:
    items, weights = zip(*items_with_weights)
    return random.choices(items, weights=weights, k=1)[0]


def simulate_clicks(conn: sqlite3.Connection, num_clicks: int = 5000) -> int:
    now = datetime.utcnow()
    start = now - timedelta(days=30)
    clicks = []
    for _ in range(num_clicks):
        code = random.choices([s[0] for s in SHORT_URLS], [s[2] for s in SHORT_URLS], k=1)[0]
        click_time = start + timedelta(seconds=random.randint(0, 30 * 86400))
        if 9 <= click_time.hour <= 17:
            if random.random() < 0.3: continue
        elif random.random() < 0.6:
            continue
        clicks.append((code, click_time.isoformat(), random.choice(REFERRERS),
                        weighted_choice(COUNTRIES), weighted_choice(DEVICES)))
    conn.executemany(
        "INSERT INTO clicks (short_code, clicked_at, referrer, country, device) VALUES (?,?,?,?,?)", clicks)
    conn.commit()
    return len(clicks)


# ---------------------------------------------------------------------------
# Analytics queries
# ---------------------------------------------------------------------------

def query(conn, sql, params=()):
    return [(r[0], r[1]) for r in conn.execute(sql, params).fetchall()]


def bar_chart(items: list[tuple], max_width: int = 40):
    if not items:
        return
    max_val = max(v for _, v in items)
    for label, val in items:
        bar = "#" * int(val / max_val * max_width)
        print(f"  {str(label):<22s} {bar} {val:,}")


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

def main():
    conn = sqlite3.connect(DB_FILE)
    init_db(conn)

    print("Simulating 30 days of click traffic...")
    total = simulate_clicks(conn, num_clicks=8000)
    print(f"Generated {total:,} click events\n")

    totals = query(conn, "SELECT short_code, COUNT(*) FROM clicks GROUP BY short_code ORDER BY 2 DESC")
    print(f"{'='*65}\nCLICKS PER SHORT URL\n{'='*65}")
    bar_chart(totals)

    top_code = totals[0][0]
    top_dest = {s[0]: s[1] for s in SHORT_URLS}.get(top_code, "unknown")

    print(f"\n{'='*65}")
    print(f"DETAILED ANALYTICS: /{top_code}")
    print(f"  Destination: {top_dest}")
    print(f"  Total clicks: {totals[0][1]:,}")
    print(f"{'='*65}")

    daily = query(conn, "SELECT DATE(clicked_at), COUNT(*) FROM clicks WHERE short_code=? GROUP BY 1 ORDER BY 1", (top_code,))
    if daily:
        vals = [v for _, v in daily]
        print(f"\n  Clicks by day - Min: {min(vals)}/day  Max: {max(vals)}/day  Avg: {sum(vals)//len(vals)}/day")

    print(f"\n  Peak Hours (UTC):")
    hours = query(conn, "SELECT CAST(strftime('%H',clicked_at) AS INT), COUNT(*) FROM clicks WHERE short_code=? GROUP BY 1 ORDER BY 1", (top_code,))
    bar_chart([(f"{h:02d}:00", c) for h, c in hours])

    print(f"\n  Top Referrers:")
    bar_chart(query(conn, "SELECT referrer, COUNT(*) FROM clicks WHERE short_code=? GROUP BY 1 ORDER BY 2 DESC LIMIT 8", (top_code,)))

    print(f"\n  Geographic Distribution:")
    bar_chart(query(conn, "SELECT country, COUNT(*) FROM clicks WHERE short_code=? GROUP BY 1 ORDER BY 2 DESC", (top_code,)))

    print(f"\n  Device Breakdown:")
    bar_chart(query(conn, "SELECT device, COUNT(*) FROM clicks WHERE short_code=? GROUP BY 1 ORDER BY 2 DESC", (top_code,)))

    grand_total = sum(t for _, t in totals)
    print(f"\n{'='*65}\nSUMMARY\n{'='*65}")
    print(f"  Total clicks (all URLs):  {grand_total:,}")
    print(f"  Most popular:             /{totals[0][0]} ({totals[0][1]:,} clicks)")
    print(f"  Least popular:            /{totals[-1][0]} ({totals[-1][1]:,} clicks)")

    top3 = query(conn, "SELECT referrer, COUNT(*) FROM clicks GROUP BY 1 ORDER BY 2 DESC LIMIT 3")
    print(f"  Top referrers overall:    {', '.join(r[0] for r in top3)}")
    conn.close()


if __name__ == "__main__":
    main()
