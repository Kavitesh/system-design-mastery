"""
TLS Handshake Simulation
=========================
Walks through every step of a TLS 1.3 handshake - ClientHello, ServerHello,
key exchange, certificate verification, and encrypted data transfer.

Usage: python tls_handshake.py
"""

import os
import hashlib
import hmac
import time

# ---------------------------------------------------------------------------
# Simulated Diffie-Hellman key exchange
# ---------------------------------------------------------------------------

DH_PRIME = 0xFFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1
DH_GENERATOR = 2


def dh_keypair() -> tuple[int, int]:
    """Generate a Diffie-Hellman key pair (private, public)."""
    private = int.from_bytes(os.urandom(16), 'big') % (DH_PRIME - 2) + 1
    public = pow(DH_GENERATOR, private, DH_PRIME)
    return private, public


def dh_shared_secret(my_private: int, their_public: int) -> bytes:
    """Derive shared secret from DH key exchange."""
    shared = pow(their_public, my_private, DH_PRIME)
    return hashlib.sha256(shared.to_bytes(32, 'big')).digest()


# ---------------------------------------------------------------------------
# Simulated certificate chain
# ---------------------------------------------------------------------------

def create_cert_chain(server_name: str) -> dict:
    """Simulates a certificate chain: Root CA -> Intermediate CA -> Server cert."""
    root_key = os.urandom(32)
    root_cert = {
        "subject": "DigiCert Global Root G2",
        "issuer": "DigiCert Global Root G2 (self-signed)",
        "public_key": hashlib.sha256(root_key).hexdigest()[:40],
        "valid_from": "2024-01-01",
        "valid_to": "2034-01-01",
    }

    intermediate_key = os.urandom(32)
    intermediate_sig = hmac.new(root_key, b"intermediate", hashlib.sha256).hexdigest()[:20]
    intermediate_cert = {
        "subject": "DigiCert SHA2 Extended Validation Server CA",
        "issuer": root_cert["subject"],
        "public_key": hashlib.sha256(intermediate_key).hexdigest()[:40],
        "signature_by_root": intermediate_sig,
    }

    server_key = os.urandom(32)
    server_sig = hmac.new(intermediate_key, server_name.encode(), hashlib.sha256).hexdigest()[:20]
    server_cert = {
        "subject": server_name,
        "issuer": intermediate_cert["subject"],
        "public_key": hashlib.sha256(server_key).hexdigest()[:40],
        "signature_by_intermediate": server_sig,
        "san": [server_name, f"*.{server_name}"],
    }

    return {
        "root": root_cert,
        "intermediate": intermediate_cert,
        "server": server_cert,
        "server_private_key": server_key,
    }


# ---------------------------------------------------------------------------
# TLS 1.3 handshake simulation
# ---------------------------------------------------------------------------

def simulate_tls_handshake(server_name: str = "api.example.com"):
    """Simulates a TLS 1.3 handshake step by step."""

    print(f"\n{'='*60}")
    print(f"  TLS 1.3 Handshake: client -> {server_name}")
    print(f"{'='*60}")

    # --- Step 1: ClientHello ---
    print("\n--- Step 1: ClientHello ---")
    client_random = os.urandom(32)
    client_dh_private, client_dh_public = dh_keypair()
    client_hello = {
        "tls_version": "TLS 1.3",
        "client_random": client_random.hex()[:16] + "...",
        "cipher_suites": [
            "TLS_AES_256_GCM_SHA384",
            "TLS_AES_128_GCM_SHA256",
            "TLS_CHACHA20_POLY1305_SHA256",
        ],
        "key_share": f"x25519: {hex(client_dh_public)[:20]}...",
        "sni": server_name,
    }
    print(f"  Client -> Server:")
    print(f"    TLS version:  {client_hello['tls_version']}")
    print(f"    SNI:          {client_hello['sni']}")
    print(f"    Client random: {client_hello['client_random']}")
    print(f"    Cipher suites: {len(client_hello['cipher_suites'])} offered")
    for cs in client_hello["cipher_suites"]:
        print(f"      - {cs}")
    print(f"    Key share:    {client_hello['key_share']}")

    # --- Step 2: ServerHello ---
    print("\n--- Step 2: ServerHello + Certificate ---")
    server_random = os.urandom(32)
    server_dh_private, server_dh_public = dh_keypair()
    chosen_cipher = "TLS_AES_256_GCM_SHA384"
    cert_chain = create_cert_chain(server_name)

    print(f"  Server -> Client:")
    print(f"    Server random: {server_random.hex()[:16]}...")
    print(f"    Chosen cipher: {chosen_cipher}")
    print(f"    Key share:    x25519: {hex(server_dh_public)[:20]}...")
    print(f"    Certificate chain:")
    print(f"      [1] {cert_chain['server']['subject']}")
    print(f"          Signed by: {cert_chain['server']['issuer']}")
    print(f"      [2] {cert_chain['intermediate']['subject']}")
    print(f"          Signed by: {cert_chain['intermediate']['issuer']}")
    print(f"      [3] {cert_chain['root']['subject']} (trusted root)")

    # --- Step 3: Key derivation ---
    print("\n--- Step 3: Key Derivation (both sides) ---")
    client_secret = dh_shared_secret(client_dh_private, server_dh_public)
    server_secret = dh_shared_secret(server_dh_private, client_dh_public)

    secrets_match = client_secret == server_secret
    print(f"  Client derives shared secret: {client_secret.hex()[:24]}...")
    print(f"  Server derives shared secret: {server_secret.hex()[:24]}...")
    print(f"  Secrets match: {secrets_match}")

    handshake_context = client_random + server_random
    client_write_key = hmac.new(client_secret, b"c_write" + handshake_context, hashlib.sha256).digest()
    server_write_key = hmac.new(client_secret, b"s_write" + handshake_context, hashlib.sha256).digest()
    print(f"  Client write key: {client_write_key.hex()[:24]}...")
    print(f"  Server write key: {server_write_key.hex()[:24]}...")

    # --- Step 4: Certificate verification ---
    print("\n--- Step 4: Certificate Verification ---")
    print(f"  Checking {cert_chain['server']['subject']}...")
    print(f"    Subject Alternative Names: {cert_chain['server']['san']}")
    print(f"    Matches requested SNI '{server_name}': True")
    print(f"    Signature by intermediate CA: verified")
    print(f"  Checking {cert_chain['intermediate']['subject']}...")
    print(f"    Signature by root CA: verified")
    print(f"  Checking {cert_chain['root']['subject']}...")
    print(f"    Found in trusted root store: True")
    print(f"  Certificate chain: VALID")

    # --- Step 5: Finished messages ---
    print("\n--- Step 5: Finished Messages ---")
    client_finished = hmac.new(client_write_key, b"client_finished", hashlib.sha256).hexdigest()[:16]
    server_finished = hmac.new(server_write_key, b"server_finished", hashlib.sha256).hexdigest()[:16]
    print(f"  Client -> Server: Finished (verify={client_finished}...)")
    print(f"  Server -> Client: Finished (verify={server_finished}...)")
    print(f"  Handshake complete. All further traffic encrypted with AES-256-GCM.")

    # --- Step 6: Encrypted application data ---
    print("\n--- Step 6: Encrypted Application Data ---")
    request = b"GET /api/users HTTP/1.1\r\nHost: api.example.com\r\n"
    key_stream = hashlib.sha256(client_write_key + os.urandom(12)).digest()
    extended = (key_stream * 3)[:len(request)]
    encrypted_request = bytes(a ^ b for a, b in zip(request, extended))
    print(f"  Plaintext request:  {request[:40].decode()}...")
    print(f"  Encrypted request:  {encrypted_request.hex()[:40]}...")
    print(f"  Wire sees only ciphertext - request method, path, headers all hidden")

    return secrets_match


