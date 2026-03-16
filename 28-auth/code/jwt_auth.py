"""
JWT Authentication Server
=========================
Flask app with JWT login, protected routes, token refresh,
and role-based claims.

Run: python jwt_auth.py
Serve: python jwt_auth.py --serve
"""

import sys, datetime, jwt
from functools import wraps
from flask import Flask, request, jsonify

app = Flask(__name__)
SECRET_KEY = "super-secret-key-change-in-production"
REFRESH_SECRET = "refresh-secret-also-change-this"
ACCESS_EXPIRY = datetime.timedelta(minutes=15)
REFRESH_EXPIRY = datetime.timedelta(days=7)

USERS = {
    "alice": {"password": "password123", "role": "admin", "user_id": 1},
    "bob": {"password": "bobsecure", "role": "editor", "user_id": 2},
    "charlie": {"password": "charliepass", "role": "viewer", "user_id": 3},
}
refresh_store = {}

# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------

def make_access_token(user_id, username, role):
    payload = {
        "user_id": user_id, "username": username, "role": role,
        "exp": datetime.datetime.utcnow() + ACCESS_EXPIRY,
        "iat": datetime.datetime.utcnow(), "type": "access",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def make_refresh_token(user_id):
    payload = {
        "user_id": user_id, "type": "refresh",
        "exp": datetime.datetime.utcnow() + REFRESH_EXPIRY,
    }
    token = jwt.encode(payload, REFRESH_SECRET, algorithm="HS256")
    refresh_store[user_id] = token
    return token

# ---------------------------------------------------------------------------
# Auth decorators
# ---------------------------------------------------------------------------

def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        hdr = request.headers.get("Authorization", "")
        if not hdr.startswith("Bearer "):
            return jsonify({"error": "Missing Bearer token"}), 401
        try:
            payload = jwt.decode(hdr.split(" ", 1)[1], SECRET_KEY, algorithms=["HS256"])
            if payload.get("type") != "access":
                return jsonify({"error": "Wrong token type"}), 401
            request.user = payload
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired - use /refresh"}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({"error": f"Invalid token: {e}"}), 401
        return f(*args, **kwargs)
    return wrapper

def require_role(*roles):
    def decorator(f):
        @wraps(f)
        @require_auth
        def wrapper(*args, **kwargs):
            if request.user["role"] not in roles:
                return jsonify({"error": "Forbidden", "need": list(roles)}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    user = USERS.get(data.get("username", ""))
    if not user or user["password"] != data.get("password"):
        return jsonify({"error": "Invalid credentials"}), 401
    username = data["username"]
    return jsonify({
        "access_token": make_access_token(user["user_id"], username, user["role"]),
        "refresh_token": make_refresh_token(user["user_id"]),
        "token_type": "Bearer",
        "expires_in": int(ACCESS_EXPIRY.total_seconds()),
    })

@app.route("/refresh", methods=["POST"])
def refresh():
    token = (request.get_json() or {}).get("refresh_token", "")
    try:
        payload = jwt.decode(token, REFRESH_SECRET, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid refresh token"}), 401
    uid = payload["user_id"]
    if refresh_store.get(uid) != token:
        return jsonify({"error": "Refresh token revoked"}), 401
    for uname, u in USERS.items():
        if u["user_id"] == uid:
            return jsonify({"access_token": make_access_token(uid, uname, u["role"])})
    return jsonify({"error": "User not found"}), 404

@app.route("/protected")
@require_auth
def protected():
    return jsonify({"message": f"Hello {request.user['username']}!", "claims": request.user})

@app.route("/admin")
@require_role("admin")
def admin_only():
    return jsonify({"message": "Welcome to admin panel", "user": request.user["username"]})

# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def run_demo():
    print("=" * 60)
    print("JWT AUTHENTICATION DEMO")
    print("=" * 60)
    auth = lambda t: {"Authorization": f"Bearer {t}"}
    with app.test_client() as c:
        d = c.post("/login", json={"username": "alice", "password": "password123"}).get_json()
        tok, parts = d["access_token"], d["access_token"].split(".")
        print(f"\n1. Login alice  -> JWT: {parts[0][:15]}..{parts[1][:15]}..{parts[2][:15]}..")
        print(f"2. Protected   -> {c.get('/protected', headers=auth(tok)).get_json()['message']}")
        print(f"3. Admin       -> {c.get('/admin', headers=auth(tok)).get_json()['message']}")
        ct = c.post("/login", json={"username": "charlie", "password": "charliepass"}).get_json()
        r = c.get("/admin", headers=auth(ct["access_token"]))
        print(f"4. Viewer/admin -> {r.status_code} {r.get_json()['error']}")
        print(f"5. No token    -> {c.get('/protected').status_code} Unauthorized")
        r = c.get("/protected", headers=auth(tok[:-5] + "XXXXX"))
        print(f"6. Bad token   -> {r.status_code} {r.get_json()['error']}")
        r = c.post("/refresh", json={"refresh_token": d["refresh_token"]})
        print(f"7. Refresh     -> new token: {r.get_json()['access_token'][:30]}...")
    print(f"\nServer mode: python jwt_auth.py --serve")

if __name__ == "__main__":
    if "--serve" in sys.argv:
        print("JWT auth server running on http://localhost:5000")
        app.run(port=5000, debug=False)
    else:
        run_demo()
