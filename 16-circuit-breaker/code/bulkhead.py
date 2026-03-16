"""
Bulkhead Pattern - Thread Pool Isolation
=========================================
Separate thread pools per downstream service prevent one slow
dependency from consuming all resources and starving others.
"""

import time
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

# ---------------------------------------------------------------------------
#  Bulkhead Implementation
# ---------------------------------------------------------------------------

class Bulkhead:
    """Thread pool isolation for a single downstream dependency."""

    def __init__(self, name, max_concurrent, queue_size=5):
        self.name = name
        self.max_concurrent = max_concurrent
        self.pool = ThreadPoolExecutor(
            max_workers=max_concurrent,
            thread_name_prefix=name
        )
        self.semaphore = threading.Semaphore(max_concurrent + queue_size)
        self.active = 0
        self.rejected = 0
        self.lock = threading.Lock()

    def submit(self, func, *args, timeout=5.0):
        acquired = self.semaphore.acquire(blocking=False)
        if not acquired:
            with self.lock:
                self.rejected += 1
            raise BulkheadFullError(
                f"[{self.name}] Pool exhausted ({self.max_concurrent} threads busy, "
                f"{self.rejected} rejected total)"
            )

        with self.lock:
            self.active += 1

        try:
            future = self.pool.submit(func, *args)
            return future.result(timeout=timeout)
        except FuturesTimeout:
            raise TimeoutError(f"[{self.name}] Call timed out after {timeout}s")
        finally:
            with self.lock:
                self.active -= 1
            self.semaphore.release()

    def stats(self):
        with self.lock:
            return {"name": self.name, "active": self.active, "rejected": self.rejected}

    def shutdown(self):
        self.pool.shutdown(wait=False)


class BulkheadFullError(Exception):
    pass


# ---------------------------------------------------------------------------
#  Simulated Services
# ---------------------------------------------------------------------------

def payment_service(request_id):
    time.sleep(3.0)
    return f"Payment {request_id} processed"


def inventory_service(request_id):
    time.sleep(0.1)
    return f"Inventory {request_id} checked"


def email_service(request_id):
    time.sleep(0.1)
    return f"Email {request_id} sent"


# ---------------------------------------------------------------------------
#  Demo
# ---------------------------------------------------------------------------

def main():
    print("Bulkhead Pattern Demo")
    print("=" * 50)

    payment_pool = Bulkhead("payment", max_concurrent=2, queue_size=1)
    inventory_pool = Bulkhead("inventory", max_concurrent=3, queue_size=2)
    email_pool = Bulkhead("email", max_concurrent=2, queue_size=1)

    print("\nSetup:")
    print("  Payment service:   SLOW (3s per call), pool size 2")
    print("  Inventory service: FAST (0.1s per call), pool size 3")
    print("  Email service:     FAST (0.1s per call), pool size 2")
    print("\nSending 5 requests to each service simultaneously...\n")

    counters = {"success": 0, "rejected": 0, "timeout": 0}
    counter_lock = threading.Lock()

    def call_service(pool, service_func, request_id, service_name):
        try:
            result = pool.submit(service_func, request_id, timeout=4.0)
            with counter_lock:
                counters["success"] += 1
            print(f"  OK   {service_name}-{request_id}: {result}")
        except BulkheadFullError:
            with counter_lock:
                counters["rejected"] += 1
            print(f"  FULL {service_name}-{request_id}: Pool exhausted")
        except TimeoutError:
            with counter_lock:
                counters["timeout"] += 1
            print(f"  TIME {service_name}-{request_id}: Timed out")

    threads = []
    services = [
        (payment_pool, payment_service, "payment"),
        (inventory_pool, inventory_service, "inventory"),
        (email_pool, email_service, "email"),
    ]
    for pool, func, name in services:
        for i in range(1, 6):
            threads.append(threading.Thread(target=call_service, args=(pool, func, i, name)))

    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    print(f"\nResults: {counters['success']} ok, {counters['rejected']} rejected, {counters['timeout']} timeout")
    print("\nPool Stats:")
    for pool in [payment_pool, inventory_pool, email_pool]:
        s = pool.stats()
        print(f"  {s['name']:12s} - rejected: {s['rejected']}")
    print("\nPayment is slow and its pool fills up, but inventory and email keep working.")
    for pool in [payment_pool, inventory_pool, email_pool]:
        pool.shutdown()


if __name__ == "__main__":
    main()
