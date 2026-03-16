"""
OAuth 2.0 Authorization Code Flow
==================================
Simulates the full OAuth 2.0 authorization code flow with
auth server, client app, and resource server.

Run: python oauth_flow.py
"""

import secrets, time, json

# ---------------------------------------------------------------------------
# Authorization Server
# ---------------------------------------------------------------------------

class AuthServer:
    def __init__(self):
        self.clients = {
            "my-web-app": {
                "secret": "app-secret-xyz",
                "redirect_uri": "http://localhost:3000/callback",
                "name": "My Cool Web App",
            }
        }
        self.users = {
            "alice": {"password": "pass123", "name": "Alice Smith", "email": "alice@example.com"},
        }
        self.auth_codes = {}
        self.tokens = {}

    def login_and_consent(self, client_id, username, password, scope, state):
        client = self.clients.get(client_id)
        if not client:
            return {"error": "Unknown client"}
        user = self.users.get(username)
        if not user or user["password"] != password:
            return {"error": "Invalid credentials"}

        code = secrets.token_urlsafe(32)
        self.auth_codes[code] = {
            "client_id": client_id, "username": username,
            "scope": scope, "expires": time.time() + 600,
        }
        return {
            "code": code, "state": state,
            "redirect": f"{client['redirect_uri']}?code={code}&state={state}",
        }

    def exchange_code(self, client_id, client_secret, code):
        client = self.clients.get(client_id)
        if not client or client["secret"] != client_secret:
            return {"error": "Invalid client credentials"}
        data = self.auth_codes.pop(code, None)
        if not data or data["client_id"] != client_id:
            return {"error": "Invalid or expired code"}

        access_token = secrets.token_urlsafe(32)
        self.tokens[access_token] = {
            "username": data["username"], "scope": data["scope"],
            "expires": time.time() + 3600,
        }
        return {"access_token": access_token, "token_type": "Bearer", "expires_in": 3600}

    def validate(self, token):
        data = self.tokens.get(token)
        if not data:
            return None
        if time.time() > data["expires"]:
            return None
        return data

# ---------------------------------------------------------------------------
# Resource Server
# ---------------------------------------------------------------------------

class ResourceServer:
    def __init__(self, auth):
        self.auth = auth

    def get_profile(self, access_token):
        data = self.auth.validate(access_token)
        if not data:
            return {"error": "401 Unauthorized"}
        user = self.auth.users[data["username"]]
        scopes = data["scope"].split()
        result = {}
        if "profile" in scopes:
            result["name"] = user["name"]
        if "email" in scopes:
            result["email"] = user["email"]
        return {"status": "200 OK", "data": result}

# ---------------------------------------------------------------------------
# Client App
# ---------------------------------------------------------------------------

class ClientApp:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.secret = client_secret
        self.state = None
        self.token = None

    def start_login(self):
        self.state = secrets.token_urlsafe(16)
        return {"url": f"https://auth.example.com/authorize?client_id={self.client_id}&state={self.state}"}

    def handle_callback(self, code, state, auth):
        if state != self.state:
            return {"error": "State mismatch - possible CSRF attack!"}
        resp = auth.exchange_code(self.client_id, self.secret, code)
        if "error" not in resp:
            self.token = resp["access_token"]
        return resp

# ---------------------------------------------------------------------------
# Full flow demo
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("OAUTH 2.0 AUTHORIZATION CODE FLOW")
    print("=" * 60)

    auth = AuthServer()
    resource = ResourceServer(auth)
    client = ClientApp("my-web-app", "app-secret-xyz")

    print("\nStep 1: User clicks 'Login with Example'")
    start = client.start_login()
    print(f"   Redirect to: {start['url'][:60]}...")

    print("\nStep 2: User logs in and grants consent")
    auth_resp = auth.login_and_consent("my-web-app", "alice", "pass123", "profile email", client.state)
    print(f"   Auth code: {auth_resp['code'][:25]}...")

    print("\nStep 3: Client exchanges code for token (server-to-server)")
    token_resp = client.handle_callback(auth_resp["code"], auth_resp["state"], auth)
    print(f"   Access token: {token_resp['access_token'][:25]}...")
    print(f"   Expires in:   {token_resp['expires_in']}s")

    print("\nStep 4: Client fetches user profile")
    profile = resource.get_profile(client.token)
    print(f"   {json.dumps(profile['data'], indent=6)}")

    print("\n" + "-" * 60)
    print("SECURITY CHECKS")
    print("-" * 60)

    print("\n  Invalid token:  ", resource.get_profile("fake-token")["error"])
    print("  Code replay:    ", auth.exchange_code("my-web-app", "app-secret-xyz", auth_resp["code"])["error"])
    print("  CSRF (bad state):", client.handle_callback("x", "wrong", auth)["error"])
    print("  Wrong secret:   ", auth.exchange_code("my-web-app", "wrong", "x")["error"])

    print("\n" + "=" * 60)
    print("All security checks caught the attack.")
    print("=" * 60)

if __name__ == "__main__":
    main()
