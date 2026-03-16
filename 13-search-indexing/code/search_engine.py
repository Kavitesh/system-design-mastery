"""
search_engine.py
================
A Flask REST API that wraps an inverted index with TF-IDF scoring. Exposes
endpoints to index documents, run ranked searches, and inspect index
statistics. This is the same index from inverted_index.py exposed over HTTP.

Run:
    python search_engine.py

Endpoints:
    POST /index   - add a document  {"id": "...", "text": "..."}
    GET  /search  - search          ?q=query+terms&top_k=5
    GET  /stats   - index stats
"""

import math
import re
from collections import defaultdict
from flask import Flask, request, jsonify

# ---------------------------------------------------------------------------
# Text analysis (same pipeline as inverted_index.py)
# ---------------------------------------------------------------------------

STOP_WORDS = frozenset([
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
    "into", "through", "during", "before", "after", "and", "but", "or",
    "not", "no", "nor", "so", "yet", "both", "either", "neither", "each",
    "this", "that", "these", "those", "it", "its", "i", "me", "my", "we",
])

SUFFIX_RULES = [
    ("ies", "y"), ("ves", "f"), ("ing", ""), ("tion", "t"),
    ("sses", "ss"), ("ness", ""), ("ment", ""), ("able", ""),
    ("ly", ""), ("ed", ""), ("er", ""), ("es", ""), ("s", ""),
]


def tokenize(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def stem(word):
    if len(word) <= 3:
        return word
    for suffix, replacement in SUFFIX_RULES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 2:
            return word[: -len(suffix)] + replacement
    return word


def analyze(text):
    return [stem(t) for t in tokenize(text) if t not in STOP_WORDS]


# ---------------------------------------------------------------------------
# Inverted index with TF-IDF
# ---------------------------------------------------------------------------

class SearchIndex:
    def __init__(self):
        self.postings = defaultdict(dict)
        self.doc_count = 0
        self.documents = {}

    def add(self, doc_id, text):
        self.documents[doc_id] = text
        self.doc_count += 1
        terms = analyze(text)
        tf = defaultdict(int)
        for t in terms:
            tf[t] += 1
        for t, count in tf.items():
            self.postings[t][doc_id] = count

    def search(self, query, top_k=10):
        terms = analyze(query)
        if not terms:
            return []
        scores = defaultdict(float)
        for term in terms:
            if term not in self.postings:
                continue
            df = len(self.postings[term])
            idf = math.log(self.doc_count / df) if df else 0
            for doc_id, tf in self.postings[term].items():
                scores[doc_id] += tf * idf
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]


# ---------------------------------------------------------------------------
# Flask API
# ---------------------------------------------------------------------------

app = Flask(__name__)
index = SearchIndex()


@app.route("/index", methods=["POST"])
def index_document():
    data = request.get_json()
    if not data or "id" not in data or "text" not in data:
        return jsonify({"error": "Provide 'id' and 'text' fields"}), 400
    index.add(data["id"], data["text"])
    return jsonify({"status": "indexed", "id": data["id"]})


@app.route("/search", methods=["GET"])
def search():
    query = request.args.get("q", "")
    top_k = int(request.args.get("top_k", 10))
    if not query:
        return jsonify({"error": "Provide query parameter 'q'"}), 400
    results = index.search(query, top_k)
    return jsonify({
        "query": query,
        "results": [
            {"id": doc_id, "score": round(score, 4), "text": index.documents[doc_id]}
            for doc_id, score in results
        ],
    })


@app.route("/stats", methods=["GET"])
def stats():
    return jsonify({
        "document_count": index.doc_count,
        "vocabulary_size": len(index.postings),
    })


# ---------------------------------------------------------------------------
# Seed data and startup
# ---------------------------------------------------------------------------

SEED_DOCS = [
    ("1", "B-trees are the default index structure in PostgreSQL and MySQL"),
    ("2", "LSM trees use sequential writes and are optimized for write-heavy workloads"),
    ("3", "Elasticsearch is built on top of Apache Lucene and uses inverted indexes"),
    ("4", "Inverted indexes map terms to posting lists of document identifiers"),
    ("5", "PostgreSQL supports B-tree, hash, GiST, GIN, and BRIN index types"),
    ("6", "Cassandra uses LSM trees with compaction to manage on-disk data"),
    ("7", "BM25 scoring improves on TF-IDF with term frequency saturation"),
    ("8", "Composite indexes should place equality columns before range columns"),
]


def seed():
    for doc_id, text in SEED_DOCS:
        index.add(doc_id, text)
    print(f"Seeded {len(SEED_DOCS)} documents")


if __name__ == "__main__":
    seed()
    print("Starting search API on http://localhost:5000")
    print("Try: curl 'http://localhost:5000/search?q=PostgreSQL+index'\n")
    app.run(debug=False, port=5000)
