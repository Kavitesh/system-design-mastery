"""
Resilience Demo - Flask App
===========================
Combines circuit breaker, retry with backoff, and bulkhead patterns
into a single Flask application simulating an order service.
"""

import time, random, threading
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from flask import Flask, jsonify

app = Flask(__name__)

# ---------------------------------------------------------------------------
#  Circuit Breaker (compact version)
# ---------------------------------------------------------------------------

class CBState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

class CircuitBreaker:
    def __init__(self, name, threshold=3, reset_timeout=10):
        self.name, self.threshold, self.reset_timeout = name, threshold, reset_timeout
        self.state, self.failures, self.last_fail = CBState.CLOSED, 0, None
        self.lock = threading.Lock()

    def call(self, func, *args):
        with self.lock:
            if self.state == CBState.OPEN:
                if time.time() - self.last_fail >= self.reset_timeout:
                    self.state = CBState.HALF_OPEN
                else:
                    raise CircuitOpenError(f"{self.name} circuit open")
        try:
            result = func(*args)
        except Exception:
            with self.lock:
                self.failures += 1
                if self.state == CBState.HALF_OPEN or self.failures >= self.threshold:
                    print(f"  [breaker:{self.name}] {self.state.value} -> OPEN")
                    self.state, self.last_fail, self.failures = CBState.OPEN, time.time(), 0
            raise
        else:
            with self.lock:
                self.state, self.failures = CBState.CLOSED, 0
            return result

    @property
    def status(self):
        return self.state.value

class CircuitOpenError(Exception):
    pass

# ---------------------------------------------------------------------------
#  Retry with Jitter
# ---------------------------------------------------------------------------

def retry_with_backoff(func, max_attempts=3, base_delay=0.3):
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            return func()
        except CircuitOpenError:
            raise
        except Exception as e:
            last_error = e
            if attempt < max_attempts:
                delay = random.uniform(0, base_delay * (2 ** (attempt - 1)))
                time.sleep(delay)
    raise last_error

# ---------------------------------------------------------------------------
#  Bulkhead
# ---------------------------------------------------------------------------

class Bulkhead:
    def __init__(self, name, size=3):
        self.name = name
        self.semaphore = threading.Semaphore(size)
        self.pool = ThreadPoolExecutor(max_workers=size, thread_name_prefix=name)

    def submit(self, func, *args, timeout=5.0):
        if not self.semaphore.acquire(blocking=False):
            raise BulkheadFullError(f"{self.name} pool full")
        try:
            future = self.pool.submit(func, *args)
            return future.result(timeout=timeout)
        finally:
            self.semaphore.release()

class BulkheadFullError(Exception):
    pass


# ---------------------------------------------------------------------------
#  Simulated Downstream Services
# ---------------------------------------------------------------------------

payment_failure_rate = 0.6

def payment_service(order_id):
    time.sleep(random.uniform(0.1, 0.3))
    if random.random() < payment_failure_rate:
        raise ConnectionError("Payment gateway timeout")
    return {"status": "charged", "order_id": order_id}

def inventory_service(order_id):
    time.sleep(random.uniform(0.05, 0.15))
    return {"status": "reserved", "order_id": order_id, "warehouse": "US-EAST-1"}


# ---------------------------------------------------------------------------
#  Resilience Wiring
# ---------------------------------------------------------------------------

payment_breaker = CircuitBreaker("payment", threshold=3, reset_timeout=15)
payment_bulkhead = Bulkhead("payment", size=3)
inventory_bulkhead = Bulkhead("inventory", size=5)

def call_payment(order_id):
    return retry_with_backoff(
        lambda: payment_breaker.call(payment_service, order_id), max_attempts=2
    )

# ---------------------------------------------------------------------------
#  Flask Routes
# ---------------------------------------------------------------------------

@app.route("/order")
def place_order():
    order_id = f"ORD-{random.randint(1000, 9999)}"
    try:
        inventory = inventory_bulkhead.submit(inventory_service, order_id)
    except (BulkheadFullError, FuturesTimeout):
        return jsonify({"error": "Inventory unavailable", "order_id": order_id}), 503
    try:
        payment = payment_bulkhead.submit(lambda: call_payment(order_id))
    except Exception:
        payment = {"status": "queued", "order_id": order_id, "note": "Payment queued for retry"}
    return jsonify({"order_id": order_id, "inventory": inventory, "payment": payment})


@app.route("/status")
def system_status():
    return jsonify({"payment_circuit": payment_breaker.status})

@app.route("/config")
def get_config():
    return jsonify({"failure_rate": payment_failure_rate, "threshold": payment_breaker.threshold})

# ---------------------------------------------------------------------------
#  Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Resilience Demo - GET /order, /status, /config - http://localhost:5000")
    app.run(port=5000, debug=False)
