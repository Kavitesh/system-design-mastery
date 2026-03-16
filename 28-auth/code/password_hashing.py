"""
Password Hashing - Right vs Wrong
==================================
Compares plaintext, MD5, SHA-256, and bcrypt password storage.
Shows why intentionally slow hashing matters.

Run: python password_hashing.py
Requires: pip install bcrypt
"""

import hashlib
import secrets
import time

try:
    import bcrypt
    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False
    print("NOTE: pip install bcrypt for full demo\n")

# ---------------------------------------------------------------------------
# Hashing methods
# ---------------------------------------------------------------------------

def hash_md5(pw):
    return hashlib.md5(pw.encode()).hexdigest()

def hash_sha256(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def hash_bcrypt(pw, rounds=12):
    if not HAS_BCRYPT:
        return "(bcrypt not installed)"
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt(rounds=rounds)).decode()

def verify_bcrypt(pw, hashed):
    if not HAS_BCRYPT:
        return False
    return bcrypt.checkpw(pw.encode(), hashed.encode())

# ---------------------------------------------------------------------------
# Brute force simulation
# ---------------------------------------------------------------------------

COMMON = ["123456", "password", "password123", "qwerty", "letmein",
          "admin", "welcome", "monkey", "dragon", "master",
          "football", "shadow", "sunshine", "trustno1", "iloveyou"]

def brute_md5(target_hash):
    t = time.perf_counter()
    for guess in COMMON:
        if hashlib.md5(guess.encode()).hexdigest() == target_hash:
            return guess, time.perf_counter() - t
    return None, time.perf_counter() - t

def brute_bcrypt(target_hash):
    if not HAS_BCRYPT:
        return None, 0.0
    t = time.perf_counter()
    for guess in COMMON:
        if bcrypt.checkpw(guess.encode(), target_hash.encode()):
            return guess, time.perf_counter() - t
    return None, time.perf_counter() - t

# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def main():
    pw = "password123"
    print("=" * 60)
    print("PASSWORD HASHING - RIGHT VS WRONG")
    print("=" * 60)

    print(f"\nPassword: '{pw}'\n")
    print(f"  Plaintext:  {pw}")
    print(f"  MD5:        {hash_md5(pw)}")
    print(f"  SHA-256:    {hash_sha256(pw)}")
    bh = hash_bcrypt(pw)
    print(f"  bcrypt:     {bh}")

    print("\n--- Determinism ---\n")
    print("  MD5 (same every time):")
    for i in range(3):
        print(f"    {hash_md5(pw)}")
    if HAS_BCRYPT:
        print("  bcrypt (different every time - salt is embedded):")
        for i in range(3):
            print(f"    {hash_bcrypt(pw, rounds=4)}")

    print("\n--- Speed Comparison ---\n")
    n = 1000
    t = time.perf_counter()
    for _ in range(n):
        hash_md5(pw)
    md5_t = time.perf_counter() - t

    t = time.perf_counter()
    for _ in range(n):
        hash_sha256(pw)
    sha_t = time.perf_counter() - t

    print(f"  MD5    x{n}: {md5_t*1000:.1f}ms  ({n/md5_t:,.0f} hashes/sec)")
    print(f"  SHA256 x{n}: {sha_t*1000:.1f}ms  ({n/sha_t:,.0f} hashes/sec)")

    if HAS_BCRYPT:
        bn = 3
        t = time.perf_counter()
        for _ in range(bn):
            hash_bcrypt(pw, rounds=12)
        bc_t = time.perf_counter() - t
        print(f"  bcrypt x{bn}:  {bc_t*1000:.0f}ms  ({bn/bc_t:.1f} hashes/sec)")
        ratio = int((bc_t / bn) / (md5_t / n))
        print(f"\n  bcrypt is ~{ratio}x slower than MD5. That's the point.")

    print("\n--- Brute Force Attack ---\n")
    print(f"  Wordlist: {len(COMMON)} common passwords")
    found, elapsed = brute_md5(hash_md5(pw))
    print(f"  MD5:    cracked '{found}' in {elapsed*1000:.3f}ms")

    if HAS_BCRYPT:
        found, elapsed = brute_bcrypt(hash_bcrypt(pw, rounds=12))
        print(f"  bcrypt: cracked '{found}' in {elapsed*1000:.0f}ms")
        print(f"  Same result, but scale to millions of guesses and it's years vs seconds.")

    if HAS_BCRYPT:
        print("\n--- Verification ---\n")
        stored = hash_bcrypt("secure-pass")
        print(f"  Stored:  {stored}")
        print(f"  Correct: {verify_bcrypt('secure-pass', stored)}")
        print(f"  Wrong:   {verify_bcrypt('wrong-pass', stored)}")

    print("\n--- Summary ---\n")
    print(f"  {'Method':<15} {'Salted':<10} {'Slow':<8} {'Use It?'}")
    print(f"  {'-'*48}")
    print(f"  {'Plaintext':<15} {'No':<10} {'N/A':<8} NEVER")
    print(f"  {'MD5':<15} {'No':<10} {'No':<8} NEVER")
    print(f"  {'SHA-256':<15} {'No':<10} {'No':<8} No")
    print(f"  {'bcrypt':<15} {'Built-in':<10} {'Yes':<8} Yes")
    print(f"  {'Argon2':<15} {'Built-in':<10} {'Yes':<8} Best")

    print("\n" + "=" * 60)
    print("Rule: if your password hash is fast, it's wrong.")
    print("=" * 60)

if __name__ == "__main__":
    main()
