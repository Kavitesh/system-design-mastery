"""
File Storage API
================
Flask API with upload, download, versioning, and block-level deduplication.

    pip install flask
    python file_storage.py

    curl -X POST -F "file=@myfile.txt" http://localhost:5000/files/
    curl http://localhost:5000/files/
    curl http://localhost:5000/files/<id>/versions
    curl http://localhost:5000/stats
"""

import hashlib, os, uuid
from datetime import datetime
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

# ---------------------------------------------------------------------------
BLOCK_DIR = "/tmp/file_storage_blocks"
BLOCK_SIZE = 4096
files_db = {}
versions_db = {}
blocks_index = {}
os.makedirs(BLOCK_DIR, exist_ok=True)

# ---------------------------------------------------------------------------

def store_block(block_hash: str, data: bytes) -> bool:
    if block_hash in blocks_index:
        blocks_index[block_hash]["ref_count"] += 1
        return False
    path = os.path.join(BLOCK_DIR, block_hash[:2], block_hash)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    blocks_index[block_hash] = {"size": len(data), "ref_count": 1}
    return True


def reassemble(block_hashes: list[str]) -> bytes:
    parts = []
    for h in block_hashes:
        with open(os.path.join(BLOCK_DIR, h[:2], h), "rb") as f:
            parts.append(f.read())
    return b"".join(parts)

# ---------------------------------------------------------------------------

@app.route("/files/", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    uploaded = request.files["file"]
    data = uploaded.read()
    checksum = hashlib.sha256(data).hexdigest()

    file_id = request.form.get("file_id")
    is_update = file_id and file_id in files_db
    version = files_db[file_id]["current_version"] + 1 if is_update else 1
    if not is_update:
        file_id = str(uuid.uuid4())[:8]

    hashes, new, deduped = [], 0, 0
    for i in range(0, len(data), BLOCK_SIZE):
        chunk = data[i:i + BLOCK_SIZE]
        h = hashlib.sha256(chunk).hexdigest()
        hashes.append(h)
        if store_block(h, chunk):
            new += 1
        else:
            deduped += 1

    now = datetime.utcnow().isoformat()
    if is_update:
        files_db[file_id].update(current_version=version, updated_at=now)
    else:
        files_db[file_id] = {"name": uploaded.filename, "current_version": 1, "created_at": now, "updated_at": now}
    versions_db[(file_id, version)] = {"blocks": hashes, "size": len(data), "checksum": checksum, "created_at": now}

    return jsonify({"file_id": file_id, "version": version, "size": len(data),
                    "blocks": len(hashes), "new_blocks": new, "deduped_blocks": deduped}), 201


@app.route("/files/", methods=["GET"])
def list_files():
    items = [{"file_id": fid, "name": m["name"], "version": m["current_version"],
              "size": versions_db.get((fid, m["current_version"]), {}).get("size", 0)}
             for fid, m in files_db.items()]
    return jsonify({"files": items, "count": len(items)})


@app.route("/files/<file_id>/download")
def download_file(file_id):
    if file_id not in files_db:
        return jsonify({"error": "Not found"}), 404
    ver = files_db[file_id]["current_version"]
    content = reassemble(versions_db[(file_id, ver)]["blocks"])
    tmp = f"/tmp/dl_{file_id}"
    with open(tmp, "wb") as f:
        f.write(content)
    return send_file(tmp, download_name=files_db[file_id]["name"], as_attachment=True)


@app.route("/files/<file_id>/versions")
def list_versions(file_id):
    if file_id not in files_db:
        return jsonify({"error": "Not found"}), 404
    vers = [{"version": v, "size": d["size"], "checksum": d["checksum"][:12], "blocks": len(d["blocks"])}
            for (fid, v), d in versions_db.items() if fid == file_id]
    return jsonify({"file_id": file_id, "versions": sorted(vers, key=lambda x: x["version"], reverse=True)})


@app.route("/stats")
def storage_stats():
    unique = sum(b["size"] for b in blocks_index.values())
    logical = sum(b["size"] * b["ref_count"] for b in blocks_index.values())
    return jsonify({"files": len(files_db), "versions": len(versions_db), "unique_blocks": len(blocks_index),
                    "unique_bytes": unique, "logical_bytes": logical,
                    "dedup_savings": f"{(1 - unique/logical)*100:.1f}%" if logical else "0%"})

# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("File Storage API running on http://localhost:5000")
    app.run(debug=True, port=5000)
