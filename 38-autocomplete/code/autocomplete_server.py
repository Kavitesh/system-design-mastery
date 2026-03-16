"""
Autocomplete API Server
========================
Flask server that serves autocomplete suggestions from an in-memory trie.
Loads a sample dataset at startup, exposes prefix search and stats endpoints.

Run: python autocomplete_server.py
Test: curl "http://localhost:5000/autocomplete?q=wea&k=5"
"""

import time
from flask import Flask, jsonify, request

# ---------------------------------------------------------------------------
# Trie (embedded so this file runs standalone)
# ---------------------------------------------------------------------------

import heapq


class TrieNode:
    __slots__ = ("children", "is_end", "frequency", "top_k")

    def __init__(self):
        self.children: dict[str, "TrieNode"] = {}
        self.is_end = False
        self.frequency = 0
        self.top_k: list[tuple[int, str]] = []


class Trie:
    def __init__(self, k: int = 10):
        self.root = TrieNode()
        self.k = k
        self._word_count = 0

    def insert(self, word: str, frequency: int = 1):
        node = self.root
        for char in word:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        if not node.is_end:
            self._word_count += 1
        node.is_end = True
        node.frequency += frequency

    def build_top_k_cache(self):
        self._build_cache(self.root, "")

    def _build_cache(self, node: TrieNode, prefix: str):
        candidates = []
        if node.is_end:
            candidates.append((node.frequency, prefix))
        for char, child in node.children.items():
            self._build_cache(child, prefix + char)
            candidates.extend(child.top_k)
        node.top_k = heapq.nlargest(self.k, candidates, key=lambda x: x[0])

    def search(self, prefix: str, k: int = None) -> list[tuple[int, str]]:
        node = self.root
        for char in prefix.lower():
            if char not in node.children:
                return []
            node = node.children[char]
        results = node.top_k
        if k and k < len(results):
            results = results[:k]
        return results

    @property
    def word_count(self):
        return self._word_count


# ---------------------------------------------------------------------------
# Sample dataset
# ---------------------------------------------------------------------------

QUERIES = [
    ("weather", 1500), ("weather tomorrow", 900), ("weather radar", 600),
    ("weather forecast", 550), ("weather map", 400),
    ("web design", 400), ("website builder", 350), ("webmail", 250),
    ("python tutorial", 1200), ("python download", 800), ("python flask", 450),
    ("python list comprehension", 500), ("python pandas", 380),
    ("pizza near me", 2000), ("pizza recipe", 700), ("pizza hut", 1100),
    ("pizza dough", 400), ("pizza delivery", 900),
    ("how to tie a tie", 900), ("how to lose weight", 1300),
    ("how to cook rice", 750), ("how to screenshot", 1100),
    ("machine learning", 1000), ("machine learning course", 600),
    ("mac address", 350), ("map of the world", 500),
    ("java tutorial", 700), ("javascript array methods", 500),
    ("netflix login", 1400), ("netflix shows", 800), ("news today", 1200),
    ("amazon prime", 1300), ("apple stock", 700), ("airline tickets", 550),
    ("best restaurants near me", 1100), ("best laptop 2026", 800),
    ("bitcoin price", 950), ("bank of america", 700),
    ("chatgpt", 2500), ("chatgpt login", 1800), ("costco hours", 500),
]


# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------

app = Flask(__name__)
trie = Trie(k=10)
request_count = 0
start_time = None


def load_trie():
    global start_time
    for query, freq in QUERIES:
        trie.insert(query.lower(), freq)
    trie.build_top_k_cache()
    start_time = time.time()


@app.route("/autocomplete")
def autocomplete():
    global request_count
    request_count += 1

    prefix = request.args.get("q", "").lower().strip()
    k = request.args.get("k", 10, type=int)

    if not prefix:
        return jsonify({"error": "query parameter 'q' is required"}), 400

    if len(prefix) > 100:
        return jsonify({"error": "prefix too long (max 100 chars)"}), 400

    lookup_start = time.perf_counter()
    results = trie.search(prefix, k=k)
    lookup_us = (time.perf_counter() - lookup_start) * 1_000_000

    suggestions = [{"query": word, "score": freq} for freq, word in results]

    return jsonify({
        "prefix": prefix,
        "count": len(suggestions),
        "suggestions": suggestions,
        "lookup_us": round(lookup_us, 1),
    })


@app.route("/stats")
def stats():
    uptime = time.time() - start_time if start_time else 0
    return jsonify({
        "queries_in_trie": trie.word_count,
        "requests_served": request_count,
        "uptime_seconds": round(uptime, 1),
    })


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/")
def index():
    return jsonify({
        "service": "autocomplete",
        "endpoints": {
            "/autocomplete?q=<prefix>&k=<top_k>": "Get suggestions for a prefix",
            "/stats": "Server statistics",
            "/health": "Health check",
        },
    })


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    load_trie()
    print(f"Autocomplete server ready - {trie.word_count} queries loaded - http://localhost:5000")
    app.run(port=5000, debug=False)
