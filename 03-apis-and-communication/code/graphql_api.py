"""
GraphQL API Demo
================
Query exactly the fields you need. One endpoint, no over-fetching,
no under-fetching. Uses graphql-core with Flask.

Run: python graphql_api.py
"""

from flask import Flask, request, jsonify
from graphql import (
    GraphQLSchema, GraphQLObjectType, GraphQLField,
    GraphQLString, GraphQLInt, GraphQLList, GraphQLArgument,
    GraphQLNonNull, graphql_sync,
)

app = Flask(__name__)

# ---------------------------------------------------------------------------
# In-memory data
# ---------------------------------------------------------------------------

authors_db = {
    "a1": {"id": "a1", "name": "Martin Kleppmann", "country": "UK"},
    "a2": {"id": "a2", "name": "Alex Xu", "country": "US"},
}

books_db = {
    "b1": {"id": "b1", "title": "Designing Data-Intensive Applications", "year": 2017, "author_id": "a1"},
    "b2": {"id": "b2", "title": "System Design Interview Vol 1", "year": 2020, "author_id": "a2"},
    "b3": {"id": "b3", "title": "System Design Interview Vol 2", "year": 2022, "author_id": "a2"},
}

# ---------------------------------------------------------------------------
# GraphQL Types
# ---------------------------------------------------------------------------

author_type = GraphQLObjectType(
    "Author",
    lambda: {
        "id": GraphQLField(GraphQLString),
        "name": GraphQLField(GraphQLString),
        "country": GraphQLField(GraphQLString),
        "books": GraphQLField(
            GraphQLList(book_type),
            resolve=lambda author, info: [
                b for b in books_db.values() if b["author_id"] == author["id"]
            ],
        ),
    },
)

book_type = GraphQLObjectType(
    "Book",
    lambda: {
        "id": GraphQLField(GraphQLString),
        "title": GraphQLField(GraphQLString),
        "year": GraphQLField(GraphQLInt),
        "author": GraphQLField(
            author_type,
            resolve=lambda book, info: authors_db.get(book["author_id"]),
        ),
    },
)

# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

query_type = GraphQLObjectType(
    "Query",
    {
        "book": GraphQLField(
            book_type,
            args={"id": GraphQLArgument(GraphQLNonNull(GraphQLString))},
            resolve=lambda root, info, id: books_db.get(id),
        ),
        "books": GraphQLField(
            GraphQLList(book_type),
            resolve=lambda root, info: list(books_db.values()),
        ),
        "author": GraphQLField(
            author_type,
            args={"id": GraphQLArgument(GraphQLNonNull(GraphQLString))},
            resolve=lambda root, info, id: authors_db.get(id),
        ),
    },
)

# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------

def _add_book(title, author_id, year):
    book_id = f"b{len(books_db) + 1}"
    book = {"id": book_id, "title": title, "year": year, "author_id": author_id}
    books_db[book_id] = book
    return book


mutation_type = GraphQLObjectType(
    "Mutation",
    {
        "addBook": GraphQLField(
            book_type,
            args={
                "title": GraphQLArgument(GraphQLNonNull(GraphQLString)),
                "year": GraphQLArgument(GraphQLInt),
                "author_id": GraphQLArgument(GraphQLNonNull(GraphQLString)),
            },
            resolve=lambda root, info, title, author_id, year=None: _add_book(title, author_id, year),
        ),
    },
)

schema = GraphQLSchema(query=query_type, mutation=mutation_type)

# ---------------------------------------------------------------------------
# Flask endpoint
# ---------------------------------------------------------------------------

@app.route("/graphql", methods=["POST"])
def graphql_endpoint():
    data = request.get_json()
    result = graphql_sync(
        schema,
        data.get("query", ""),
        variable_values=data.get("variables", {}),
    )

    response = {}
    if result.data:
        response["data"] = result.data
    if result.errors:
        response["errors"] = [str(e) for e in result.errors]

    return jsonify(response), 200 if not result.errors else 400


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "service": "Book API (GraphQL)",
        "endpoint": "POST /graphql",
        "example_queries": [
            '{ books { title, year } }',
            '{ book(id: "b1") { title, author { name, country } } }',
            '{ author(id: "a2") { name, books { title, year } } }',
        ],
    })


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"\n  GraphQL API running at http://localhost:5001")
    print(f"  Try: curl -X POST http://localhost:5001/graphql \\")
    print(f'       -H "Content-Type: application/json" \\')
    print(f"       -d '{{\"query\": \"{{ books {{ title, year }} }}\"}}'")
    print()

    app.run(port=5001, debug=True)
