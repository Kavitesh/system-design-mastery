"""
DNS Lookup Tool
===============
Performs DNS resolution and displays the full record breakdown,
showing how domain names map to IP addresses.

Run:
  python dns_lookup.py google.com
  python dns_lookup.py github.com
"""

import socket
import sys
import time


def resolve_dns(domain: str):
    print(f"\n{'='*60}")
    print(f"  DNS LOOKUP: {domain}")
    print(f"{'='*60}\n")

    # Step 1: Basic A record lookup
    print("[1] A Record (Domain -> IPv4 Address)")
    print("-" * 40)
    start = time.time()
    try:
        ip = socket.gethostbyname(domain)
        elapsed = (time.time() - start) * 1000
        print(f"    {domain} -> {ip}")
        print(f"    Resolution time: {elapsed:.2f}ms")
    except socket.gaierror as e:
        print(f"    Failed: {e}")
        return
    print()

    # Step 2: Get all addresses (there may be multiple)
    print("[2] All Addresses (may include round-robin IPs)")
    print("-" * 40)
    try:
        results = socket.getaddrinfo(domain, 80, socket.AF_UNSPEC, socket.SOCK_STREAM)
        seen = set()
        for family, socktype, proto, canonname, sockaddr in results:
            addr = sockaddr[0]
            if addr not in seen:
                seen.add(addr)
                family_name = "IPv4" if family == socket.AF_INET else "IPv6"
                print(f"    {family_name}: {addr}")
    except socket.gaierror as e:
        print(f"    Failed: {e}")
    print()

    # Step 3: Reverse DNS lookup
    print("[3] Reverse DNS (IP -> Hostname)")
    print("-" * 40)
    try:
        hostname, _, _ = socket.gethostbyaddr(ip)
        print(f"    {ip} -> {hostname}")
    except (socket.herror, socket.gaierror):
        print(f"    {ip} -> (no reverse DNS record)")
    print()

    # Step 4: Measure multiple lookups to show caching
    print("[4] DNS Caching Effect (5 consecutive lookups)")
    print("-" * 40)
    times = []
    for i in range(5):
        start = time.time()
        socket.gethostbyname(domain)
        elapsed = (time.time() - start) * 1000
        times.append(elapsed)
        bar = "*" * max(1, int(elapsed * 10))
        print(f"    Lookup {i+1}: {elapsed:>6.2f}ms  {bar}")

    print()
    print(f"    First lookup:   {times[0]:.2f}ms (may involve full resolution)")
    print(f"    Average cached: {sum(times[1:])/len(times[1:]):.2f}ms")
    print()

    # Summary
    print("=" * 60)
    print("HOW DNS WORKS:")
    print("  1. Browser checks local cache")
    print("  2. OS checks its DNS cache")
    print("  3. Query goes to recursive resolver (ISP or 8.8.8.8)")
    print("  4. Resolver asks: Root -> TLD (.com) -> Authoritative server")
    print("  5. Answer cached at every level (based on TTL)")
    print()
    print("IN SYSTEM DESIGN:")
    print("  - DNS enables load balancing (multiple A records)")
    print("  - GeoDNS routes users to the nearest datacenter")
    print("  - Short TTLs (30-60s) enable fast failover")
    print("  - Long TTLs (3600s) reduce lookup latency")
    print("=" * 60)


def main():
    if len(sys.argv) < 2:
        domain = "google.com"
        print(f"No domain specified. Using default: {domain}")
        print(f"Usage: python dns_lookup.py <domain>")
    else:
        domain = sys.argv[1]

    resolve_dns(domain)


if __name__ == "__main__":
    main()
