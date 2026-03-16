"""
REST API Demo
=============
A simple CRUD API for managing books. Shows proper HTTP methods,
status codes, URL versioning, and pagination.

Run: python rest_api.py
"""

from flask import Flask, request, jsonify
import uuid

app = Flask(__name__)

# In-memory "database"
books = {}


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "service": "Book API (REST)",
        "version": "v1",
        "endpoints": [
            "GET    /api/v1/books",
            "GET    /api/v1/books/<id>",
            "POST   /api/v1/books",
            "PUT    /api/v1/books/<id>",
            "DELETE /api/v1/books/<id>",
        ]
    })


# ---------------------------------------------------------------------------
# CREATE
# ---------------------------------------------------------------------------

@app.route("/api/v1/books", methods=["POST"])
def create_book():
    data = request.get_json()

    if not data or "title" not in data or "author" not in data:
        return jsonify({"error": "title and author are required"}), 400

    book_id = str(uuid.uuid4())[:8]
    book = {
        "id": book_id,
        "title": data["title"],
        "author": data["author"],
        "year": data.get("year"),
    }
    books[book_id] = book

    return jsonify(book), 201


# ---------------------------------------------------------------------------
# READ (list with pagination)
# ---------------------------------------------------------------------------

@app.route("/api/v1/books", methods=["GET"])
def list_books():
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 10, type=int)
    limit = min(limit, 100)

    all_books = list(books.values())
    start = (page - 1) * limit
    page_books = all_books[start:start + limit]

    return jsonify({
        "data": page_books,
        "page": page,
        "limit": limit,
        "total": len(all_books),
    })


# ---------------------------------------------------------------------------
# READ (single)
# ---------------------------------------------------------------------------

@app.route("/api/v1/books/<book_id>", methods=["GET"])
def get_book(book_id):
    book = books.get(book_id)
    if not book:
        return jsonify({"error": "book not found"}), 404
    return jsonify(book)


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------

@app.route("/api/v1/books/<book_id>", methods=["PUT"])
def update_book(book_id):
    if book_id not in books:
        return jsonify({"error": "book not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "request body required"}), 400

    book = books[book_id]
    book["title"] = data.get("title", book["title"])
    book["author"] = data.get("author", book["author"])
    book["year"] = data.get("year", book["year"])

    return jsonify(book)


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------

@app.route("/api/v1/books/<book_id>", methods=["DELETE"])
def delete_book(book_id):
    if book_id not in books:
        return jsonify({"error": "book not found"}), 404
    del books[book_id]
    return "", 204


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Seed some sample data
    for title, author, year in [
        ("Designing Data-Intensive Applications", "Martin Kleppmann", 2017),
        ("System Design Interview", "Alex Xu", 2020),
        ("Clean Code", "Robert C. Martin", 2008),
    ]:
        bid = str(uuid.uuid4())[:8]
        books[bid] = {"id": bid, "title": title, "author": author, "year": year}

    print(f"\n  REST API running at http://localhost:5000")
    print(f"  Try: curl http://localhost:5000/api/v1/books\n")

    app.run(port=5000, debug=True)
