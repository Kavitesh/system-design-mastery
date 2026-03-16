# Chapter 39 - Code Labs

Hands-on demos for file storage system concepts.

## Labs

| # | File | Concepts |
|---|------|----------|
| 1 | `file_storage.py` | Flask API for upload, download, and file versioning |
| 2 | `chunking.py` | Split files into content-addressed blocks with deduplication |
| 3 | `sync_engine.py` | Detect local changes and resolve sync conflicts |
| 4 | `sharing.py` | File sharing with viewer, editor, and owner permissions |

## Running the Labs

Each lab runs standalone with no external dependencies beyond Flask (lab 1 only).

```bash
# Lab 1 - File storage API (requires Flask)
pip install flask
python file_storage.py

# Lab 2 - Chunking and deduplication
python chunking.py

# Lab 3 - Sync engine simulation
python sync_engine.py

# Lab 4 - Sharing and permissions
python sharing.py
```

## Key Takeaways

- **Chunking** turns a 1 GB upload problem into 256 small block uploads that can resume and deduplicate
- **Content-addressable storage** means identical blocks are never stored twice
- **Conflict resolution** via forking preserves both versions and lets users decide
- **Permission inheritance** from folders simplifies sharing but requires careful propagation
