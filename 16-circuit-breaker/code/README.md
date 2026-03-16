# Chapter 16 Code Lab - Circuit Breaker & Retry Patterns

Hands-on Python demos for resilience patterns that prevent cascading failures.

## Files

| File | What It Demonstrates | Key Concepts |
|------|---------------------|--------------|
| `circuit_breaker.py` | Full circuit breaker with state machine | Closed/open/half-open states, failure threshold, reset timeout |
| `retry_patterns.py` | Three retry strategies compared | Simple retry, exponential backoff, backoff with jitter |
| `bulkhead.py` | Thread pool isolation | Separate pools per dependency, failure containment |
| `resilience_demo.py` | Flask app combining all patterns | Circuit breaker + retry + bulkhead working together |

## Requirements

```bash
pip install flask requests
```

No external resilience libraries needed - we build everything from scratch to understand how it works.

## Running the Labs

Each file runs standalone:

```bash
python circuit_breaker.py    # Watch breaker trip and recover
python retry_patterns.py     # Compare retry strategies
python bulkhead.py           # See failure isolation in action
python resilience_demo.py    # Flask app on http://localhost:5000
```

## What to Watch For

- **circuit_breaker.py** - Notice how the breaker transitions through all three states. Failures accumulate, the breaker trips, waits, then tests with a single request.
- **retry_patterns.py** - Compare the timing of simple retry vs. exponential backoff vs. jitter. Watch how jitter spreads out the retry attempts.
- **bulkhead.py** - One service is deliberately slow. Watch how it exhausts its own pool but the other services keep working.
- **resilience_demo.py** - Hit the `/order` endpoint while the payment service is flaky. Watch the circuit breaker trip and the fallback kick in.
