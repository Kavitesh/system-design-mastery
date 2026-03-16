"""
Load Test  - Round-Robin Client
===============================
Sends requests to multiple server instances in round-robin fashion,
demonstrating horizontal scaling with stateless servers.

Prerequisites:
  1. Start servers: python stateless_server.py 5001
  2. Start servers: python stateless_server.py 5002
  3. Run this:     python load_test.py
"""

import requests
import time

SERVERS = ["http://localhost:5001", "http://localhost:5002"]
NUM_REQUESTS = 20


def main():
    print("╔═══════════════════════════════════════════════════╗")
    print("║   LOAD TEST  - Round-Robin Across Servers          ║")
    print("╚═══════════════════════════════════════════════════╝")
    print(f"\nServers: {SERVERS}")
    print(f"Sending {NUM_REQUESTS} requests...\n")

    server_counts = {s: 0 for s in SERVERS}

    for i in range(NUM_REQUESTS):
        # Round-robin: pick server based on request index
        server = SERVERS[i % len(SERVERS)]

        try:
            resp = requests.post(f"{server}/process", timeout=5)
            data = resp.json()
            server_counts[server] += 1
            print(f"  Request {i+1:>3} → {data['handled_by']:<15} "
                  f"(total across all: {data['total_requests']})")
        except requests.ConnectionError:
            print(f"  Request {i+1:>3} → {server} is DOWN! Skipping.")

        time.sleep(0.1)  # Small delay to see output clearly

    # Summary
    print(f"\n{'='*50}")
    print("DISTRIBUTION SUMMARY")
    print(f"{'='*50}")
    for server, count in server_counts.items():
        bar = "█" * count
        print(f"  {server}: {bar} ({count} requests)")

    # Check shared stats
    print(f"\nFetching shared stats from first server...")
    try:
        resp = requests.get(f"{SERVERS[0]}/stats", timeout=5)
        stats = resp.json()
        print(f"  Total requests (all servers): {stats['total_requests_all_servers']}")
        print(f"  Servers seen: {stats['servers_seen']}")
        print(f"\n  ✓ State is shared! Both servers see the same data.")
    except requests.ConnectionError:
        print("  Could not reach server for stats.")


if __name__ == "__main__":
    main()
