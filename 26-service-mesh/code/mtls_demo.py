"""
Mutual TLS (mTLS) Simulation
=============================
Simulates how sidecar proxies perform mutual TLS authentication in a mesh.
Uses a simplified certificate model to demonstrate the handshake, identity
verification, revocation, and what happens with invalid/foreign certs.

Usage:
  python mtls_demo.py
"""

import time
import uuid
import hashlib


# ---------------------------------------------------------------------------
# Certificate Authority (simulates mesh control plane CA)
# ---------------------------------------------------------------------------

class MeshCA:
    def __init__(self, mesh_name):
        self.mesh_name = mesh_name
        self.ca_key = uuid.uuid4().hex
        self.issued = {}
        self.revoked = set()

    def issue(self, service_name):
        cert_id = uuid.uuid4().hex[:12]
        sig_data = f"{service_name}:{cert_id}:{self.ca_key}"
        cert = {
            "cert_id": cert_id,
            "subject": service_name,
            "issuer": f"{self.mesh_name}-ca",
            "expires_at": time.time() + 86400,
            "signature": hashlib.sha256(sig_data.encode()).hexdigest()[:16],
        }
        self.issued[cert_id] = cert
        return cert

    def verify(self, cert):
        if cert["cert_id"] in self.revoked:
            return False, "certificate revoked"
        if cert["cert_id"] not in self.issued:
            return False, "not issued by this CA"
        if time.time() > cert["expires_at"]:
            return False, "certificate expired"
        sig_data = f"{cert['subject']}:{cert['cert_id']}:{self.ca_key}"
        expected = hashlib.sha256(sig_data.encode()).hexdigest()[:16]
        if cert["signature"] != expected:
            return False, "invalid signature"
        return True, "valid"

    def revoke(self, cert_id):
        self.revoked.add(cert_id)


# ---------------------------------------------------------------------------
# Sidecar proxy with mTLS
# ---------------------------------------------------------------------------

class Sidecar:
    def __init__(self, name, ca):
        self.name = name
        self.ca = ca
        self.cert = ca.issue(name)

    def connect_to(self, target):
        steps = []
        steps.append(f"[{self.name}] -> send cert to {target.name}")
        ok, reason = target.ca.verify(self.cert)
        steps.append(f"[{target.name}] verify {self.name}: {reason}")
        if not ok:
            return {"src": self.name, "dst": target.name, "status": "REJECTED",
                    "reason": reason, "steps": steps}

        steps.append(f"[{target.name}] -> send cert to {self.name}")
        ok, reason = self.ca.verify(target.cert)
        steps.append(f"[{self.name}] verify {target.name}: {reason}")
        if not ok:
            return {"src": self.name, "dst": target.name, "status": "REJECTED",
                    "reason": reason, "steps": steps}

        steps.append("[both] mTLS handshake complete - encrypted channel up")
        return {"src": self.name, "dst": target.name, "status": "ESTABLISHED", "steps": steps}


def show(result):
    tag = "OK" if result["status"] == "ESTABLISHED" else "FAIL"
    print(f"\n  [{tag}] {result['src']} -> {result['dst']}")
    for s in result["steps"]:
        print(f"    {s}")
    if result["status"] == "REJECTED":
        print(f"    Reason: {result['reason']}")


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def main():
    print("\n" + "=" * 60)
    print("MUTUAL TLS (mTLS) SIMULATION")
    print("=" * 60)

    ca = MeshCA("production-mesh")
    print(f"\n  Mesh CA: {ca.mesh_name} (key: {ca.ca_key[:8]}...)")

    order = Sidecar("order-service", ca)
    payment = Sidecar("payment-service", ca)
    inventory = Sidecar("inventory-service", ca)
    print(f"  Certs issued: {order.name}, {payment.name}, {inventory.name}")

    print("\n" + "-" * 60)
    print("Scenario 1: Valid mTLS (both in same mesh)")
    show(order.connect_to(payment))

    print("\n" + "-" * 60)
    print("Scenario 2: Another valid connection")
    show(order.connect_to(inventory))

    print("\n" + "-" * 60)
    print("Scenario 3: Revoked certificate")
    rogue = Sidecar("rogue-service", ca)
    ca.revoke(rogue.cert["cert_id"])
    print(f"\n  Revoked cert for {rogue.name}")
    show(rogue.connect_to(payment))

    print("\n" + "-" * 60)
    print("Scenario 4: Foreign certificate (different mesh)")
    foreign_ca = MeshCA("staging-mesh")
    foreign = Sidecar("foreign-service", foreign_ca)
    print(f"\n  Service from '{foreign_ca.mesh_name}' trying to connect")
    show(foreign.connect_to(payment))

    print("\n" + "-" * 60)
    print("Scenario 5: Expired certificate")
    expired = Sidecar("expired-service", ca)
    expired.cert["expires_at"] = time.time() - 3600
    show(expired.connect_to(payment))

    print("\n" + "-" * 60)
    print("How real mTLS works in a mesh:")
    print("  1. Control plane CA issues X.509 certs (SPIFFE identity)")
    print("  2. Auto-rotate every 24h - no manual management")
    print("  3. Sidecars do TLS handshake on every connection")
    print("  4. Both sides verify - that's the 'mutual' in mTLS")
    print("  5. App code uses plain HTTP - sidecar handles crypto")
    print("=" * 60)


if __name__ == "__main__":
    main()
