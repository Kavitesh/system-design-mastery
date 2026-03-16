"""
Feed Ranking Algorithm
=========================

Chronological vs engagement-based feed ranking. Generates synthetic posts
with varying engagement signals and shows how ranking reorders the feed.
"""

import math
import time
import random

random.seed(42)

# ---------------------------------------------------------------------------
# Scoring parameters
# ---------------------------------------------------------------------------

RECENCY_LAMBDA = 0.1
WEIGHTS = {"engagement": 0.30, "affinity": 0.30, "recency": 0.30, "content_type": 0.10}


def recency_score(age_hours):
    return math.exp(-RECENCY_LAMBDA * age_hours)


def engagement_score(likes, comments, shares):
    return min((likes + comments * 2.0 + shares * 3.0) / 100.0, 1.0)


def content_bonus(has_media):
    return 1.0 if has_media else 0.5


def rank_score(post):
    e = engagement_score(post["likes"], post["comments"], post["shares"])
    a = post["affinity"]
    r = recency_score(post["age_h"])
    c = content_bonus(post["media"])
    total = WEIGHTS["engagement"]*e + WEIGHTS["affinity"]*a + WEIGHTS["recency"]*r + WEIGHTS["content_type"]*c
    return total, {"eng": e, "aff": a, "rec": r, "ct": c}

# ---------------------------------------------------------------------------
# Generate test posts
# ---------------------------------------------------------------------------

TOPICS = [
    "Just deployed v2 of the feed ranker",
    "Great coffee shop find downtown",
    "New transformer architecture paper",
    "Weekend hiking trip photos",
    "Hot take: microservices are overrated",
    "System design tip: start with requirements",
    "Debugging a race condition at 2am",
    "Book review: Designing Data-Intensive Apps",
    "Conference talk went well today",
    "Redis cluster migration - zero downtime",
    "Monoliths are underrated",
    "Hit 1M req/sec on the new cache layer",
    "Team lunch at the new ramen place",
    "Code review best practices thread",
    "Shipped dark mode - finally",
]

AUTHORS = ["alice", "bob", "carol", "dave", "eve"]


def generate_posts(n=15):
    posts = []
    for i in range(n):
        posts.append({
            "id": f"post_{i:03d}", "author": random.choice(AUTHORS),
            "content": TOPICS[i % len(TOPICS)],
            "age_h": random.uniform(0.5, 48),
            "likes": random.randint(0, 200),
            "comments": random.randint(0, 50),
            "shares": random.randint(0, 20),
            "media": random.random() > 0.6,
            "affinity": round(random.uniform(0.1, 1.0), 2),
        })
    return posts

# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def print_feed(title, posts, scored=False):
    print(f"\n{title}")
    print("-" * 72)
    hdr = f"{'#':<3} {'Author':<8} {'Age':>5} {'L':>4} {'C':>3} {'S':>3} {'M':>2}"
    if scored:
        hdr += f" {'Score':>6} {'Eng':>5} {'Aff':>5} {'Rec':>5}"
    hdr += f"  Content"
    print(hdr)
    print("-" * 72)

    for rank, p in enumerate(posts[:10], 1):
        line = f"{rank:<3} {p['author']:<8} {p['age_h']:>4.1f}h {p['likes']:>4} {p['comments']:>3} {p['shares']:>3} {'Y' if p['media'] else 'N':>2}"
        if scored:
            s, c = rank_score(p)
            line += f" {s:>6.3f} {c['eng']:>5.2f} {c['aff']:>5.2f} {c['rec']:>5.2f}"
        line += f"  {p['content'][:32]}"
        print(line)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Feed Ranking Algorithm Demo")
    print("=" * 72)
    print(f"Recency decay lambda: {RECENCY_LAMBDA} | Weights: {WEIGHTS}")

    posts = generate_posts(15)

    chrono = sorted(posts, key=lambda p: p["age_h"])
    print_feed("Chronological Feed (newest first)", chrono)

    ranked = sorted(posts, key=lambda p: rank_score(p)[0], reverse=True)
    print_feed("Ranked Feed (engagement + recency + affinity)", ranked, scored=True)

    print("\n" + "=" * 72)
    print("How Ranking Changes the Feed")
    print("=" * 72)

    chrono_ids = [p["id"] for p in chrono[:10]]
    ranked_ids = [p["id"] for p in ranked[:10]]
    overlap = len(set(chrono_ids) & set(ranked_ids))
    print(f"\n  Top-10 overlap: {overlap}/10 posts appear in both feeds")

    for i, p in enumerate(ranked[:3]):
        cpos = chrono_ids.index(p["id"]) + 1 if p["id"] in chrono_ids else ">10"
        s, _ = rank_score(p)
        print(f"\n  Ranked #{i+1}: \"{p['content'][:40]}\"")
        print(f"    Chrono position: #{cpos} | Score: {s:.3f} | Age: {p['age_h']:.1f}h | Likes: {p['likes']}")

    print(f"\n{'='*72}")
    print(f"Recency Decay Curve (lambda = {RECENCY_LAMBDA})")
    print(f"{'='*72}")
    print(f"  {'Hours':>6}  {'Score':>6}  Visualization")
    for h in [0, 1, 2, 4, 8, 12, 24, 36, 48]:
        s = recency_score(h)
        print(f"  {h:>5}h  {s:>6.3f}  {'#' * int(s * 40)}")

    print("\nKey insight: ranking surfaces high-engagement posts that")
    print("chronological sorting would bury under newer low-value content.")


if __name__ == "__main__":
    main()
