# URL Shortener - Code Lab

Hands-on demos covering URL shortening algorithms, a working Flask shortener, click analytics, and load testing.

## What's Included

| File | Description |
|------|-------------|
| `url_shortener.py` | Full Flask URL shortener with base62 encoding, SQLite storage, and redirects |
| `encoding_comparison.py` | Side-by-side comparison of base62, MD5, and UUID approaches |
| `analytics.py` | Click tracking and analytics dashboard for shortened URLs |
| `load_test.py` | Load testing the URL shortener to measure throughput and latency |

## Prerequisites

```bash
pip install flask requests
```

## Running the Demos

### 1. URL Shortener Service

A complete URL shortener with create, redirect, and stats endpoints:

```bash
python url_shortener.py
```

Then in another terminal:

```bash
# Shorten a URL
curl -X POST http://localhost:5000/api/v1/urls \
  -H "Content-Type: application/json" \
  -d '{"long_url": "https://example.com/very/long/path/to/something"}'

# Use the returned short code to test redirect
curl -v http://localhost:5000/a1B2c3

# Check stats
curl http://localhost:5000/api/v1/urls/a1B2c3/stats
```

### 2. Encoding Comparison

Compare base62, MD5, and UUID approaches for generating short codes - collision rates, speed, and code length:

```bash
python encoding_comparison.py
```

### 3. Analytics Dashboard

Simulates click traffic and shows analytics breakdowns by time, referrer, country, and device:

```bash
python analytics.py
```

### 4. Load Test

Start the URL shortener first, then run the load test to measure throughput:

```bash
# Terminal 1
python url_shortener.py

# Terminal 2
python load_test.py
```
