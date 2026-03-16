"""
Hashing Demo
==============
SHA-256, HMAC, and bcrypt comparison - different tools for different jobs.
Shows when to use each and why using SHA-256 for passwords will get you breached.

Usage: python hashing_demo.py
Optional: pip install bcrypt (for real bcrypt demo)
"""

import hashlib
import hmac
import os
import time
import struct

# ---------------------------------------------------------------------------
# Check for optional bcrypt library
# ---------------------------------------------------------------------------

try:
    import bcrypt
    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False


# ---------------------------------------------------------------------------
# SHA-256 basics
# ---------------------------------------------------------------------------

def demo_sha256():
    """Demonstrate SHA-256 properties."""
    print("\n=== SHA-256 - Cryptographic Hash Function ===")
    print("Fixed output, one-way, deterministic, avalanche effect.\n")

    test_cases = [
        "hello",
        "hello.",
        "hello!",
        "The quick brown fox jumps over the lazy dog",
        "The quick brown fox jumps over the lazy dog.",
    ]

    for text in test_cases:
        digest = hashlib.sha256(text.encode()).hexdigest()
        print(f"  SHA-256(\"{text[:45]}\")")
        print(f"    = {digest}")
        print()

    print("  Notice: one character difference completely changes the hash.")
    print("  This is the avalanche effect - no way to predict the change.\n")

    h1 = hashlib.sha256(b"hello").hexdigest()
    h2 = hashlib.sha256(b"hello").hexdigest()
    print(f"  Same input always produces same output:")
    print(f"    SHA-256('hello') = {h1[:32]}...")
    print(f"    SHA-256('hello') = {h2[:32]}...")
    print(f"    Match: {h1 == h2}")

    sizes = [10, 100, 1000, 1_000_000]
    print(f"\n  Output is always 256 bits (64 hex chars) regardless of input size:")
    for size in sizes:
        data = os.urandom(size)
        digest = hashlib.sha256(data).hexdigest()
        print(f"    {size:>10} bytes input -> {len(digest)} hex chars: {digest[:24]}...")


# ---------------------------------------------------------------------------
# HMAC
# ---------------------------------------------------------------------------

def demo_hmac():
    """Demonstrate HMAC - hash with a secret key."""
    print("\n=== HMAC - Hash-Based Message Authentication Code ===")
    print("Proves integrity AND authenticity. Requires a shared secret key.\n")

    secret_key = b"webhook-signing-secret-2024"
    payload = b'{"event":"payment.success","amount":99.99}'

    signature = hmac.new(secret_key, payload, hashlib.sha256).hexdigest()
    print(f"  Secret key: {secret_key.decode()}")
    print(f"  Payload:    {payload.decode()}")
    print(f"  HMAC-SHA256: {signature}")

    print(f"\n  --- Verification (server receives payload + signature) ---")
    received_sig = signature
    expected_sig = hmac.new(secret_key, payload, hashlib.sha256).hexdigest()
    valid = hmac.compare_digest(received_sig, expected_sig)
    print(f"  Received signature:  {received_sig[:32]}...")
    print(f"  Computed signature:  {expected_sig[:32]}...")
    print(f"  Valid: {valid}")

    print(f"\n  --- Tampered payload ---")
    tampered = b'{"event":"payment.success","amount":999.99}'
    tampered_sig = hmac.new(secret_key, tampered, hashlib.sha256).hexdigest()
    valid = hmac.compare_digest(received_sig, tampered_sig)
    print(f"  Original amount: 99.99")
    print(f"  Tampered amount: 999.99")
    print(f"  Signature still valid: {valid}")
    print(f"  Attacker can't forge HMAC without the secret key.")

    print(f"\n  --- Why not plain SHA-256? ---")
    plain_hash = hashlib.sha256(payload).hexdigest()
    print(f"  SHA-256(payload): {plain_hash[:32]}...")
    print(f"  Anyone can compute this - no secret required.")
    print(f"  An attacker could modify the payload AND recompute the hash.")
    print(f"  HMAC prevents this because the attacker doesn't have the key.")

    print(f"\n  Real-world HMAC usage:")
    print(f"    - Stripe webhook signatures")
    print(f"    - GitHub webhook verification")
    print(f"    - AWS Signature V4 (API request signing)")
    print(f"    - JWT HS256 signatures")


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

def sim_bcrypt(password: str, rounds: int = 12) -> tuple[str, float]:
    """Simulates bcrypt's cost by running SHA-256 2^rounds times."""
    start = time.perf_counter()
    salt = os.urandom(16)
    digest = hashlib.sha256(salt + password.encode()).digest()
    iterations = 2 ** rounds
    for _ in range(iterations):
        digest = hashlib.sha256(digest).digest()
    elapsed = time.perf_counter() - start
    result = f"$sim_bcrypt${rounds}${salt.hex()[:22]}${digest.hex()[:31]}"
    return result, elapsed