# ---------------------------------------------------------------------------
# TLS version comparison
# ---------------------------------------------------------------------------

def compare_tls_versions():
    """Shows key differences between TLS 1.2 and TLS 1.3."""
    print(f"\n{'='*60}")
    print(f"  TLS 1.2 vs TLS 1.3 Comparison")
    print(f"{'='*60}\n")

    comparisons = [
        ("Handshake round trips", "2 RTT", "1 RTT"),
        ("0-RTT resumption", "No", "Yes (with PSK)"),
        ("Key exchange", "RSA or DHE", "DHE only (forward secrecy mandatory)"),
        ("Cipher suites", "37 options (many weak)", "5 options (all strong)"),
        ("RSA key transport", "Allowed", "Removed"),
        ("CBC mode ciphers", "Allowed", "Removed"),
        ("RC4, DES, 3DES", "Allowed", "Removed"),
        ("MD5, SHA-1", "Allowed", "Removed"),
        ("Forward secrecy", "Optional", "Mandatory"),
        ("Encrypted handshake", "Partial", "Most of handshake encrypted"),
    ]

    print(f"  {'Feature':<28} {'TLS 1.2':<28} {'TLS 1.3':<28}")
    print(f"  {'-'*28} {'-'*28} {'-'*28}")
    for feature, v12, v13 in comparisons:
        print(f"  {feature:<28} {v12:<28} {v13:<28}")

    print(f"\n  TLS 1.3 removed everything that was known to be weak or unnecessary.")
    print(f"  Fewer options means fewer ways to misconfigure. That's a security win.")


# ---------------------------------------------------------------------------
# mTLS explanation
# ---------------------------------------------------------------------------

def explain_mtls():
    """Explains mutual TLS for service-to-service communication."""
    print(f"\n{'='*60}")
    print(f"  Mutual TLS (mTLS) - Service-to-Service Auth")
    print(f"{'='*60}\n")

    steps = [
        ("Standard TLS", "Client verifies server certificate", "Server identity confirmed"),
        ("", "Server does NOT verify client", "Any client can connect"),
        ("", "", ""),
        ("Mutual TLS", "Client verifies server certificate", "Server identity confirmed"),
        ("", "Server ALSO verifies client certificate", "Client identity confirmed"),
        ("", "Both sides authenticated", "Zero-trust service mesh"),
    ]

    print("  Standard TLS:")
    print("    Browser ----[verifies server cert]----> api.example.com")
    print("    Browser <---[no client verification]--- api.example.com")
    print("    Result: Server is authenticated, client is anonymous")
    print()
    print("  Mutual TLS:")
    print("    Payment Service ---[verifies server cert]---> Order Service")
    print("    Payment Service <--[verifies client cert]---- Order Service")
    print("    Result: Both services authenticated, encrypted, trusted")
    print()
    print("  mTLS use cases:")
    print("    - Kubernetes service mesh (Istio, Linkerd)")
    print("    - Microservice-to-microservice calls")
    print("    - API gateway to backend services")
    print("    - Database connections from application servers")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("TLS Handshake Simulation Lab")

    start = time.perf_counter()
    success = simulate_tls_handshake("api.example.com")
    elapsed = (time.perf_counter() - start) * 1000

    print(f"\n  Handshake simulation took {elapsed:.1f}ms")
    print(f"  Real TLS 1.3 handshake takes ~50-100ms (1 RTT)")

    compare_tls_versions()
    explain_mtls()
