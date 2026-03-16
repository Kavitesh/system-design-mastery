"""
Lambda Simulator - FaaS Execution Environment
===============================================
Simulates how serverless platforms manage function containers,
including cold starts, warm starts, timeouts, and memory limits.

Usage:
    python lambda_simulator.py
"""

import time
import random
import threading
import sys

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CONTAINER_IDLE_TIMEOUT = 3.0    # seconds before container is recycled
FUNCTION_TIMEOUT = 2.0          # max execution time per invocation
MEMORY_LIMIT_MB = 128           # memory cap per function
COLD_START_BASE_MS = 200        # base cold start latency

# ---------------------------------------------------------------------------
# Simulated Function Container
# ---------------------------------------------------------------------------

class FunctionContainer:
    def __init__(self, function_name, runtime="python3.11"):
        self.function_name = function_name
        self.runtime = runtime
        self.container_id = f"ctr-{random.randint(10000, 99999)}"
        self.created_at = time.time()
        self.last_invoked = time.time()
        self.invocation_count = 0
        self.is_warm = False
        self.memory_used_mb = 0
        self._globals = {}

    def cold_start(self):
        lang_overhead = {
            "python3.11": random.uniform(150, 400),
            "nodejs18": random.uniform(100, 350),
            "java17": random.uniform(800, 3000),
            "go1.21": random.uniform(50, 150),
        }
        delay_ms = lang_overhead.get(self.runtime, COLD_START_BASE_MS)
        delay_ms += random.uniform(20, 80)  # network jitter
        time.sleep(delay_ms / 1000)
        self.is_warm = True
        return delay_ms

    def invoke(self, handler, event, context):
        self.last_invoked = time.time()
        self.invocation_count += 1
        result = {"output": None, "error": None, "timed_out": False}

        def _run():
            try:
                result["output"] = handler(event, context, self._globals)
            except MemoryError:
                result["error"] = "Function exceeded memory limit"
            except Exception as e:
                result["error"] = str(e)

        thread = threading.Thread(target=_run)
        thread.start()
        thread.join(timeout=FUNCTION_TIMEOUT)

        if thread.is_alive():
            result["timed_out"] = True
            result["error"] = f"Task timed out after {FUNCTION_TIMEOUT}s"

        return result

    @property
    def idle_seconds(self):
        return time.time() - self.last_invoked

    @property
    def is_expired(self):
        return self.idle_seconds > CONTAINER_IDLE_TIMEOUT


# ---------------------------------------------------------------------------
# Lambda Runtime Simulator
# ---------------------------------------------------------------------------

class LambdaRuntime:
    def __init__(self):
        self.containers = {}
        self.total_invocations = 0
        self.cold_starts = 0
        self.warm_starts = 0
        self.timeouts = 0
        self.errors = 0

    def invoke(self, function_name, handler, event, runtime="python3.11"):
        self.total_invocations += 1
        start = time.time()

        container = self.containers.get(function_name)
        cold_start_ms = 0

        if container is None or container.is_expired:
            container = FunctionContainer(function_name, runtime)
            self.containers[function_name] = container
            cold_start_ms = container.cold_start()
            self.cold_starts += 1
            start_type = "COLD"
        else:
            self.warm_starts += 1
            start_type = "WARM"

        context = {
            "function_name": function_name,
            "memory_limit_mb": MEMORY_LIMIT_MB,
            "timeout": FUNCTION_TIMEOUT,
            "request_id": f"req-{random.randint(100000, 999999)}",
            "container_id": container.container_id,
        }

        result = container.invoke(handler, event, context)
        elapsed_ms = (time.time() - start) * 1000

        if result["timed_out"]:
            self.timeouts += 1
        if result["error"]:
            self.errors += 1

        billed_ms = max(1, round(elapsed_ms))
        cost = (billed_ms / 1000) * (MEMORY_LIMIT_MB / 1024) * 0.0000166667 + 0.0000002

        print(f"  [{start_type:4}] {function_name:<25} "
              f"| {elapsed_ms:7.1f}ms "
              f"| cold_start={cold_start_ms:5.1f}ms "
              f"| container={container.container_id} "
              f"| cost=${cost:.8f}")

        if result["error"]:
            print(f"         ERROR: {result['error']}")

        return result

    def print_stats(self):
        total = self.total_invocations or 1
        print(f"\n{'='*70}")
        print(f"  Runtime Statistics")
        print(f"{'='*70}")
        print(f"  Total invocations:  {self.total_invocations}")
        print(f"  Cold starts:        {self.cold_starts} ({100*self.cold_starts/total:.1f}%)")
        print(f"  Warm starts:        {self.warm_starts} ({100*self.warm_starts/total:.1f}%)")
        print(f"  Timeouts:           {self.timeouts}")
        print(f"  Errors:             {self.errors}")
        print(f"  Active containers:  {len(self.containers)}")
        print(f"{'='*70}")


# ---------------------------------------------------------------------------
# Sample Functions
# ---------------------------------------------------------------------------

def hello_handler(event, context, state):
    name = event.get("name", "World")
    return f"Hello, {name}! (request: {context['request_id']})"

def slow_handler(event, context, state):
    delay = event.get("delay", 3.0)
    time.sleep(delay)
    return f"Finished after {delay}s"

def stateful_handler(event, context, state):
    state.setdefault("call_count", 0)
    state["call_count"] += 1
    return f"This container has handled {state['call_count']} requests"

def error_handler(event, context, state):
    if random.random() < 0.5:
        raise ValueError("Random failure - downstream service unavailable")
    return "Success (got lucky)"


# ---------------------------------------------------------------------------
# Main Demo
# ---------------------------------------------------------------------------

def main():
    print("Lambda Simulator - FaaS Execution Environment")
    runtime = LambdaRuntime()

    print("\n--- Scenario 1: Cold start vs warm start ---")
    runtime.invoke("greeting", hello_handler, {"name": "Alice"})
    runtime.invoke("greeting", hello_handler, {"name": "Bob"})
    runtime.invoke("greeting", hello_handler, {"name": "Charlie"})

    print("\n--- Scenario 2: Different runtimes, different cold starts ---")
    for rt in ["python3.11", "nodejs18", "java17", "go1.21"]:
        runtime.invoke(f"hello-{rt}", hello_handler, {"name": "Test"}, runtime=rt)

    print("\n--- Scenario 3: Timeout enforcement ---")
    runtime.invoke("quick-task", slow_handler, {"delay": 0.5})
    runtime.invoke("slow-task", slow_handler, {"delay": 5.0})

    print("\n--- Scenario 4: Container state reuse (warm) ---")
    runtime.invoke("counter", stateful_handler, {})
    runtime.invoke("counter", stateful_handler, {})
    runtime.invoke("counter", stateful_handler, {})

    print("\n--- Scenario 5: Error handling ---")
    for i in range(4):
        runtime.invoke("flaky-service", error_handler, {})

    print("\n--- Scenario 6: Container expiry ---")
    runtime.invoke("ephemeral", hello_handler, {"name": "First"})
    print(f"  Waiting {CONTAINER_IDLE_TIMEOUT + 0.5}s for container to expire...")
    time.sleep(CONTAINER_IDLE_TIMEOUT + 0.5)
    runtime.invoke("ephemeral", hello_handler, {"name": "Second"})

    runtime.print_stats()


if __name__ == "__main__":
    main()
