"""
Content-Based Video Recommendation Engine
==========================================
TF-IDF similarity over video metadata. Demonstrates content-based
filtering, user profile construction, and ranked suggestions.

Run:  python recommendation.py
"""

import math, re
from collections import Counter, defaultdict

# ---------------------------------------------------------------------------

CATALOG = [
    {"id": "v01", "title": "Python Flask Tutorial - REST APIs",
     "tags": ["python","flask","rest","api","web"], "cat": "programming", "views": 245000},
    {"id": "v02", "title": "System Design: Distributed Caching",
     "tags": ["system-design","caching","redis","architecture"], "cat": "system-design", "views": 189000},
    {"id": "v03", "title": "Kubernetes - Container Orchestration",
     "tags": ["kubernetes","docker","containers","devops"], "cat": "devops", "views": 520000},
    {"id": "v04", "title": "Video Streaming - HLS and DASH",
     "tags": ["streaming","hls","dash","video","cdn"], "cat": "networking", "views": 97000},
    {"id": "v05", "title": "PostgreSQL Performance Tuning",
     "tags": ["postgresql","database","performance","sql"], "cat": "databases", "views": 134000},
    {"id": "v06", "title": "Building a CDN with Python",
     "tags": ["cdn","python","networking","caching"], "cat": "networking", "views": 78000},
    {"id": "v07", "title": "Machine Learning with Python",
     "tags": ["python","ml","scikit-learn","data-science"], "cat": "data-science", "views": 890000},
    {"id": "v08", "title": "Docker Networking Deep Dive",
     "tags": ["docker","networking","containers","devops"], "cat": "devops", "views": 156000},
    {"id": "v09", "title": "Redis Crash Course - Caching",
     "tags": ["redis","caching","pub-sub","database"], "cat": "databases", "views": 203000},
    {"id": "v10", "title": "System Design: URL Shortener",
     "tags": ["system-design","architecture","database","hashing"], "cat": "system-design", "views": 312000},
    {"id": "v11", "title": "Flask and SQLAlchemy Integration",
     "tags": ["python","flask","sqlalchemy","database"], "cat": "programming", "views": 167000},
    {"id": "v12", "title": "Kafka - Distributed Message Queues",
     "tags": ["kafka","distributed","messaging","streaming"], "cat": "system-design", "views": 145000},
]

# ---------------------------------------------------------------------------

class TFIDFEngine:
    def __init__(self, videos):
        self.videos = {v["id"]: v for v in videos}
        self.vecs = {}
        self._build(videos)

    def _tokenize(self, v):
        words = re.findall(r'[a-z0-9]+', v["title"].lower())
        tags = [w for t in v["tags"] for w in t.replace("-"," ").split()]
        return words * 2 + tags * 3 + v["cat"].split("-")

    def _build(self, videos):
        docs = {v["id"]: self._tokenize(v) for v in videos}
        n = len(videos)
        df = Counter()
        for toks in docs.values():
            for t in set(toks): df[t] += 1
        idf = {t: math.log(n / c) for t, c in df.items()}
        for vid, toks in docs.items():
            tf = Counter(toks); total = len(toks)
            self.vecs[vid] = {t: (c/total)*idf.get(t,0) for t, c in tf.items()}

    def _cosine(self, a, b):
        common = set(a) & set(b)
        if not common: return 0.0
        dot = sum(a[k]*b[k] for k in common)
        ma = math.sqrt(sum(v**2 for v in a.values()))
        mb = math.sqrt(sum(v**2 for v in b.values()))
        return dot/(ma*mb) if ma and mb else 0.0

    def similar(self, vid, n=4):
        src = self.vecs[vid]
        scores = [(v, self._cosine(src, vec)) for v, vec in self.vecs.items() if v != vid]
        return sorted(scores, key=lambda x: -x[1])[:n]

    def recommend(self, watched, n=4):
        profile = defaultdict(float)
        for vid in watched:
            for t, w in self.vecs.get(vid, {}).items(): profile[t] += w / len(watched)
        scores = [(v, self._cosine(dict(profile), vec))
                  for v, vec in self.vecs.items() if v not in watched]
        return sorted(scores, key=lambda x: -x[1])[:n]

# ---------------------------------------------------------------------------

def show(engine, title, recs):
    print(f"\n  {title}")
    print(f"  {'-'*55}")
    for i, (vid, sc) in enumerate(recs, 1):
        v = engine.videos[vid]
        print(f"  {i}. [{sc:.3f}] {v['title']}")
        print(f"     {', '.join(v['tags'])}  |  {v['views']:,} views")

def main():
    print("=" * 65)
    print("CONTENT-BASED VIDEO RECOMMENDATION ENGINE")
    print("=" * 65)
    engine = TFIDFEngine(CATALOG)
    print(f"Catalog: {len(CATALOG)} videos  |  Vocab: {len(set().union(*engine.vecs.values()))} terms")

    print("\n" + "=" * 65)
    print("SIMILAR VIDEOS")
    for vid in ["v01", "v02", "v04"]:
        show(engine, f'Because you watched: "{engine.videos[vid]["title"]}"',
             engine.similar(vid))

    print("\n" + "=" * 65)
    print("USER RECOMMENDATIONS")
    users = {
        "Alice (system design)": ["v02", "v10", "v12"],
        "Bob (Python dev)":      ["v01", "v07", "v11"],
        "Carol (DevOps)":        ["v03", "v08", "v04"],
    }
    for name, history in users.items():
        print(f"\n  {name}")
        print(f"  Watched: {', '.join(engine.videos[v]['title'] for v in history)}")
        show(engine, "Recommended:", engine.recommend(history))

    print("\n" + "=" * 65)
    print("SIMILARITY MATRIX")
    sub = ["v01","v02","v04","v06","v09","v12"]
    print(f"  {'':>28s}" + "".join(f" {v:>5s}" for v in sub))
    for a in sub:
        label = engine.videos[a]["title"][:27]
        row = "".join(f" {'1.00' if a==b else f'{engine._cosine(engine.vecs[a], engine.vecs[b]):.2f}':>5s}" for b in sub)
        print(f"  {label:>28s}{row}")

# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Recommendation engine starting")
    main()
