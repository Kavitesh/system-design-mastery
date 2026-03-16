# Chapter 29 - Code Labs: Encryption & Data Security

Hands-on Python demos for encryption primitives, TLS, hashing, and key management patterns.

## Labs

| # | File | What You'll Learn |
|---|------|-------------------|
| 1 | `symmetric_vs_asymmetric.py` | AES vs RSA encryption - how they work, when to use each, performance gap |
| 2 | `tls_handshake.py` | Simulated TLS 1.3 handshake - every step from ClientHello to encrypted traffic |
| 3 | `hashing_demo.py` | SHA-256, HMAC, bcrypt - different tools for different jobs |
| 4 | `envelope_encryption.py` | Envelope encryption pattern - data keys wrapped by master keys |

## Running the Labs

Each lab is standalone. No external dependencies required for core functionality.

```bash
python symmetric_vs_asymmetric.py
python tls_handshake.py
python hashing_demo.py
python envelope_encryption.py
```

### Optional Dependencies

For real AES/RSA operations (instead of simulated), install the `cryptography` library:

```bash
pip install cryptography bcrypt
```

The labs detect whether these packages are available and upgrade from simulation to real crypto automatically.

## Key Takeaways

- Symmetric encryption (AES) is 100-1000x faster than asymmetric (RSA) - use asymmetric only for key exchange
- TLS combines both: asymmetric for handshake, symmetric for data transfer
- Never use SHA-256 for passwords - use bcrypt or Argon2id (intentionally slow)
- Envelope encryption lets you rotate master keys without re-encrypting all data
- HMAC proves both integrity AND authenticity - plain hashing only proves integrity