def demo_password_hashing():
    """Show why SHA-256 is wrong for passwords and bcrypt is right."""
    print("\n=== PASSWORD HASHING - SHA-256 vs bcrypt ===")
    print("Fast hashes are great for files. Terrible for passwords.\n")

    password = "correct-horse-battery-staple"

    print(f"  Password: {password}\n")

    # SHA-256 speed
    iterations = 100_000
    start = time.perf_counter()
    for _ in range(iterations):
        hashlib.sha256(password.encode()).digest()
    sha_time = time.perf_counter() - start
    sha_per_sec = iterations / sha_time

    print(f"  SHA-256:")
    sha_hash = hashlib.sha256(password.encode()).hexdigest()
    print(f"    Hash: {sha_hash[:48]}...")
    print(f"    Speed: {sha_per_sec:,.0f} hashes/sec on this machine")
    print(f"    GPU (RTX 4090): ~10,000,000,000 hashes/sec")
    print(f"    Time to try all 8-char passwords: ~2 hours on one GPU")

    # bcrypt
    if HAS_BCRYPT:
        print(f"\n  bcrypt (real, cost factor 12):")
        start = time.perf_counter()
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12))
        bcrypt_time = time.perf_counter() - start
        bcrypt_per_sec = 1 / bcrypt_time

        print(f"    Hash: {hashed.decode()[:48]}...")
        print(f"    Speed: {bcrypt_per_sec:,.1f} hashes/sec on this machine")
        print(f"    GPU: ~30,000 hashes/sec (bcrypt resists GPU parallelism)")
        print(f"    Time to try all 8-char passwords: ~800 years on one GPU")

        print(f"\n  --- Verification ---")
        start = time.perf_counter()
        valid = bcrypt.checkpw(password.encode(), hashed)
        verify_time = (time.perf_counter() - start) * 1000
        print(f"    Password matches: {valid} (took {verify_time:.0f}ms)")

        wrong_valid = bcrypt.checkpw(b"wrong-password", hashed)
        print(f"    Wrong password:   {wrong_valid}")
    else:
        print(f"\n  bcrypt (simulated, cost factor 12):")
        hashed, bcrypt_time = sim_bcrypt(password, rounds=12)
        bcrypt_per_sec = 1 / bcrypt_time if bcrypt_time > 0 else 0

        print(f"    Hash: {hashed[:48]}...")
        print(f"    Speed: {bcrypt_per_sec:,.1f} hashes/sec (simulated)")
        print(f"    Real bcrypt on GPU: ~30,000 hashes/sec")
        print(f"    Install 'bcrypt' package for real demo: pip install bcrypt")

    print(f"\n  --- The math that matters ---")
    print(f"    SHA-256:  10 billion/sec on GPU = passwords cracked in hours")
    print(f"    bcrypt:   30 thousand/sec on GPU = passwords cracked in centuries")
    print(f"    The speed difference IS the security.")

    print(f"\n  --- Choosing a password hash ---")
    print(f"    bcrypt:   Battle-tested since 1999. Safe default.")
    print(f"    scrypt:   Memory-hard. Good against GPU/ASIC attacks.")
    print(f"    Argon2id: Won PHC (2015). Memory-hard + time-hard. Best choice for new systems.")
    print(f"    MD5/SHA:  NEVER for passwords. Not even with salt.")


# ---------------------------------------------------------------------------
# Hash comparison table
# ---------------------------------------------------------------------------

def demo_comparison():
    """Side-by-side comparison of hashing approaches."""
    print("\n=== WHEN TO USE WHAT ===\n")

    rows = [
        ("File integrity check", "SHA-256", "Verify downloads, detect corruption"),
        ("Git commits", "SHA-1 (moving to SHA-256)", "Content-addressable storage"),
        ("Password storage", "bcrypt / Argon2id", "Intentionally slow, salted"),
        ("API authentication", "HMAC-SHA256", "Proves sender has the secret key"),
        ("Data deduplication", "SHA-256 / xxHash", "Find identical content fast"),
        ("Webhook verification", "HMAC-SHA256", "Verify payload came from trusted source"),
        ("Digital signatures", "SHA-256 + RSA/ECDSA", "Non-repudiation, certificate signing"),
        ("Bloom filters", "MurmurHash / xxHash", "Speed matters more than crypto strength"),
    ]

    print(f"  {'Use Case':<26} {'Algorithm':<26} {'Why'}")
    print(f"  {'-'*26} {'-'*26} {'-'*40}")
    for use_case, algo, why in rows:
        print(f"  {use_case:<26} {algo:<26} {why}")


# ---------------------------------------------------------------------------
# Salt demonstration
# ---------------------------------------------------------------------------

def demo_salt():
    """Show why salting matters for password hashing."""
    print("\n=== WHY SALT MATTERS ===\n")

    password = "password123"

    unsalted = hashlib.sha256(password.encode()).hexdigest()
    print(f"  Without salt:")
    print(f"    User A: SHA-256('password123') = {unsalted[:32]}...")
    print(f"    User B: SHA-256('password123') = {unsalted[:32]}...")
    print(f"    Identical hashes - attacker knows both users have the same password.")
    print(f"    One rainbow table cracks all identical passwords at once.\n")

    salt_a = os.urandom(16)
    salt_b = os.urandom(16)
    salted_a = hashlib.sha256(salt_a + password.encode()).hexdigest()
    salted_b = hashlib.sha256(salt_b + password.encode()).hexdigest()
    print(f"  With salt (unique per user):")
    print(f"    User A salt: {salt_a.hex()[:16]}...")
    print(f"    User A hash: {salted_a[:32]}...")
    print(f"    User B salt: {salt_b.hex()[:16]}...")
    print(f"    User B hash: {salted_b[:32]}...")
    print(f"    Different hashes even for the same password.")
    print(f"    Rainbow tables are useless - each password must be cracked individually.")
    print(f"\n    bcrypt and Argon2id include salts automatically. Don't roll your own.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Hashing Demo Lab")
    print(f"  bcrypt library: {'installed' if HAS_BCRYPT else 'not found (using simulation)'}")

    demo_sha256()
    demo_hmac()
    demo_password_hashing()
    demo_salt()
    demo_comparison()
