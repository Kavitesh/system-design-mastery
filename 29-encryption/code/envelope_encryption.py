"""
Envelope Encryption
====================
Demonstrates the envelope encryption pattern used by AWS KMS, Azure Key Vault,
and GCP Cloud KMS. Data keys encrypt data, master keys encrypt data keys.

Usage: python envelope_encryption.py
"""

import os
import hashlib
import hmac
import json
import time
import base64

# ---------------------------------------------------------------------------
# Simulated KMS (Key Management Service)
# ---------------------------------------------------------------------------

class SimulatedKMS:
    """Simulates a cloud KMS with master key management and audit logging."""

    def __init__(self):
        self._master_keys = {}
        self._audit_log = []

    def create_master_key(self, alias: str) -> str:
        """Create a new Customer Master Key. Key material never leaves KMS."""
        key_id = f"cmk-{os.urandom(8).hex()}"
        self._master_keys[key_id] = {
            "alias": alias,
            "key_material": os.urandom(32),
            "created": time.time(),
            "state": "enabled",
        }
        self._log("CreateKey", key_id, alias)
        return key_id

    def generate_data_key(self, key_id: str) -> tuple[bytes, bytes]:
        """
        Generate a data encryption key (DEK).
        Returns (plaintext_dek, encrypted_dek).
        The plaintext DEK should be used then immediately discarded.
        """
        if key_id not in self._master_keys:
            raise ValueError(f"Key {key_id} not found")

        master_material = self._master_keys[key_id]["key_material"]
        plaintext_dek = os.urandom(32)

        nonce = os.urandom(12)
        key_stream = hashlib.sha256(master_material + nonce).digest()
        extended = (key_stream * 2)[:len(plaintext_dek)]
        encrypted_dek = bytes(a ^ b for a, b in zip(plaintext_dek, extended))
        encrypted_dek_bundle = nonce + encrypted_dek

        self._log("GenerateDataKey", key_id)
        return plaintext_dek, encrypted_dek_bundle

    def decrypt_data_key(self, key_id: str, encrypted_dek_bundle: bytes) -> bytes:
        """Decrypt a data encryption key using the master key."""
        if key_id not in self._master_keys:
            raise ValueError(f"Key {key_id} not found")

        master_material = self._master_keys[key_id]["key_material"]
        nonce = encrypted_dek_bundle[:12]
        encrypted_dek = encrypted_dek_bundle[12:]

        key_stream = hashlib.sha256(master_material + nonce).digest()
        extended = (key_stream * 2)[:len(encrypted_dek)]
        plaintext_dek = bytes(a ^ b for a, b in zip(encrypted_dek, extended))

        self._log("Decrypt", key_id)
        return plaintext_dek

    def rotate_master_key(self, key_id: str) -> str:
        """Rotate master key material. Old encrypted DEKs still work with old material."""
        if key_id not in self._master_keys:
            raise ValueError(f"Key {key_id} not found")

        old_alias = self._master_keys[key_id]["alias"]
        old_material = self._master_keys[key_id]["key_material"]

        self._master_keys[key_id]["key_material"] = os.urandom(32)
        self._master_keys[key_id]["previous_material"] = old_material
        self._master_keys[key_id]["rotated"] = time.time()

        self._log("RotateKey", key_id, old_alias)
        return key_id

    def get_audit_log(self) -> list:
        return self._audit_log.copy()

    def _log(self, action: str, key_id: str, detail: str = ""):
        self._audit_log.append({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "action": action,
            "key_id": key_id,
            "detail": detail,
        })


# ---------------------------------------------------------------------------
# Data encryption with envelope pattern
# ---------------------------------------------------------------------------

