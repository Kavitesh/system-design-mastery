# Authentication & Authorization - Code Lab

Hands-on demos covering JWT authentication, OAuth 2.0 flows, role-based access control, and proper password hashing.

## What's Included

| File | Description |
|------|-------------|
| `jwt_auth.py` | Flask app with JWT login, protected routes, and token refresh |
| `oauth_flow.py` | Simulates OAuth 2.0 authorization code flow with auth server and resource server |
| `rbac_demo.py` | Role-based access control system with users, roles, and permissions |
| `password_hashing.py` | Proper password hashing vs common mistakes - timing comparisons |

## Prerequisites

```bash
pip install flask pyjwt bcrypt
```

## Running the Demos

### 1. JWT Authentication

A full Flask API with login, protected routes, and token refresh:

```bash
python jwt_auth.py
```

Then test with curl:

```bash
# Login
curl -X POST http://localhost:5000/login \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "password123"}'

# Access protected route (use the token from login response)
curl http://localhost:5000/protected \
  -H "Authorization: Bearer <your-token>"
```

### 2. OAuth 2.0 Flow Simulation

Simulates the full authorization code flow - no external services needed:

```bash
python oauth_flow.py
```

### 3. Role-Based Access Control

Demonstrates RBAC with users, roles, and permission checks:

```bash
python rbac_demo.py
```

### 4. Password Hashing

Compares plaintext, MD5, SHA-256, and bcrypt - shows why slow hashing matters:

```bash
python password_hashing.py
```
