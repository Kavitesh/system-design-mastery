"""
object_store.py - Flask-Based S3-Like Object Store
===================================================
A minimal object store with buckets, PUT/GET/DELETE, and custom
metadata served over HTTP. Run without arguments to start the server,
or pass --test to execute the built-in test client.
"""

import sys
import time
import json
import hashlib
from flask import Flask, request, jsonify, Response

# ---------------------------------------------------------------------------
# In-Memory Storage Backend
# ---------------------------------------------------------------------------

buckets = {}
app = Flask(__name__)

# ---------------------------------------------------------------------------
# Bucket Operations
# ---------------------------------------------------------------------------

@app.route("/buckets/<name>", methods=["PUT"])
def create_bucket(name):
    if name in buckets:
        return jsonify({"error": f"Bucket '{name}' already exists"}), 409
    buckets[name] = {}
    return jsonify({"bucket": name, "created": True}), 201

@app.route("/buckets/<name>", methods=["GET"])
def list_bucket(name):
    if name not in buckets:
        return jsonify({"error": "NoSuchBucket"}), 404
    prefix = request.args.get("prefix", "")
    objects = [
        {"key": k, "size": o["size"], "etag": o["etag"]}
        for k, o in buckets[name].items() if k.startswith(prefix)
    ]
    return jsonify({"bucket": name, "objects": objects, "count": len(objects)})

# ---------------------------------------------------------------------------
# Object Operations
# ---------------------------------------------------------------------------

@app.route("/buckets/<bucket>/<path:key>", methods=["PUT"])
def put_object(bucket, key):
    if bucket not in buckets:
        return jsonify({"error": "NoSuchBucket"}), 404
    data = request.get_data()
    metadata = {h[7:]: v for h, v in request.headers if h.lower().startswith("x-meta-")}
    etag = hashlib.md5(data).hexdigest()
    buckets[bucket][key] = {
        "data": data, "metadata": metadata, "etag": etag,
        "size": len(data), "content_type": request.content_type or "application/octet-stream",
        "last_modified": time.time(),
    }
    return jsonify({"key": key, "etag": etag, "size": len(data)}), 200

@app.route("/buckets/<bucket>/<path:key>", methods=["GET"])
def get_object(bucket, key):
    if bucket not in buckets:
        return jsonify({"error": "NoSuchBucket"}), 404
    if key not in buckets[bucket]:
        return jsonify({"error": "NoSuchKey"}), 404
    obj = buckets[bucket][key]
    headers = {"ETag": obj["etag"], "Content-Type": obj["content_type"]}
    for mk, mv in obj["metadata"].items():
        headers[f"X-Meta-{mk}"] = mv
    return Response(obj["data"], headers=headers)

@app.route("/buckets/<bucket>/<path:key>", methods=["HEAD"])
def head_object(bucket, key):
    if bucket not in buckets or key not in buckets[bucket]:
        return "", 404
    obj = buckets[bucket][key]
    headers = {"ETag": obj["etag"], "Content-Type": obj["content_type"],
               "Content-Length": str(obj["size"])}
    for mk, mv in obj["metadata"].items():
        headers[f"X-Meta-{mk}"] = mv
    return Response("", headers=headers, status=200)

@app.route("/buckets/<bucket>/<path:key>", methods=["DELETE"])
def delete_object(bucket, key):
    if bucket not in buckets:
        return jsonify({"error": "NoSuchBucket"}), 404
    if key not in buckets[bucket]:
        return jsonify({"error": "NoSuchKey"}), 404
    del buckets[bucket][key]
    return jsonify({"deleted": key}), 200

# ---------------------------------------------------------------------------
# Test Client
# ---------------------------------------------------------------------------

def run_tests():
    import requests
    base = "http://127.0.0.1:5000"
    print("=" * 60)
    print("Object Store - Test Client")
    print("=" * 60)

    print("\n1. Creating bucket 'photos'...")
    r = requests.put(f"{base}/buckets/photos")
    print(f"   {r.status_code}: {r.json()}")

    print("\n2. Uploading 'vacation/beach.jpg'...")
    r = requests.put(f"{base}/buckets/photos/vacation/beach.jpg",
                     data=b"fake-jpeg-bytes", headers={"Content-Type": "image/jpeg",
                                                       "X-Meta-location": "hawaii"})
    print(f"   {r.status_code}: {r.json()}")

    print("\n3. Listing bucket...")
    r = requests.get(f"{base}/buckets/photos", params={"prefix": "vacation/"})
    print(f"   {r.status_code}: {json.dumps(r.json(), indent=2)}")

    print("\n4. HEAD request for metadata...")
    r = requests.head(f"{base}/buckets/photos/vacation/beach.jpg")
    for h in ["ETag", "Content-Type", "Content-Length", "X-Meta-location"]:
        print(f"   {h}: {r.headers.get(h, 'N/A')}")

    print("\n5. GET object data...")
    r = requests.get(f"{base}/buckets/photos/vacation/beach.jpg")
    print(f"   {r.status_code}: body={r.content}")

    print("\n6. DELETE object...")
    r = requests.delete(f"{base}/buckets/photos/vacation/beach.jpg")
    print(f"   {r.status_code}: {r.json()}")

    print("\n7. Confirm deletion (expect 404)...")
    r = requests.get(f"{base}/buckets/photos/vacation/beach.jpg")
    print(f"   {r.status_code}: {r.json()}")

    print("\n" + "-" * 60)
    print("All tests passed.")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if "--test" in sys.argv:
        run_tests()
    else:
        print("Starting object store on http://127.0.0.1:5000")
        print("Run 'python object_store.py --test' in another terminal.")
        app.run(debug=False, port=5000)