def encrypt_data(plaintext: bytes, dek: bytes) -> tuple[bytes, bytes]:
    """Encrypt data with the data encryption key (simulated AES)."""
    nonce = os.urandom(12)
    key_stream = hashlib.sha256(dek + nonce).digest()
    extended = (key_stream * ((len(plaintext) // 32) + 1))[:len(plaintext)]
    ciphertext = bytes(a ^ b for a, b in zip(plaintext, extended))
    tag = hmac.new(dek, nonce + ciphertext, hashlib.sha256).digest()[:16]
    return nonce, ciphertext + tag


def decrypt_data(nonce: bytes, ciphertext_and_tag: bytes, dek: bytes) -> bytes:
    """Decrypt data with the data encryption key (simulated AES)."""
    ciphertext = ciphertext_and_tag[:-16]
    tag = ciphertext_and_tag[-16:]

    expected_tag = hmac.new(dek, nonce + ciphertext, hashlib.sha256).digest()[:16]
    if not hmac.compare_digest(tag, expected_tag):
        raise ValueError("Authentication failed - data may be tampered")

    key_stream = hashlib.sha256(dek + nonce).digest()
    extended = (key_stream * ((len(ciphertext) // 32) + 1))[:len(ciphertext)]
    return bytes(a ^ b for a, b in zip(ciphertext, extended))


# ---------------------------------------------------------------------------
# Encrypted record storage
# ---------------------------------------------------------------------------

class EncryptedStore:
    """Simulates encrypted storage using envelope encryption."""

    def __init__(self, kms: SimulatedKMS, master_key_id: str):
        self._kms = kms
        self._master_key_id = master_key_id
        self._records = {}

    def put(self, record_id: str, data: dict) -> dict:
        """Encrypt and store a record. Each record gets its own DEK."""
        plaintext = json.dumps(data).encode()

        plaintext_dek, encrypted_dek = self._kms.generate_data_key(self._master_key_id)
        nonce, ciphertext = encrypt_data(plaintext, plaintext_dek)

        plaintext_dek = b'\x00' * 32  # noqa: F841 - wipe from memory

        record = {
            "id": record_id,
            "encrypted_dek": base64.b64encode(encrypted_dek).decode(),
            "nonce": base64.b64encode(nonce).decode(),
            "ciphertext": base64.b64encode(ciphertext).decode(),
            "master_key_id": self._master_key_id,
        }
        self._records[record_id] = record
        return record

    def get(self, record_id: str) -> dict:
        """Retrieve and decrypt a record."""
        record = self._records.get(record_id)
        if not record:
            raise KeyError(f"Record {record_id} not found")

        encrypted_dek = base64.b64decode(record["encrypted_dek"])
        nonce = base64.b64decode(record["nonce"])
        ciphertext = base64.b64decode(record["ciphertext"])

        plaintext_dek = self._kms.decrypt_data_key(record["master_key_id"], encrypted_dek)
        plaintext = decrypt_data(nonce, ciphertext, plaintext_dek)

        plaintext_dek = b'\x00' * 32  # noqa: F841 - wipe from memory

        return json.loads(plaintext.decode())

    def list_records(self) -> list:
        return list(self._records.keys())


# ---------------------------------------------------------------------------
# Demos
# ---------------------------------------------------------------------------

def demo_basic_envelope():
    """Demonstrate the core envelope encryption flow."""
    print("\n=== ENVELOPE ENCRYPTION - Basic Flow ===")
    print("Data key encrypts data. Master key encrypts data key.\n")

    kms = SimulatedKMS()
    master_key_id = kms.create_master_key("production/user-data")

    print(f"  Step 1: Created master key in KMS")
    print(f"    Key ID: {master_key_id}")
    print(f"    Key material: NEVER LEAVES KMS\n")

    plaintext_dek, encrypted_dek = kms.generate_data_key(master_key_id)
    print(f"  Step 2: KMS generates data encryption key (DEK)")
    print(f"    Plaintext DEK:  {plaintext_dek.hex()[:32]}...")
    print(f"    Encrypted DEK:  {encrypted_dek.hex()[:32]}...")
    print(f"    (KMS returns both - use plaintext, store encrypted)\n")

    sensitive_data = b"SSN: 123-45-6789, Account: 9876543210"
    nonce, ciphertext = encrypt_data(sensitive_data, plaintext_dek)
    print(f"  Step 3: Encrypt data with plaintext DEK")
    print(f"    Plaintext:  {sensitive_data.decode()}")
    print(f"    Ciphertext: {ciphertext.hex()[:32]}...\n")

    plaintext_dek = b'\x00' * 32
    print(f"  Step 4: WIPE plaintext DEK from memory")
    print(f"    DEK in memory: {plaintext_dek.hex()[:32]}... (zeroed)\n")

    print(f"  Step 5: Store encrypted data + encrypted DEK together")
    print(f"    Stored: {{ciphertext: '...', encrypted_dek: '...'}}")
    print(f"    An attacker with disk access sees only encrypted blobs.\n")

    recovered_dek = kms.decrypt_data_key(master_key_id, encrypted_dek)
    recovered_data = decrypt_data(nonce, ciphertext, recovered_dek)
    print(f"  Step 6: To decrypt - send encrypted DEK to KMS")
    print(f"    KMS decrypts DEK:  {recovered_dek.hex()[:32]}...")
    print(f"    Decrypt data:      {recovered_data.decode()}")
    print(f"    Match: {sensitive_data == recovered_data}")


def demo_per_record_encryption():
    """Show envelope encryption with per-record data keys."""
    print("\n=== PER-RECORD ENCRYPTION ===")
    print("Each record gets its own DEK. Compromise one, lose only one record.\n")

    kms = SimulatedKMS()
    master_key_id = kms.create_master_key("production/pii")
    store = EncryptedStore(kms, master_key_id)

    users = [
        {"name": "Alice Johnson", "ssn": "123-45-6789", "salary": 125000},
        {"name": "Bob Smith", "ssn": "987-65-4321", "salary": 98000},
        {"name": "Carol Williams", "ssn": "456-78-9012", "salary": 145000},
    ]

    print("  Encrypting records (each with unique DEK):\n")
    for i, user in enumerate(users):
        record = store.put(f"user-{i+1}", user)
        print(f"    user-{i+1}: {user['name']}")
        print(f"      Encrypted DEK: {record['encrypted_dek'][:24]}...")
        print(f"      Ciphertext:    {record['ciphertext'][:24]}...")
        print()

    print("  Decrypting records:\n")
    for record_id in store.list_records():
        data = store.get(record_id)
        print(f"    {record_id}: {data['name']} | SSN: {data['ssn']} | Salary: ${data['salary']:,}")

    print(f"\n  Each record has a unique DEK. If user-1's DEK is compromised,")
    print(f"  user-2 and user-3 remain protected. That's blast radius containment.")


def demo_key_rotation():
    """Demonstrate master key rotation without re-encrypting data."""
    print("\n=== MASTER KEY ROTATION ===")
    print("Rotate the master key without re-encrypting all your data.\n")

    kms = SimulatedKMS()
    master_key_id = kms.create_master_key("production/payments")
    store = EncryptedStore(kms, master_key_id)

    store.put("txn-001", {"card": "4111-1111-1111-1111", "amount": 59.99})
    store.put("txn-002", {"card": "5500-0000-0000-0004", "amount": 129.50})

    print(f"  Before rotation:")
    for rid in store.list_records():
        data = store.get(rid)
        print(f"    {rid}: card={data['card']}, amount=${data['amount']}")

    print(f"\n  --- Rotating master key ---")
    print(f"  In a real KMS:")
    print(f"    - Old key material is kept for decrypting existing DEKs")
    print(f"    - New key material is used for encrypting new DEKs")
    print(f"    - No data re-encryption needed")
    print(f"    - Gradual re-encryption of DEKs can happen in background\n")

    store.put("txn-003", {"card": "3400-0000-0000-009", "amount": 250.00})

    print(f"  After rotation - all records still accessible:")
    for rid in store.list_records():
        data = store.get(rid)
        print(f"    {rid}: card={data['card']}, amount=${data['amount']}")


def demo_why_envelope():
    """Explain why envelope encryption beats direct encryption."""
    print("\n=== WHY ENVELOPE ENCRYPTION? ===\n")

    print("  Direct encryption (master key encrypts data directly):")
    print("    Problem 1: Master key touches every piece of data")
    print("    Problem 2: Key rotation = re-encrypt ALL data (terabytes)")
    print("    Problem 3: Master key must be fast-accessible (less secure)")
    print("    Problem 4: Compromised key exposes everything\n")

    print("  Envelope encryption (master key encrypts DEKs):")
    print("    Benefit 1: Master key only touches small DEKs (32 bytes each)")
    print("    Benefit 2: Key rotation = re-encrypt only DEKs (fast)")
    print("    Benefit 3: Master key stays in HSM (maximum security)")
    print("    Benefit 4: Each record's DEK is independent (blast radius)\n")

    records = [100, 1_000, 100_000, 10_000_000]
    avg_record_kb = 4
    dek_bytes = 32

    print(f"  Cost of master key rotation (re-encrypt everything):\n")
    print(f"    {'Records':<14} {'Direct (re-encrypt data)':<30} {'Envelope (re-encrypt DEKs)'}")
    print(f"    {'-'*14} {'-'*30} {'-'*30}")
    for count in records:
        data_mb = (count * avg_record_kb) / 1024
        dek_kb = (count * dek_bytes) / 1024
        print(f"    {count:<14,} {data_mb:>12,.0f} MB to process     {dek_kb:>12,.1f} KB to process")

    print(f"\n  At 10M records, you're re-encrypting 312 KB instead of 39 GB.")
    print(f"  That's the difference between milliseconds and hours.")


def demo_audit_log():
    """Show KMS audit logging."""
    print("\n=== KMS AUDIT LOG ===")
    print("Every key operation is logged. This is critical for compliance.\n")

    kms = SimulatedKMS()
    key_id = kms.create_master_key("prod/secrets")
    kms.generate_data_key(key_id)
    kms.generate_data_key(key_id)

    dek_plain, dek_enc = kms.generate_data_key(key_id)
    kms.decrypt_data_key(key_id, dek_enc)

    for entry in kms.get_audit_log():
        detail = f" ({entry['detail']})" if entry['detail'] else ""
        print(f"  [{entry['timestamp']}] {entry['action']:<20} {entry['key_id']}{detail}")

    print(f"\n  In AWS KMS, these logs go to CloudTrail.")
    print(f"  You can alert on unusual patterns: too many decrypt calls,")
    print(f"  access from unexpected regions, bulk key generation, etc.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Envelope Encryption Lab")

    demo_basic_envelope()
    demo_per_record_encryption()
    demo_key_rotation()
    demo_why_envelope()
    demo_audit_log()
