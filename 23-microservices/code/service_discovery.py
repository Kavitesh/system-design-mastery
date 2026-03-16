"""
Service Discovery Demo
=======================
A standalone service registry that services register with and clients query.
Includes heartbeat monitoring - services that stop sending heartbeats get
marked as unhealthy and eventually deregistered.

This is what Consul, Eureka, or etcd do in production.

Run:
  python service_discovery.py

The demo runs a registry server and simulates services registering,
sending heartbeats, and being discovered. No other services needed.

Registry Endpoints:
  POST /register               - Register a service instance
  GET  /discover/<service>     - Find healthy instances of a service
  POST /heartbeat              - Send a heartbeat to stay alive
  GET  /registry               - View the full registry
  POST /deregister             - Remove a service instance
"""

import time
import threading
from flask import Flask, jsonify, request

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Registry data
# ---------------------------------------------------------------------------

REGISTRY = {}
HEARTBEAT_TIMEOUT = 10
CLEANUP_INTERVAL = 5
lock = threading.Lock()


# ---------------------------------------------------------------------------
# Registry endpoints
# ---------------------------------------------------------------------------

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    service_name = data["service"]
    instance_id = data["instance_id"]
    host = data["host"]
    port = data["port"]

    with lock:
        if service_name not in REGISTRY:
            REGISTRY[service_name] = {}

        REGISTRY[service_name][instance_id] = {
            "instance_id": instance_id,
            "host": host,
            "port": port,
            "status": "healthy",
            "registered_at": time.time(),
            "last_heartbeat": time.time(),
            "metadata": data.get("metadata", {}),
        }

    return jsonify({"registered": instance_id, "service": service_name}), 201


@app.route("/discover/<service_name>")
def discover(service_name):
    with lock:
        instances = REGISTRY.get(service_name, {})
        healthy = [inst for inst in instances.values() if inst["status"] == "healthy"]

    if not healthy:
        return jsonify({"service": service_name, "instances": [], "message": "No healthy instances"}), 404

    return jsonify({
        "service": service_name,
        "instances": healthy,
        "count": len(healthy),
    })


@app.route("/heartbeat", methods=["POST"])
def heartbeat():
    data = request.json
    service_name = data["service"]
    instance_id = data["instance_id"]

    with lock:
        instances = REGISTRY.get(service_name, {})
        instance = instances.get(instance_id)
        if not instance:
            return jsonify({"error": "Instance not registered"}), 404

        instance["last_heartbeat"] = time.time()
        instance["status"] = "healthy"

    return jsonify({"acknowledged": instance_id})


@app.route("/deregister", methods=["POST"])
def deregister():
    data = request.json
    service_name = data["service"]
    instance_id = data["instance_id"]

    with lock:
        instances = REGISTRY.get(service_name, {})
        if instance_id in instances:
            del instances[instance_id]
            return jsonify({"deregistered": instance_id})

    return jsonify({"error": "Instance not found"}), 404


@app.route("/registry")
def view_registry():
    with lock:
        summary = {}
        for service_name, instances in REGISTRY.items():
            summary[service_name] = {
                "total": len(instances),
                "healthy": sum(1 for i in instances.values() if i["status"] == "healthy"),
                "unhealthy": sum(1 for i in instances.values() if i["status"] == "unhealthy"),
                "instances": list(instances.values()),
            }
    return jsonify(summary)


# ---------------------------------------------------------------------------
# Heartbeat monitor - marks instances unhealthy if they miss heartbeats
# ---------------------------------------------------------------------------

def heartbeat_monitor():
    while True:
        time.sleep(CLEANUP_INTERVAL)
        now = time.time()
        with lock:
            for service_name, instances in REGISTRY.items():
                stale = []
                for iid, inst in instances.items():
                    age = now - inst["last_heartbeat"]
                    if age > HEARTBEAT_TIMEOUT * 2:
                        stale.append(iid)
                    elif age > HEARTBEAT_TIMEOUT:
                        inst["status"] = "unhealthy"
                for iid in stale:
                    del instances[iid]


# ---------------------------------------------------------------------------
# Simulation - demonstrates the full lifecycle without external services
# ---------------------------------------------------------------------------

