# Monolith vs Microservices - Code Lab

Hands-on demos comparing monolithic and microservice architectures using the same e-commerce domain.

## What's Included

| File | Description |
|------|-------------|
| `monolith_app.py` | Complete e-commerce app in one Flask process - users, products, orders |
| `microservices/user_service.py` | User service - owns user data, runs on port 5001 |
| `microservices/product_service.py` | Product service - owns catalog and inventory, port 5002 |
| `microservices/order_service.py` | Order service - calls user + product services via HTTP, port 5003 |
| `api_gateway_demo.py` | API gateway that routes and aggregates across all services |
| `service_discovery.py` | Service registry with registration, discovery, and heartbeat monitoring |

## Prerequisites

```bash
pip install flask requests
```

## Running the Demos

### 1. Monolith (standalone)

Run the complete monolith with simulated requests - no server needed:

```bash
python monolith_app.py
```

Or run it as a server:

```bash
python monolith_app.py --serve
# All endpoints on http://localhost:5000
```

### 2. Microservices (3 terminals)

Start each service in a separate terminal:

```bash
# Terminal 1
python microservices/user_service.py

# Terminal 2
python microservices/product_service.py

# Terminal 3
python microservices/order_service.py
```

Then test with curl:

```bash
# List users
curl http://localhost:5001/users

# List products
curl http://localhost:5002/products

# Place an order (calls both user and product services internally)
curl -X POST http://localhost:5003/orders \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "product_id": 1, "quantity": 2}'
```

### 3. API Gateway (4 terminals)

Start all three microservices (above), then start the gateway:

```bash
python api_gateway_demo.py
```

All traffic goes through the gateway on port 5000:

```bash
# Proxied requests
curl http://localhost:5000/api/users
curl http://localhost:5000/api/products

# Aggregated dashboard - combines data from all 3 services
curl http://localhost:5000/api/dashboard/1

# Aggregated health check
curl http://localhost:5000/api/health
```

### 4. Service Discovery (standalone)

Run the full simulation with no other services needed:

```bash
python service_discovery.py
```

Or run the registry as a server:

```bash
python service_discovery.py --serve
# Registry on http://localhost:5100
```

## What to Notice

- **Monolith:** Orders validate users and check stock with direct dictionary lookups. Fast, simple, transactional.
- **Microservices:** Orders make HTTP calls to user and product services. Slower, but services can deploy and scale independently.
- **API Gateway:** Clients hit one endpoint instead of three. The gateway aggregates responses from multiple services.
- **Service Discovery:** Services register themselves and send heartbeats. Clients discover healthy instances dynamically.
