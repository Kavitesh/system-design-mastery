"""
Video Streaming Platform - Metadata API
========================================
Flask API for video metadata: upload, list, search, view counting.

Run:  python video_platform.py
Then: curl http://localhost:5000/api/videos
      curl http://localhost:5000/api/videos/search?q=python
"""

import sqlite3, uuid, time
from flask import Flask, request, jsonify, g

app = Flask(__name__)
DB = ":memory:"

SEED = [
    ("Python Flask Tutorial", "Build REST APIs with Flask", "python,flask,api", 1847, "CodeSam"),
    ("System Design: Distributed Caching", "Redis and Memcached strategies", "caching,redis,system-design", 2415, "DesignGuru"),
    ("Kubernetes Full Course", "Container orchestration from scratch", "kubernetes,docker,devops", 7200, "CloudNinja"),
    ("How Video Streaming Works", "HLS, DASH, and adaptive bitrate", "streaming,hls,dash,cdn", 1560, "TechDeep"),
    ("PostgreSQL Performance Tuning", "Indexes, query plans, pooling", "postgresql,database,sql", 2100, "DBMaster"),
    ("Building a CDN from Scratch", "Edge caching and content delivery", "cdn,networking,caching", 1980, "TechDeep"),
    ("Machine Learning with Python", "Regression, classification, clustering", "python,ml,data-science", 3600, "DataDriven"),
    ("Docker Networking Deep Dive", "Bridge, host, and overlay networks", "docker,networking,devops", 1320, "CloudNinja"),
]

# ---------------------------------------------------------------------------

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db: db.close()

def init_db():
    db = get_db()
    db.execute("""CREATE TABLE IF NOT EXISTS videos (
        video_id TEXT PRIMARY KEY, title TEXT, description TEXT, tags TEXT,
        duration_sec INT, creator TEXT, status TEXT DEFAULT 'ready',
        view_count INT DEFAULT 0, created_at REAL)""")
    for title, desc, tags, dur, creator in SEED:
        db.execute("INSERT INTO videos VALUES (?,?,?,?,?,?,?,?,?)",
                   (uuid.uuid4().hex[:10], title, desc, tags, dur, creator,
                    "ready", int(time.time() % 9000) * 3, time.time()))
    db.commit()

def fmt(sec):
    h, r = divmod(sec, 3600); m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

def to_dict(row):
    d = dict(row); d["duration_fmt"] = fmt(d["duration_sec"])
    d["tags"] = d["tags"].split(",") if d["tags"] else []; return d

# ---------------------------------------------------------------------------

@app.before_request
def ensure_db():
    if not hasattr(app, "_init"):
        init_db(); app._init = True

@app.route("/api/videos/upload", methods=["POST"])
def upload():
    data = request.get_json() or {}
    if not data.get("title") or not data.get("creator"):
        return jsonify(error="title and creator required"), 400
    vid = uuid.uuid4().hex[:10]
    db = get_db()
    db.execute("INSERT INTO videos VALUES (?,?,?,?,?,?,'pending',0,?)",
               (vid, data["title"], data.get("description",""),
                ",".join(data.get("tags",[])), data.get("duration_sec",0),
                data["creator"], time.time()))
    db.commit()
    return jsonify(video_id=vid, status="pending",
                   message="Upload registered. Transcoding would start here."), 201

@app.route("/api/videos")
def list_videos():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    db = get_db()
    rows = db.execute("SELECT * FROM videos WHERE status='ready' ORDER BY created_at DESC LIMIT ? OFFSET ?",
                      (per_page, (page-1)*per_page)).fetchall()
    total = db.execute("SELECT COUNT(*) c FROM videos WHERE status='ready'").fetchone()["c"]
    return jsonify(videos=[to_dict(r) for r in rows], page=page, total=total)

@app.route("/api/videos/<vid>")
def get_video(vid):
    db = get_db()
    db.execute("UPDATE videos SET view_count=view_count+1 WHERE video_id=?", (vid,))
    db.commit()
    row = db.execute("SELECT * FROM videos WHERE video_id=?", (vid,)).fetchone()
    return jsonify(to_dict(row)) if row else (jsonify(error="Not found"), 404)

@app.route("/api/videos/search")
def search():
    q = request.args.get("q", "").lower()
    if not q: return jsonify(error="q param required"), 400
    db = get_db()
    rows = db.execute(
        "SELECT * FROM videos WHERE status='ready' AND "
        "(LOWER(title) LIKE ? OR LOWER(description) LIKE ? OR LOWER(tags) LIKE ?) "
        "ORDER BY view_count DESC", (f"%{q}%",)*3).fetchall()
    return jsonify(query=q, count=len(rows), results=[to_dict(r) for r in rows])

@app.route("/api/videos/<vid>", methods=["DELETE"])
def delete(vid):
    db = get_db()
    if not db.execute("SELECT 1 FROM videos WHERE video_id=?", (vid,)).fetchone():
        return jsonify(error="Not found"), 404
    db.execute("DELETE FROM videos WHERE video_id=?", (vid,)); db.commit()
    return jsonify(deleted=vid)

# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Video Platform API running on http://localhost:5000")
    app.run(debug=True, port=5000)
