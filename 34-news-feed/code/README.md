# Chapter 34 - Code Lab: News Feed System

Hands-on demos for the news feed design concepts.

## Files

| File | What It Does | Run It |
|---|---|---|
| `news_feed.py` | Flask social feed API with posts, follows, timeline | `python news_feed.py` |
| `fanout_comparison.py` | Benchmarks fan-out-on-write vs fan-out-on-read | `python fanout_comparison.py` |
| `feed_ranking.py` | Ranking algorithm with recency decay and engagement | `python feed_ranking.py` |
| `feed_cache.py` | Cached feed with write-through and invalidation | `python feed_cache.py` |

## Requirements

```bash
pip install flask
```

## Quick Start

```bash
# Run the full social feed API
python news_feed.py
# Then in another terminal:
# curl http://localhost:5000/post -X POST -H "Content-Type: application/json" -d '{"user_id": "alice", "content": "Hello world"}'
# curl http://localhost:5000/follow -X POST -H "Content-Type: application/json" -d '{"follower": "bob", "followee": "alice"}'
# curl http://localhost:5000/feed/bob

# Run standalone demos
python fanout_comparison.py
python feed_ranking.py
python feed_cache.py
```

Each file is self-contained and prints informative output.
