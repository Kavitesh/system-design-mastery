"""
Video Transcoding Pipeline Simulator
=====================================
Simulates parallel video transcoding across a resolution x codec matrix.
Shows progress, output sizes, and pipeline timing.

Run:  python transcoding_pipeline.py
"""

import time, random, uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------------------------------------------------------------------------

RESOLUTIONS = [
    {"name": "1080p", "factor": 1.0},
    {"name": "720p",  "factor": 0.55},
    {"name": "480p",  "factor": 0.22},
    {"name": "360p",  "factor": 0.11},
]

CODECS = [
    {"name": "H.264", "base_kbps": 4500, "speed": 1.0},
    {"name": "VP9",   "base_kbps": 3000, "speed": 2.5},
    {"name": "AV1",   "base_kbps": 2000, "speed": 8.0},
]

VIDEOS = [
    {"title": "Python Flask Tutorial",     "dur": 1847, "raw_mb": 2800},
    {"title": "System Design Interview",   "dur": 2415, "raw_mb": 3700},
    {"title": "Kubernetes Full Course",     "dur": 7200, "raw_mb": 11000},
]

def fmt_size(mb):
    return f"{mb/1024:.1f} GB" if mb >= 1024 else f"{mb:.0f} MB"

def fmt_dur(s):
    h, r = divmod(int(s), 3600); m, s = divmod(r, 60)
    return f"{h}h{m:02d}m" if h else f"{m}m{s:02d}s"

# ---------------------------------------------------------------------------

def transcode_job(title, dur, res, codec):
    """Simulate one rendition encode with timing proportional to codec speed."""
    t = 0.3 * codec["speed"] * (dur / 3600) * random.uniform(0.8, 1.2)
    time.sleep(t)
    bitrate = codec["base_kbps"] * res["factor"]
    size_mb = (bitrate / 8) * dur / 1024
    failed = random.random() < 0.03
    return {"res": res["name"], "codec": codec["name"], "kbps": bitrate,
            "size_mb": size_mb, "time": t, "ok": not failed}

def run_pipeline():
    print("=" * 70)
    print("VIDEO TRANSCODING PIPELINE")
    print("=" * 70)
    print(f"Resolutions: {', '.join(r['name'] for r in RESOLUTIONS)}")
    print(f"Codecs: {', '.join(c['name'] for c in CODECS)}")
    print(f"Renditions per video: {len(RESOLUTIONS) * len(CODECS)}\n")

    grand_output, grand_raw = 0.0, 0

    for video in VIDEOS:
        print("-" * 70)
        print(f"{video['title']}  |  {fmt_dur(video['dur'])}  |  Raw: {fmt_size(video['raw_mb'])}\n")

        jobs = [(video["title"], video["dur"], r, c) for r in RESOLUTIONS for c in CODECS]
        done, failed, output_mb = 0, 0, 0.0
        t0 = time.time()

        with ThreadPoolExecutor(max_workers=6) as pool:
            futures = {pool.submit(transcode_job, *j): j for j in jobs}
            for f in as_completed(futures):
                r = f.result(); done += 1
                tag = f"[{done:2d}/{len(jobs)}]"
                if r["ok"]:
                    output_mb += r["size_mb"]
                    print(f"  {tag} {r['res']:>5s}/{r['codec']:<5s} -> "
                          f"{r['kbps']:6.0f} kbps  {fmt_size(r['size_mb']):>8s}  [{r['time']:.1f}s]")
                else:
                    failed += 1
                    print(f"  {tag} {r['res']:>5s}/{r['codec']:<5s} -> FAILED")

        elapsed = time.time() - t0
        grand_output += output_mb; grand_raw += video["raw_mb"]
        print(f"\n  Wall time: {elapsed:.1f}s  |  Output: {fmt_size(output_mb)}  |  "
              f"Ratio: {output_mb/video['raw_mb']:.1%} of raw  |  Failed: {failed}")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print(f"  Total raw:     {fmt_size(grand_raw)}")
    print(f"  Total encoded: {fmt_size(grand_output)}")
    print(f"  Compression:   {grand_output/grand_raw:.1%} of raw")
    print(f"\n  Encoding ladder:")
    print(f"  {'Res':<8s} {'Codec':<6s} {'Bitrate':>8s}")
    for r in RESOLUTIONS:
        for c in CODECS:
            print(f"  {r['name']:<8s} {c['name']:<6s} {c['base_kbps']*r['factor']:>7.0f} kbps")

    avg_dur = sum(v["dur"] for v in VIDEOS) / len(VIDEOS)
    uploads_min = 500 * 3600 / avg_dur
    print(f"\n  YouTube scale (500 hrs/min): ~{uploads_min:,.0f} uploads/min, "
          f"~{uploads_min * 12:,.0f} renditions/min")

# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Transcoding pipeline starting")
    run_pipeline()
