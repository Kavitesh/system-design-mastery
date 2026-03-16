"""
Scalability Simulation
======================
Demonstrates vertical vs horizontal scaling by simulating
request processing under load.

Run: python scalability_sim.py
"""

import time
from concurrent.futures import ThreadPoolExecutor

# ---------------------------------------------------------------------------
# Simulate processing a single request
# ---------------------------------------------------------------------------

def process_request(request_id: int, server_name: str, speed_factor: float = 1.0):
    """Simulate processing a request. speed_factor > 1 = faster hardware (vertical scaling)."""
    work_time = 0.05 / speed_factor  # base 50ms per request
    time.sleep(work_time)
    return f"[{server_name}] Request {request_id} done in {work_time*1000:.0f}ms"


# ---------------------------------------------------------------------------
# Vertical Scaling: 1 powerful server
# ---------------------------------------------------------------------------

def vertical_scaling(num_requests: int, cpu_multiplier: int):
    """
    One server with more CPU power.
    cpu_multiplier simulates upgrading hardware (2x, 4x, 8x faster).
    """
    print(f"\n{'='*60}")
    print(f"VERTICAL SCALING: 1 server with {cpu_multiplier}x CPU power")
    print(f"Processing {num_requests} requests...")
    print(f"{'='*60}")

    start = time.time()

    with ThreadPoolExecutor(max_workers=cpu_multiplier) as pool:
        futures = [
            pool.submit(process_request, i, "BigServer", cpu_multiplier)
            for i in range(num_requests)
        ]
        results = [f.result() for f in futures]

    elapsed = time.time() - start
    print(f"Completed {num_requests} requests in {elapsed:.2f}s")
    print(f"Throughput: {num_requests/elapsed:.0f} req/s")
    return elapsed


# ---------------------------------------------------------------------------
# Horizontal Scaling: N identical servers
# ---------------------------------------------------------------------------

def horizontal_scaling(num_requests: int, num_servers: int):
    """
    Multiple identical servers sharing the load.
    Requests are distributed round-robin across servers.
    """
    print(f"\n{'='*60}")
    print(f"HORIZONTAL SCALING: {num_servers} identical servers")
    print(f"Processing {num_requests} requests...")
    print(f"{'='*60}")

    start = time.time()

    # Distribute requests across servers (round-robin)
    with ThreadPoolExecutor(max_workers=num_servers) as pool:
        futures = [
            pool.submit(process_request, i, f"Server-{i % num_servers + 1}")
            for i in range(num_requests)
        ]
        results = [f.result() for f in futures]

    elapsed = time.time() - start
    print(f"Completed {num_requests} requests in {elapsed:.2f}s")
    print(f"Throughput: {num_requests/elapsed:.0f} req/s")
    return elapsed


# ---------------------------------------------------------------------------
# Run the comparison
# ---------------------------------------------------------------------------

def main():
    NUM_REQUESTS = 200

    print("╔══════════════════════════════════════════════════════════╗")
    print("║         SCALABILITY SIMULATION                          ║")
    print("║   Vertical Scaling vs Horizontal Scaling                ║")
    print("╚══════════════════════════════════════════════════════════╝")

    # Baseline: 1 server, 1x power
    t_base = vertical_scaling(NUM_REQUESTS, cpu_multiplier=1)

    # Vertical: 1 server, 4x power
    t_vert = vertical_scaling(NUM_REQUESTS, cpu_multiplier=4)

    # Horizontal: 4 servers
    t_horiz = horizontal_scaling(NUM_REQUESTS, num_servers=4)

    # Horizontal: 8 servers
    t_horiz8 = horizontal_scaling(NUM_REQUESTS, num_servers=8)

    # Summary
    print(f"\n{'='*60}")
    print("RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"{'Setup':<35} {'Time':>8} {'Speedup':>8}")
    print(f"{'-'*55}")
    print(f"{'Baseline (1 server, 1x CPU)':<35} {t_base:>7.2f}s {1.0:>7.1f}x")
    print(f"{'Vertical (1 server, 4x CPU)':<35} {t_vert:>7.2f}s {t_base/t_vert:>7.1f}x")
    print(f"{'Horizontal (4 servers)':<35} {t_horiz:>7.2f}s {t_base/t_horiz:>7.1f}x")
    print(f"{'Horizontal (8 servers)':<35} {t_horiz8:>7.2f}s {t_base/t_horiz8:>7.1f}x")
    print(f"\nNotice: Horizontal scaling gives near-linear speedup!")


if __name__ == "__main__":
    main()
