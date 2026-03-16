"""
News Feed - Flask Social Feed API
===================================

Hybrid fan-out social feed: push for normal users, pull for celebrities.
POST /post, POST /follow, POST /unfollow, GET /feed/<user>, GET /profile/<user>
"""

import time
import uuid
from collections import defaultdict
from flask import Flask, request, jsonify

app = Flask(__name__)

# ---------------------------------------------------------------------------
# In-memory storage (Redis + DB in production)
# ---------------------------------------------------------------------------

CELEBRITY_THRESHOLD = 5

posts_db = {}
user_posts = defaultdict(list)
followers = defaultdict(set)
following = defaultdict(set)
feed_cache = defaultdict(list)


def is_celebrity(uid):
    return len(followers[uid]) >= CELEBRITY_THRESHOLD


def make_post_id():
    return f"{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# Fan-out logic
# ---------------------------------------------------------------------------

def fan_out_on_write(post_id, author_id):
    """Push post into every follower's pre-computed feed."""
    count = 0
    for fid in followers[author_id]:
        feed_cache[fid].insert(0, post_id)
        feed_cache[fid] = feed_cache[fid][:200]
        count += 1
    return count


def fetch_celebrity_posts(user_id, limit=20):
    """Pull recent posts from celebrities this user follows."""
    results = []
    for followee in following[user_id]:
        if is_celebrity(followee):
            results.extend(user_posts[followee][-limit:])
    results.sort(key=lambda pid: posts_db[pid]["timestamp"], reverse=True)
    return results[:limit]


def assemble_feed(user_id, page_size=20):
    """Hybrid: merge pre-computed cache with pulled celebrity posts."""
    cached = feed_cache.get(user_id, [])[:page_size]
    celebrity = fetch_celebrity_posts(user_id, limit=page_size)
    merged = list(dict.fromkeys(cached + celebrity))
    merged.sort(key=lambda pid: posts_db[pid]["timestamp"], reverse=True)
    return [posts_db[pid] for pid in merged[:page_size]]


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------

@app.route("/post", methods=["POST"])
def create_post():
    data = request.json
    post_id = make_post_id()
    post = {
        "post_id": post_id, "author": data["user_id"],
        "content": data["content"], "timestamp": time.time(), "likes": 0,
    }
    posts_db[post_id] = post
    user_posts[data["user_id"]].append(post_id)

    if is_celebrity(data["user_id"]):
        strategy, fan_count = "fan-out-on-read (celebrity)", 0
    else:
        fan_count = fan_out_on_write(post_id, data["user_id"])
        strategy = "fan-out-on-write"

    return jsonify({"post": post, "strategy": strategy, "fan_out_count": fan_count}), 201


@app.route("/follow", methods=["POST"])
def follow_user():
    follower, followee = request.json["follower"], request.json["followee"]
    if follower == followee:
        return jsonify({"error": "can't follow yourself"}), 400
    followers[followee].add(follower)
    following[follower].add(followee)
    recent = user_posts[followee][-5:]
    for pid in recent:
        if pid not in feed_cache[follower]:
            feed_cache[follower].insert(0, pid)
    return jsonify({
        "follower": follower, "followee": followee,
        "is_celebrity": is_celebrity(followee), "backfilled": len(recent),
    })


@app.route("/unfollow", methods=["POST"])
def unfollow_user():
    followers[request.json["followee"]].discard(request.json["follower"])
    following[request.json["follower"]].discard(request.json["followee"])
    return jsonify({"unfollowed": request.json["followee"]})


@app.route("/feed/<user_id>")
def get_feed(user_id):
    feed = assemble_feed(user_id)
    return jsonify({"user": user_id, "feed": feed, "count": len(feed)})


@app.route("/profile/<user_id>")
def get_profile(user_id):
    pids = user_posts.get(user_id, [])
    return jsonify({
        "user": user_id,
        "posts": [posts_db[pid] for pid in reversed(pids)],
        "follower_count": len(followers[user_id]),
        "is_celebrity": is_celebrity(user_id),
    })


# ---------------------------------------------------------------------------
# Seed demo data
# ---------------------------------------------------------------------------

def seed():
    for u in ["bob", "carol", "dave", "eve", "frank", "grace"]:
        followers["alice"].add(u)
        following[u].add("alice")
    followers["bob"].add("carol")
    following["carol"].add("bob")
    for author, content in [("alice", "Shipped the new feed algorithm!"),
                            ("alice", "Scaling Redis to 500M sorted sets"),
                            ("bob", "Coffee and code this morning"),
                            ("carol", "Design review went well today")]:
        pid = make_post_id()
        posts_db[pid] = {"post_id": pid, "author": author,
                         "content": content, "timestamp": time.time(), "likes": 0}
        user_posts[author].append(pid)
        if not is_celebrity(author):
            fan_out_on_write(pid, author)
        time.sleep(0.01)
    print(f"  Seeded 4 posts | Alice: {len(followers['alice'])} followers (celebrity={is_celebrity('alice')})")


if __name__ == "__main__":
    print("News Feed API - seeding demo data...")
    seed()
    print("Starting server on http://localhost:5000")
    app.run(debug=True, port=5000)
