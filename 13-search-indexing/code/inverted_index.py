"""
inverted_index.py
=================
A from-scratch inverted index with tokenization, stop word removal, and
TF-IDF ranking. Indexes a small document corpus and runs ranked search
queries to show how full-text search engines work under the hood.

Run:
    python inverted_index.py
"""

import math
import re
from collections import defaultdict

# ---------------------------------------------------------------------------
# Text analysis pipeline
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
    """Lowercase, strip punctuation, split on whitespace."""
    return re.findall(r"[a-z0-9]+", text.lower())


def remove_stop_words(tokens):
    return [t for t in tokens if t not in STOP_WORDS]


def stem(word):
    """A crude suffix-stripping stemmer. Production systems use Porter or
    Snowball, but this captures the core idea: reduce variant forms to a
    common root so that 'running' and 'runs' match the same index entry."""
    if len(word) <= 3:
        return word
    for suffix, replacement in SUFFIX_RULES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 2:
            return word[: -len(suffix)] + replacement
            break
    return word


def analyze(text):
    return [stem(t) for t in remove_stop_words(tokenize(text))]


# ---------------------------------------------------------------------------
# Inverted index with TF-IDF scoring
# ---------------------------------------------------------------------------

class InvertedIndex:
    """Maps terms to posting lists. Each posting stores the document ID and
    the term frequency within that document. Queries return documents ranked
    by TF-IDF score."""

    def __init__(self):
        self.postings = defaultdict(dict)  # term -> {doc_id: tf}
        self.doc_count = 0
        self.documents = {}  # doc_id -> original text

    def add_document(self, doc_id, text):
        self.documents[doc_id] = text
        self.doc_count += 1
        terms = analyze(text)
        tf_counts = defaultdict(int)
        for term in terms:
            tf_counts[term] += 1
        for term, count in tf_counts.items():
            self.postings[term][doc_id] = count

    def search(self, query, top_k=10):
        query_terms = analyze(query)
        if not query_terms:
            return []
        scores = defaultdict(float)
        for term in query_terms:
            if term not in self.postings:
                continue
            df = len(self.postings[term])
            idf = math.log(self.doc_count / df) if df > 0 else 0
            for doc_id, tf in self.postings[term].items():
                scores[doc_id] += tf * idf
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]

    def vocabulary_size(self):
        return len(self.postings)


# ---------------------------------------------------------------------------
# Demo corpus and queries
# ---------------------------------------------------------------------------

CORPUS = [
    ("d1", "B-trees are the default index structure in PostgreSQL and MySQL"),
    ("d2", "LSM trees use sequential writes and are optimized for write-heavy workloads"),
    ("d3", "Elasticsearch is built on top of Apache Lucene and uses inverted indexes"),
    ("d4", "Inverted indexes map terms to posting lists of document identifiers"),
    ("d5", "PostgreSQL supports B-tree, hash, GiST, GIN, and BRIN index types"),
    ("d6", "Write amplification is the ratio of physical writes to logical writes"),
    ("d7", "Cassandra uses LSM trees with compaction to manage on-disk data"),
    ("d8", "Full-text search engines tokenize text and remove stop words before indexing"),
    ("d9", "BM25 scoring improves on TF-IDF with term frequency saturation"),
    ("d10", "Composite indexes follow the leftmost prefix rule for query matching"),
]

QUERIES = [
    "PostgreSQL index",
    "LSM tree write",
    "inverted index search",
    "BM25 TF-IDF scoring",
    "Elasticsearch Lucene",
]


def main():
    idx = InvertedIndex()
    for doc_id, text in CORPUS:
        idx.add_document(doc_id, text)

    print(f"Indexed {idx.doc_count} documents, {idx.vocabulary_size()} unique terms\n")

    for query in QUERIES:
        results = idx.search(query)
        print(f'Query: "{query}"')
        if not results:
            print("  No results\n")
            continue
        for doc_id, score in results:
            preview = idx.documents[doc_id][:70]
            print(f"  {doc_id}  score={score:.3f}  {preview}...")
        print()


if __name__ == "__main__":
    main()
