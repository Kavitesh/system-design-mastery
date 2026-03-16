# Chapter 35 - Video Streaming Platform - Code Lab

Hands-on demos covering the core subsystems of a video streaming platform: metadata management, transcoding, adaptive bitrate selection, and recommendations.

## Files

| File | Description | Key Concepts |
|---|---|---|
| `video_platform.py` | Flask API for video metadata with upload, listing, search, and view tracking | REST API, SQLite, full-text search, resumable uploads |
| `transcoding_pipeline.py` | Simulates parallel transcoding across resolutions and codecs with progress tracking | Pipeline stages, parallelism, codec/resolution matrix |
| `adaptive_streaming.py` | Demonstrates adaptive bitrate selection as bandwidth fluctuates | ABR algorithm, buffer management, quality switching |
| `recommendation.py` | Content-based recommendation engine using TF-IDF similarity | TF-IDF, cosine similarity, content-based filtering |

## Requirements

```bash
pip install flask
```

All demos use only Flask and Python standard library modules. No other dependencies needed.

## Running

Each file is standalone. Run any of them directly:

```bash
# Video metadata API (starts Flask server on port 5000)
python video_platform.py

# Transcoding pipeline simulation (runs and prints results)
python transcoding_pipeline.py

# Adaptive bitrate demo (simulates 60 seconds of playback)
python adaptive_streaming.py

# Recommendation engine (builds index and shows recommendations)
python recommendation.py
```

## Demo Details

### video_platform.py

Starts a Flask API with these endpoints:

```
POST   /api/videos/upload    - Upload video metadata (simulates resumable upload)
GET    /api/videos            - List all videos (with pagination)
GET    /api/videos/<id>       - Get video details (increments view count)
GET    /api/videos/search?q=  - Full-text search on title, description, tags
DELETE /api/videos/<id>       - Delete a video
```

Seeds the database with 8 sample videos on first run.

### transcoding_pipeline.py

Simulates the transcoding pipeline for a batch of uploaded videos. Shows:

- Parallel transcoding across 4 resolutions and 3 codecs (12 renditions per video)
- Progress bars for each transcoding job
- Estimated file sizes based on real bitrate calculations
- Total pipeline timing and output summary

### adaptive_streaming.py

Simulates a video player's adaptive bitrate algorithm over 60 seconds of playback with fluctuating bandwidth. Demonstrates:

- Quality level selection based on estimated bandwidth
- Buffer level management (filling and draining)
- Quality switches when bandwidth changes
- The tradeoff between quality and rebuffering

### recommendation.py

Builds a content-based recommendation engine from a catalog of videos. Shows:

- TF-IDF vectorization of video metadata (titles, descriptions, tags)
- Cosine similarity computation between videos
- "Because you watched X" recommendations
- User profile building from watch history
