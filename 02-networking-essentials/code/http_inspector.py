"""
HTTP Inspector
==============
Makes an HTTP request and displays the full conversation:
headers, status codes, timing breakdown, and response body.

Run:
  python http_inspector.py https://httpbin.org/get
  python http_inspector.py https://httpbin.org/status/404
  python http_inspector.py https://httpbin.org/post --method POST --body '{"test": true}'
"""

import sys
import time
import json

import requests


def inspect_request(url: str, method: str = "GET", body: str = None):
    print(f"\n{'='*65}")
    print(f"  HTTP INSPECTOR")
    print(f"{'='*65}\n")

    # Prepare request
    headers = {
        "User-Agent": "SystemDesign-HTTPInspector/1.0",
        "Accept": "application/json",
    }

    print(f"[REQUEST]")
    print(f"  {method} {url}")
    print(f"  Headers:")
    for k, v in headers.items():
        print(f"    {k}: {v}")

    if body:
        print(f"  Body: {body}")
    print()

    # Send request with timing
    start = time.time()
    try:
        if method.upper() == "POST":
            resp = requests.post(url, headers=headers, data=body, timeout=10)
        elif method.upper() == "PUT":
            resp = requests.put(url, headers=headers, data=body, timeout=10)
        elif method.upper() == "DELETE":
            resp = requests.delete(url, headers=headers, timeout=10)
        else:
            resp = requests.get(url, headers=headers, timeout=10)
    except requests.exceptions.ConnectionError:
        print(f"  ERROR: Could not connect to {url}")
        return
    except requests.exceptions.Timeout:
        print(f"  ERROR: Request timed out")
        return

    total_time = (time.time() - start) * 1000

    # Display response
    print(f"[RESPONSE]")
    print(f"  Status: {resp.status_code} {resp.reason}")
    status_category = {
        2: "SUCCESS",
        3: "REDIRECTION",
        4: "CLIENT ERROR",
        5: "SERVER ERROR",
    }
    category = status_category.get(resp.status_code // 100, "UNKNOWN")
    print(f"  Category: {category}")
    print()

    print(f"  Response Headers:")
    for k, v in resp.headers.items():
        print(f"    {k}: {v}")
    print()

    # Timing breakdown
    print(f"[TIMING]")
    print(f"  Total time: {total_time:.0f}ms")
    if resp.elapsed:
        print(f"  Server time: {resp.elapsed.total_seconds()*1000:.0f}ms")
    print()

    # Response body (truncated)
    print(f"[BODY]")
    try:
        body_json = resp.json()
        formatted = json.dumps(body_json, indent=2)
        lines = formatted.split("\n")
        if len(lines) > 20:
            print("  " + "\n  ".join(lines[:20]))
            print(f"  ... ({len(lines) - 20} more lines)")
        else:
            print("  " + "\n  ".join(lines))
    except (json.JSONDecodeError, ValueError):
        text = resp.text[:500]
        print(f"  {text}")
        if len(resp.text) > 500:
            print(f"  ... (truncated, total {len(resp.text)} chars)")

    # Summary
    print()
    print(f"{'='*65}")
    print(f"HTTP STATUS CODE QUICK REFERENCE:")
    print(f"  2xx  - Success     (200 OK, 201 Created, 204 No Content)")
    print(f"  3xx  - Redirect    (301 Permanent, 302 Temporary, 304 Not Modified)")
    print(f"  4xx  - Client Err  (400 Bad Request, 401 Unauth, 404 Not Found)")
    print(f"  5xx  - Server Err  (500 Internal, 502 Bad Gateway, 503 Unavailable)")
    print(f"{'='*65}")


def main():
    if len(sys.argv) < 2:
        url = "https://httpbin.org/get"
        print(f"No URL specified. Using default: {url}")
        print(f"Usage: python http_inspector.py <url> [--method POST] [--body 'data']")
    else:
        url = sys.argv[1]

    method = "GET"
    body = None

    for i, arg in enumerate(sys.argv):
        if arg == "--method" and i + 1 < len(sys.argv):
            method = sys.argv[i + 1]
        if arg == "--body" and i + 1 < len(sys.argv):
            body = sys.argv[i + 1]

    inspect_request(url, method, body)


if __name__ == "__main__":
    main()