def run_simulation():
    print("\n=== Service Discovery Demo ===\n")

    monitor = threading.Thread(target=heartbeat_monitor, daemon=True)
    monitor.start()

    with app.test_client() as client:
        # Register services
        services = [
            {"service": "user-service", "instance_id": "user-1", "host": "10.0.1.1", "port": 5001},
            {"service": "user-service", "instance_id": "user-2", "host": "10.0.1.2", "port": 5001},
            {"service": "product-service", "instance_id": "product-1", "host": "10.0.2.1", "port": 5002},
            {"service": "order-service", "instance_id": "order-1", "host": "10.0.3.1", "port": 5003},
            {"service": "order-service", "instance_id": "order-2", "host": "10.0.3.2", "port": 5003},
            {"service": "order-service", "instance_id": "order-3", "host": "10.0.3.3", "port": 5003},
        ]

        print("[1] Registering 6 service instances...")
        for svc in services:
            resp = client.post("/register", json=svc)
            r = resp.get_json()
            print(f"    Registered {r['registered']} for {r['service']}")

        # Discover services
        print("\n[2] Discovering services...")
        for name in ["user-service", "product-service", "order-service"]:
            resp = client.get(f"/discover/{name}")
            data = resp.get_json()
            instances = data.get("instances", [])
            hosts = [f"{i['host']}:{i['port']}" for i in instances]
            print(f"    {name}: {len(instances)} instances -> {', '.join(hosts)}")

        # View full registry
        print("\n[3] Full registry view:")
        resp = client.get("/registry")
        for name, info in resp.get_json().items():
            print(f"    {name}: {info['healthy']} healthy, {info['unhealthy']} unhealthy")

        # Send heartbeats for some instances
        print("\n[4] Sending heartbeats (only for user-1 and product-1)...")
        for svc, iid in [("user-service", "user-1"), ("product-service", "product-1")]:
            client.post("/heartbeat", json={"service": svc, "instance_id": iid})
            print(f"    Heartbeat sent: {iid}")

        # Simulate time passing - mark others as stale
        print("\n[5] Simulating missed heartbeats (advancing clock)...")
        with lock:
            stale_time = time.time() - HEARTBEAT_TIMEOUT - 1
            for svc_instances in REGISTRY.values():
                for iid, inst in svc_instances.items():
                    if iid not in ("user-1", "product-1"):
                        inst["last_heartbeat"] = stale_time

        # Run one cycle of the monitor inline
        now = time.time()
        with lock:
            for svc_instances in REGISTRY.values():
                for inst in svc_instances.values():
                    if now - inst["last_heartbeat"] > HEARTBEAT_TIMEOUT:
                        inst["status"] = "unhealthy"

        print("\n[6] Registry after missed heartbeats:")
        resp = client.get("/registry")
        for name, info in resp.get_json().items():
            print(f"    {name}: {info['healthy']} healthy, {info['unhealthy']} unhealthy")

        # Discovery now returns only healthy instances
        print("\n[7] Discovering user-service (only healthy):")
        resp = client.get("/discover/user-service")
        data = resp.get_json()
        for inst in data.get("instances", []):
            print(f"    {inst['instance_id']} at {inst['host']}:{inst['port']} - {inst['status']}")

        # Deregister a service
        print("\n[8] Deregistering order-1...")
        client.post("/deregister", json={"service": "order-service", "instance_id": "order-1"})

        resp = client.get("/registry")
        order_info = resp.get_json().get("order-service", {})
        print(f"    order-service now has {order_info.get('total', 0)} instances")

        # Try discovering a non-existent service
        print("\n[9] Discovering unknown service 'payment-service':")
        resp = client.get("/discover/payment-service")
        print(f"    Status: {resp.status_code} - {resp.get_json()['message']}")

        print("\n[Key insight] Service discovery decouples services from fixed")
        print("  addresses. Instances come and go, scale up and down, and")
        print("  clients always find healthy ones through the registry.\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    if "--serve" in sys.argv:
        monitor = threading.Thread(target=heartbeat_monitor, daemon=True)
        monitor.start()
        print("Service registry starting on port 5100")
        app.run(port=5100, debug=False)
    else:
        run_simulation()
