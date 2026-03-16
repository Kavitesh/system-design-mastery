"""
Encoding Comparison
===================
Compares three approaches for generating short URL codes: base62 counter
encoding, MD5 hash truncation, and UUID truncation. Measures collision
rates, generation speed, and code characteristics across 100K URLs.

Run: python encoding_comparison.py
"""

import hashlib
import string
import time
import uuid

ALPHABET = string.digits + string.ascii_letters
NUM_URLS = 100_000
CODE_LENGTH = 7


# ---------------------------------------------------------------------------
# Approach 1: Counter + Base62
# ---------------------------------------------------------------------------

def base62_encode(num: int) -> str:
    if num == 0:
        return ALPHABET[0]
    chars = []
    while num > 0:
        chars.append(ALPHABET[num % 62])
        num //= 62
    return "".join(reversed(chars))


def generate_base62_codes(n: int) -> list[str]:
    return [base62_encode(i + 100_000) for i in range(n)]


# ---------------------------------------------------------------------------
# Approach 2: MD5 hash + truncation
# ---------------------------------------------------------------------------

def md5_short_code(url: str, seed: int = 0) -> str:
    data = f"{url}{seed}" if seed else url
    num = int(hashlib.md5(data.encode()).hexdigest()[:12], 16)
    return base62_encode(num)[:CODE_LENGTH]


def generate_md5_codes(urls: list[str]) -> tuple[list[str], int]:
    codes, collisions = {}, 0
    for url in urls:
        seed, code = 0, md5_short_code(url)
        while code in codes:
            collisions += 1
            seed += 1
            code = md5_short_code(url, seed)
        codes[code] = url
    return list(codes.keys()), collisions


# ---------------------------------------------------------------------------
# Approach 3: UUID truncation
# ---------------------------------------------------------------------------

def uuid_short_code() -> str:
    num = int(uuid.uuid4().hex[:12], 16)
    return base62_encode(num)[:CODE_LENGTH]


def generate_uuid_codes(n: int) -> tuple[list[str], int]:
    codes, collisions = set(), 0
    while len(codes) < n:
        code = uuid_short_code()
        if code in codes:
            collisions += 1
        else:
            codes.add(code)
    return list(codes), collisions


# ---------------------------------------------------------------------------
# Run the comparison
# ---------------------------------------------------------------------------

def format_duration(seconds: float) -> str:
    if seconds < 0.001:
        return f"{seconds * 1_000_000:.0f} us"
    return f"{seconds * 1_000:.1f} ms" if seconds < 1 else f"{seconds:.2f} s"


def main():
    print(f"Generating {NUM_URLS:,} short codes with each approach...\n")
    test_urls = [f"https://example.com/page/{i}?ref=campaign_{i%50}" for i in range(NUM_URLS)]

    t0 = time.perf_counter()
    base62_codes = generate_base62_codes(NUM_URLS)
    t_base62 = time.perf_counter() - t0

    t0 = time.perf_counter()
    md5_codes, md5_collisions = generate_md5_codes(test_urls)
    t_md5 = time.perf_counter() - t0

    t0 = time.perf_counter()
    uuid_codes, uuid_collisions = generate_uuid_codes(NUM_URLS)
    t_uuid = time.perf_counter() - t0

    print(f"{'='*70}")
    print(f"{'Metric':<25} {'Base62 Counter':>14} {'MD5 Truncate':>14} {'UUID Truncate':>14}")
    print(f"{'-'*70}")
    print(f"{'Time':<25} {format_duration(t_base62):>14} {format_duration(t_md5):>14} {format_duration(t_uuid):>14}")
    print(f"{'Codes/sec':<25} {NUM_URLS/t_base62:>14,.0f} {NUM_URLS/t_md5:>14,.0f} {NUM_URLS/t_uuid:>14,.0f}")
    print(f"{'Collisions':<25} {0:>14,} {md5_collisions:>14,} {uuid_collisions:>14,}")
    print(f"{'Collision rate':<25} {'0%':>14} {md5_collisions/NUM_URLS*100:>13.3f}% {uuid_collisions/NUM_URLS*100:>13.3f}%")

    for name, codes in [("Base62 Counter", base62_codes), ("MD5 Truncate", md5_codes), ("UUID Truncate", uuid_codes)]:
        lengths = [len(c) for c in codes]
        unique_chars = len(set(ch for c in codes for ch in c))
        print(f"\n--- {name} ---")
        print(f"  Length: {min(lengths)}-{max(lengths)} chars | Unique chars: {unique_chars}/62")
        print(f"  Samples: {' '.join(codes[:8])}")

    print(f"\n{'='*70}")
    print("PREDICTABILITY TEST")
    print(f"{'='*70}")
    print(f"Base62 sequential: {' -> '.join(base62_codes[:5])}")
    print(f"  Pattern is obvious - users can enumerate URLs by incrementing\n")
    for i in range(3):
        url = f"https://example.com/page/{i}"
        print(f"  MD5({url}) -> {md5_short_code(url)}")
    print(f"  No discernible pattern - unpredictable")

    print(f"\n{'='*70}")
    print("DEDUPLICATION TEST")
    print(f"{'='*70}")
    test_url = "https://example.com/same-page"
    print(f"  MD5 x2:   {md5_short_code(test_url)}, {md5_short_code(test_url)}  (same - dedup for free)")
    print(f"  UUID x2:  {uuid_short_code()}, {uuid_short_code()}  (different every time)")
    print(f"  Base62:   depends on counter value, not URL content")

    print(f"""
{'='*70}
VERDICT
{'='*70}
  Counter + Base62: Simplest, zero collisions. Sequential codes are
  predictable but fixable with random offsets. Best when you control
  the counter (single DB, range allocation).

  MD5 Truncate: Deduplication and unpredictable codes, but collisions
  grow with scale. At 100M URLs, expect thousands of rehashes.

  UUID Truncate: Unpredictable and decentralized, but no dedup and
  collisions still possible. A worse version of pre-generated keys.
""")


if __name__ == "__main__":
    main()
