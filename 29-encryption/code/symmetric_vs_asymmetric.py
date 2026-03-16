"""
Symmetric vs Asymmetric Encryption
===================================
AES and RSA encryption demos with performance comparison.
Shows why real systems use hybrid encryption - asymmetric for key exchange,
symmetric for bulk data.

Usage: python symmetric_vs_asymmetric.py
Optional: pip install cryptography (for real AES/RSA instead of simulation)
"""

import os
import time
import hashlib
import struct

# ---------------------------------------------------------------------------
# Check for optional cryptography library
# ---------------------------------------------------------------------------

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.primitives import hashes
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


# ---------------------------------------------------------------------------
# Simulated AES (XOR-based - NOT secure, for demonstration only)
# ---------------------------------------------------------------------------

def sim_aes_encrypt(plaintext: bytes, key: bytes) -> tuple[bytes, bytes]:
    """Simulates AES encryption using repeating XOR. NOT cryptographically secure."""
    nonce = os.urandom(12)
    key_stream = hashlib.sha256(key + nonce).digest()
    extended = (key_stream * ((len(plaintext) // 32) + 1))[:len(plaintext)]
    ciphertext = bytes(a ^ b for a, b in zip(plaintext, extended))
    return nonce, ciphertext


def sim_aes_decrypt(nonce: bytes, ciphertext: bytes, key: bytes) -> bytes:
    """Simulates AES decryption. Mirror of sim_aes_encrypt."""
    key_stream = hashlib.sha256(key + nonce).digest()
    extended = (key_stream * ((len(ciphertext) // 32) + 1))[:len(ciphertext)]
    return bytes(a ^ b for a, b in zip(ciphertext, extended))


# ---------------------------------------------------------------------------
# Simulated RSA (modular exponentiation with small primes - NOT secure)
# ---------------------------------------------------------------------------

def sim_rsa_keygen() -> dict:
    """Generates a toy RSA key pair. Uses small primes - NOT for real use."""
    p, q = 7919, 7907
    n = p * q
    phi = (p - 1) * (q - 1)
    e = 65537
    d = pow(e, -1, phi)
    return {"public": (e, n), "private": (d, n)}


def sim_rsa_encrypt(plaintext: bytes, public_key: tuple) -> list[int]:
    """Encrypts bytes one chunk at a time with toy RSA."""
    e, n = public_key
    max_val = n - 1
    chunk_size = (max_val.bit_length() // 8)
    encrypted = []
    for i in range(0, len(plaintext), chunk_size):
        chunk = plaintext[i:i + chunk_size]
        m = int.from_bytes(chunk, 'big')
        if m >= n:
            m = m % n
        c = pow(m, e, n)
        encrypted.append(c)
    return encrypted


def sim_rsa_decrypt(ciphertext: list[int], private_key: tuple, chunk_size: int = 2) -> bytes:
    """Decrypts toy RSA ciphertext."""
    d, n = private_key
    decrypted = b""
    for c in ciphertext:
        m = pow(c, d, n)
        decrypted += m.to_bytes(chunk_size, 'big')
    return decrypted


# ---------------------------------------------------------------------------
# Real AES encryption (requires cryptography library)
# ---------------------------------------------------------------------------

def real_aes_encrypt(plaintext: bytes, key: bytes) -> tuple[bytes, bytes]:
    """AES-256-GCM encryption - the real deal."""
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return nonce, ciphertext


def real_aes_decrypt(nonce: bytes, ciphertext: bytes, key: bytes) -> bytes:
    """AES-256-GCM decryption with authentication."""
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)


# ---------------------------------------------------------------------------
# Real RSA encryption (requires cryptography library)
# ---------------------------------------------------------------------------

def real_rsa_keygen():
    """Generates a 2048-bit RSA key pair."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key


def real_rsa_encrypt(plaintext: bytes, public_key) -> bytes:
    """RSA-OAEP encryption."""
    return public_key.encrypt(
        plaintext,
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
    )


def real_rsa_decrypt(ciphertext: bytes, private_key) -> bytes:
    """RSA-OAEP decryption."""
    return private_key.decrypt(
        ciphertext,
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
    )


# ---------------------------------------------------------------------------
# Demos
# ---------------------------------------------------------------------------

def demo_symmetric():
    """Demonstrate symmetric (AES) encryption."""
    print("\n=== SYMMETRIC ENCRYPTION (AES) ===")
    print("Same key encrypts and decrypts. Fast. Used for bulk data.\n")

    key = os.urandom(32)
    message = b"Credit card: 4111-1111-1111-1111"

    print(f"  Plaintext:  {message.decode()}")
    print(f"  Key:        {key.hex()[:32]}...")

    if HAS_CRYPTO:
        nonce, ct = real_aes_encrypt(message, key)
        recovered = real_aes_decrypt(nonce, ct, key)
        label = "AES-256-GCM (real)"
    else:
        nonce, ct = sim_aes_encrypt(message, key)
        recovered = sim_aes_decrypt(nonce, ct, key)
        label = "AES-256 (simulated)"

    print(f"  Ciphertext: {ct.hex()[:32]}...")
    print(f"  Decrypted:  {recovered.decode()}")
    print(f"  Algorithm:  {label}")
    print(f"  Match:      {message == recovered}")


def demo_asymmetric():
    """Demonstrate asymmetric (RSA) encryption."""
    print("\n=== ASYMMETRIC ENCRYPTION (RSA) ===")
    print("Public key encrypts, private key decrypts. Slow. Used for key exchange.\n")

    message = b"session-key-abc123"

    if HAS_CRYPTO:
        private_key = real_rsa_keygen()
        public_key = private_key.public_key()
        ct = real_rsa_encrypt(message, public_key)
        recovered = real_rsa_decrypt(ct, private_key)
        label = "RSA-2048 OAEP (real)"
        print(f"  Plaintext:   {message.decode()}")
        print(f"  Ciphertext:  {ct.hex()[:32]}...")
        print(f"  Decrypted:   {recovered.decode()}")
    else:
        keys = sim_rsa_keygen()
        ct = sim_rsa_encrypt(message, keys["public"])
        recovered = sim_rsa_decrypt(ct, keys["private"], chunk_size=2)
        label = "RSA (simulated, tiny primes)"
        print(f"  Plaintext:   {message.decode()}")
        print(f"  Ciphertext:  {ct[:4]}...")
        print(f"  Decrypted:   {recovered[:len(message)]}")

    print(f"  Algorithm:   {label}")


def demo_hybrid():
    """Demonstrate hybrid encryption - how TLS actually works."""
    print("\n=== HYBRID ENCRYPTION (How TLS Works) ===")
    print("RSA exchanges the AES key. AES encrypts the actual data.\n")

    session_key = os.urandom(32)
    bulk_data = b"This is a large HTTP response body with sensitive user data..." * 10

    print(f"  Step 1: Generate random AES session key ({len(session_key)} bytes)")

    if HAS_CRYPTO:
        private_key = real_rsa_keygen()
        public_key = private_key.public_key()
        encrypted_key = real_rsa_encrypt(session_key, public_key)
        print(f"  Step 2: RSA-encrypt session key -> {len(encrypted_key)} bytes")
        recovered_key = real_rsa_decrypt(encrypted_key, private_key)
    else:
        keys = sim_rsa_keygen()
        encrypted_key = sim_rsa_encrypt(session_key[:4], keys["public"])
        print(f"  Step 2: RSA-encrypt session key -> {len(encrypted_key)} chunks")
        recovered_key = session_key

    nonce, encrypted_data = sim_aes_encrypt(bulk_data, session_key)
    print(f"  Step 3: AES-encrypt {len(bulk_data)} bytes of data")
    print(f"  Step 4: Send encrypted key + encrypted data")

    decrypted = sim_aes_decrypt(nonce, encrypted_data, recovered_key)
    print(f"  Step 5: Receiver decrypts key with RSA, then data with AES")
    print(f"  Result: {decrypted[:50].decode()}...")
    print(f"  Match:  {bulk_data == decrypted}")


def demo_performance():
    """Compare symmetric vs asymmetric encryption speed."""
    print("\n=== PERFORMANCE COMPARISON ===\n")

    key = os.urandom(32)
    data_1kb = os.urandom(1024)
    iterations = 1000

    start = time.perf_counter()
    for _ in range(iterations):
        sim_aes_encrypt(data_1kb, key)
    aes_time = time.perf_counter() - start

    if HAS_CRYPTO:
        private_key = real_rsa_keygen()
        public_key = private_key.public_key()
        small_data = os.urandom(190)
        rsa_iters = 100

        start = time.perf_counter()
        for _ in range(rsa_iters):
            real_rsa_encrypt(small_data, public_key)
        rsa_time = time.perf_counter() - start

        aes_per_op = (aes_time / iterations) * 1_000_000
        rsa_per_op = (rsa_time / rsa_iters) * 1_000_000
        ratio = rsa_per_op / aes_per_op
        print(f"  AES encrypt (1 KB):  {aes_per_op:>8.1f} us/op  ({iterations} iterations)")
        print(f"  RSA encrypt (190 B): {rsa_per_op:>8.1f} us/op  ({rsa_iters} iterations)")
        print(f"  RSA is ~{ratio:.0f}x slower than AES")
    else:
        keys = sim_rsa_keygen()
        small_data = os.urandom(4)

        start = time.perf_counter()
        for _ in range(iterations):
            sim_rsa_encrypt(small_data, keys["public"])
        rsa_time = time.perf_counter() - start

        aes_per_op = (aes_time / iterations) * 1_000_000
        rsa_per_op = (rsa_time / iterations) * 1_000_000
        ratio = rsa_per_op / aes_per_op
        print(f"  Simulated AES (1 KB): {aes_per_op:>8.1f} us/op")
        print(f"  Simulated RSA (4 B):  {rsa_per_op:>8.1f} us/op")
        print(f"  RSA is ~{ratio:.0f}x slower (real gap is 100-1000x)")

    print("\n  Takeaway: Use asymmetric for key exchange only. Symmetric for bulk data.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Symmetric vs Asymmetric Encryption Lab")
    print(f"  cryptography library: {'installed' if HAS_CRYPTO else 'not found (using simulation)'}")

    demo_symmetric()
    demo_asymmetric()
    demo_hybrid()
    demo_performance()
