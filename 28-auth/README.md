# Chapter 28 - Authentication & Authorization

> You can build the most scalable system on earth, but if anyone can walk through the front door pretending to be someone else, none of it matters.

📖 [Read on Medium](#) · 🎬 [Watch on YouTube](#)

---

## Authentication vs Authorization

These two words get swapped constantly, even by senior engineers. They're different things.

**Authentication** (AuthN) answers: *"Who are you?"*
**Authorization** (AuthZ) answers: *"What are you allowed to do?"*

```
Request comes in
       │
       ▼
┌──────────────┐     ┌──────────────┐
│ Authentication│────▶│ Authorization │────▶ Access Granted
│  "Who is this?"│     │ "Can they do  │
│               │     │   this?"      │
└──────────────┘     └──────────────┘
       │                    │
       ▼                    ▼
   401 Unauthorized     403 Forbidden
   (unknown user)     (known but denied)
```

Authentication always comes first. You can't decide what someone is allowed to do until you know who they are.

| Aspect | Authentication | Authorization |
|--------|---------------|---------------|
| Question | Who are you? | What can you do? |
| HTTP error | 401 Unauthorized | 403 Forbidden |
| Mechanism | Passwords, tokens, biometrics | Roles, permissions, policies |
| Visibility | Usually visible to user (login form) | Usually invisible to user |
| Changes | When user updates credentials | When admin updates permissions |

---

## Password Storage - Getting It Right

Storing passwords is the first place teams get it wrong. Here's the progression from terrible to correct.

### The Hall of Shame

```
Level 0: Plaintext          → "password123"           (instant breach)
Level 1: Simple hash        → MD5("password123")      (rainbow table in seconds)
Level 2: Hash + salt        → MD5(salt + "password123") (faster than you think)
Level 3: bcrypt/scrypt/argon2 → slow by design         (correct answer)
```

**Why bcrypt, scrypt, and argon2 win:** They're intentionally slow. MD5 can hash billions of passwords per second on a modern GPU. bcrypt is tunable - you set a "work factor" that controls how many iterations it runs. A work factor of 12 means roughly 250ms per hash. That's nothing for a single login, but it makes brute-forcing billions of passwords take centuries.

| Algorithm | Speed (hashes/sec on GPU) | Status |
|-----------|---------------------------|--------|
| MD5 | ~60 billion | Broken. Never use for passwords |
| SHA-256 | ~20 billion | Not designed for passwords |
| bcrypt | ~25,000 | Good - widely supported |
| scrypt | ~10,000 | Better - also memory-hard |
| Argon2 | ~5,000 | Best - won Password Hashing Competition (2015) |

The key insight: general-purpose hash functions are designed to be *fast*. Password hashing functions are designed to be *slow*. Those are opposite goals.

---

## Session-Based Authentication

The traditional approach. The server keeps track of who's logged in.

```
┌────────┐                           ┌────────┐
│ Client │                           │ Server │
└───┬────┘                           └───┬────┘
    │  1. POST /login                    │
    │     {user, password}               │
    │──────────────────────────────────▶│
    │                                    │ 2. Validate credentials
    │                                    │ 3. Create session in store
    │                                    │    session_id → {user_id, role}
    │  4. Set-Cookie: session_id=abc123  │
    │◀──────────────────────────────────│
    │                                    │
    │  5. GET /dashboard                 │
    │     Cookie: session_id=abc123      │
    │──────────────────────────────────▶│
    │                                    │ 6. Look up session in store
    │                                    │ 7. Return user-specific data
    │  8. 200 OK {dashboard data}        │
    │◀──────────────────────────────────│
```

**Session store options:** In-memory (dies with the server), Redis (fast, shared), database (persistent but slower).

**The scaling problem:** Sessions live on the server. If you have 10 servers behind a load balancer, server #3 has your session but server #7 doesn't. You either need sticky sessions (defeats the purpose of load balancing) or a shared session store like Redis.

| Pros | Cons |
|------|------|
| Simple mental model | Server must store state |
| Easy to revoke (delete session) | Harder to scale horizontally |
| Cookie-based, browser handles it | CSRF vulnerability if not careful |
| Server controls session lifetime | Requires shared store in distributed setups |

---

## Token-Based Authentication (JWT)

The modern approach for APIs and SPAs. The server issues a signed token instead of storing sessions.

### JWT Structure

A JWT has three parts, separated by dots: `header.payload.signature`

```
eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjo0Miwicm9sZSI6ImFkbWluIn0.SflKxwRJSMeKKF2QT4fwpM

┌──────────────────────┐
│ Header (Base64)      │  {"alg": "HS256", "typ": "JWT"}
├──────────────────────┤
│ Payload (Base64)     │  {"user_id": 42, "role": "admin", "exp": 1700000000}
├──────────────────────┤
│ Signature            │  HMAC-SHA256(header + "." + payload, secret_key)
└──────────────────────┘
```

The payload is **not encrypted** - it's just Base64 encoded. Anyone can decode it and read the claims. The signature only guarantees the data hasn't been tampered with.

### Token Flow

```
┌────────┐                           ┌────────┐
│ Client │                           │ Server │
└───┬────┘                           └───┬────┘
    │  1. POST /login                    │
    │     {user, password}               │
    │──────────────────────────────────▶│
    │                                    │ 2. Validate credentials
    │                                    │ 3. Create JWT (signed, NOT stored)
    │  4. {"token": "eyJhbGci..."}       │
    │◀──────────────────────────────────│
    │                                    │
    │  5. GET /api/data                  │
    │     Authorization: Bearer eyJhbGci │
    │──────────────────────────────────▶│
    │                                    │ 6. Verify signature
    │                                    │ 7. Read claims from payload
    │  8. 200 OK {data}                  │
    │◀──────────────────────────────────│
```

**The key difference from sessions:** The server doesn't store anything. All the user info lives inside the token itself. That's why JWTs scale horizontally without a shared store.

### Token Refresh Flow

Short-lived access tokens + long-lived refresh tokens. This is how production systems work.

```
┌────────┐                           ┌────────┐
│ Client │                           │ Server │
└───┬────┘                           └───┬────┘
    │  1. POST /login                    │
    │──────────────────────────────────▶│
    │  2. access_token (15 min)          │
    │     refresh_token (7 days)         │
    │◀──────────────────────────────────│
    │                                    │
    │  ... access token expires ...      │
    │                                    │
    │  3. POST /refresh                  │
    │     {refresh_token}                │
    │──────────────────────────────────▶│
    │                                    │ 4. Validate refresh token
    │                                    │ 5. Issue new access token
    │  6. new access_token (15 min)      │
    │◀──────────────────────────────────│
```

Why not just make access tokens long-lived? Because if a token leaks, the damage window is only 15 minutes instead of 7 days. The refresh token is stored more securely (httpOnly cookie, not localStorage) and is only sent to one endpoint.

| Session-Based | Token-Based (JWT) |
|---------------|-------------------|
| State on server | State in token |
| Scale: need shared store | Scale: stateless, any server works |
| Revocation: delete session | Revocation: hard (token is valid until expiry) |
| Size: small cookie | Size: larger (contains claims) |
| CSRF risk | XSS risk (if stored in localStorage) |

---

## OAuth 2.0

OAuth 2.0 is a *delegation* protocol. It lets users grant third-party apps limited access to their resources without sharing passwords.

When you click "Sign in with Google" on some random app, that's OAuth. You're not giving the app your Google password. You're telling Google "yes, let this app see my email and profile photo."

### Authorization Code Flow (Most Common)

This is the flow used by web applications. It's the most secure because the client secret never hits the browser.

```
┌──────┐         ┌──────────┐         ┌───────────────┐         ┌──────────┐
│ User │         │ Your App │         │ Auth Server   │         │ Resource │
│      │         │ (Client) │         │ (Google/Auth0)│         │ Server   │
└──┬───┘         └────┬─────┘         └──────┬────────┘         └────┬─────┘
   │ 1. Click           │                     │                      │
   │ "Login with Google" │                     │                      │
   │──────────────────▶│                     │                      │
   │                     │ 2. Redirect to      │                      │
   │                     │ auth server         │                      │
   │◀─────────────────────────────────────────│                      │
   │                     │                     │                      │
   │ 3. User logs in     │                     │                      │
   │    and consents     │                     │                      │
   │──────────────────────────────────────────▶│                      │
   │                     │                     │                      │
   │ 4. Redirect back    │                     │                      │
   │    with auth code   │                     │                      │
   │──────────────────▶│                     │                      │
   │                     │ 5. Exchange code     │                      │
   │                     │    for token         │                      │
   │                     │    (server-to-server)│                      │
   │                     │────────────────────▶│                      │
   │                     │                     │                      │
   │                     │ 6. Access token      │                      │
   │                     │◀────────────────────│                      │
   │                     │                     │                      │
   │                     │ 7. Use token to      │                      │
   │                     │    fetch user data   │                      │
   │                     │────────────────────────────────────────────▶│
   │                     │                     │                      │
   │                     │ 8. User data         │                      │
   │                     │◀────────────────────────────────────────────│
```

### Client Credentials Flow

Used for machine-to-machine communication. No user involved - one service talks to another.

```
┌──────────┐                    ┌───────────────┐
│ Service A│                    │ Auth Server   │
│ (Client) │                    │               │
└────┬─────┘                    └──────┬────────┘
     │ 1. POST /token                  │
     │    client_id + client_secret    │
     │────────────────────────────────▶│
     │                                 │
     │ 2. Access token                 │
     │◀────────────────────────────────│
     │                                 │
     │ 3. Call Service B with token    │
     │──────────────────────────────▶ Service B
```

### OAuth 2.0 Grant Types Summary

| Grant Type | Use Case | User Involved? |
|-----------|----------|----------------|
| Authorization Code | Web apps, server-side apps | Yes |
| Authorization Code + PKCE | SPAs, mobile apps | Yes |
| Client Credentials | Service-to-service | No |
| Device Code | Smart TVs, CLI tools | Yes (on separate device) |
| ~~Implicit~~ | ~~SPAs~~ | ~~Deprecated - use PKCE instead~~ |
| ~~Password~~ | ~~Trusted first-party apps~~ | ~~Deprecated - don't use~~ |

---

## OpenID Connect (OIDC)

OAuth 2.0 handles *authorization* - "can this app access my photos?" It doesn't actually handle *authentication* - "who is this user?"

OpenID Connect is a thin identity layer on top of OAuth 2.0. It adds an **ID token** (a JWT containing user identity claims) to the OAuth flow.

```
OAuth 2.0 alone:     You get an access_token → call APIs
OAuth 2.0 + OIDC:    You get an access_token + id_token → call APIs + know who the user is
```

The ID token contains standard claims:

```json
{
  "sub": "user-uuid-12345",
  "name": "Jane Doe",
  "email": "jane@example.com",
  "email_verified": true,
  "iss": "https://accounts.google.com",
  "aud": "your-app-client-id",
  "exp": 1700000000,
  "iat": 1699990000
}
```

This is why "Sign in with Google" can populate your profile automatically. The ID token carries the user's name, email, and profile photo URL.

---

## API Keys

API keys are the simplest form of authentication. They're just a long random string sent with each request.

```
GET /api/weather?city=Tokyo
X-API-Key: sk_live_abc123def456ghi789
```

**API keys are not user authentication.** They identify *applications*, not people. Stripe knows which merchant account is calling, but it doesn't know which employee clicked the button.

| Good For | Bad For |
|----------|---------|
| Identifying calling applications | Identifying individual users |
| Rate limiting per client | Fine-grained permissions |
| Usage tracking and billing | Temporary/scoped access |
| Simple server-to-server auth | Browser-based apps (keys get exposed) |

---

## Role-Based Access Control (RBAC)

RBAC assigns permissions to *roles*, then assigns roles to *users*. Users don't get permissions directly.

```
┌───────────┐     ┌───────────┐     ┌──────────────┐
│   Users   │────▶│   Roles   │────▶│ Permissions  │
└───────────┘     └───────────┘     └──────────────┘

 Alice ──────────▶ admin ──────────▶ read, write, delete, manage_users
 Bob ────────────▶ editor ─────────▶ read, write
 Charlie ────────▶ viewer ─────────▶ read
```

This is the model used by AWS IAM, GitHub organizations, and most SaaS platforms. It works well when permissions map cleanly to job functions.

| Advantage | Limitation |
|-----------|------------|
| Simple to understand | Doesn't handle contextual rules |
| Easy to audit ("who has admin?") | Role explosion in complex orgs |
| Fast permission checks | Can't express "own resources only" |
| Matches org structure | All-or-nothing per role |

---

## Attribute-Based Access Control (ABAC)

ABAC evaluates policies based on *attributes* of the user, resource, action, and environment. It's more flexible than RBAC but more complex to implement.

```
Policy: ALLOW if
  user.department == "engineering" AND
  resource.classification != "top-secret" AND
  action == "read" AND
  environment.time_of_day BETWEEN 09:00 AND 18:00
```

**When to use ABAC over RBAC:**
- "Users can only edit their own documents" (RBAC can't express ownership)
- "Access allowed only from corporate network" (contextual)
- "Managers can approve expenses under $10,000" (attribute threshold)
- "Only the EU team can access EU customer data" (data residency)

In practice, most systems use RBAC as the foundation and layer ABAC-style rules on top for specific cases.

---

## Single Sign-On (SSO)

SSO lets users log in once and access multiple applications without re-entering credentials.

```
┌──────┐     ┌─────────────────┐
│ User │     │  Identity       │
│      │     │  Provider (IdP) │
└──┬───┘     │  (Okta, Auth0)  │
   │         └────────┬────────┘
   │                  │
   │ Already logged   │
   │ in to IdP        │
   │                  │
   ├──▶ App A ────────┤  "Is this user authenticated?" → Yes → Access granted
   │                  │
   ├──▶ App B ────────┤  "Is this user authenticated?" → Yes → Access granted
   │                  │
   └──▶ App C ────────┘  "Is this user authenticated?" → Yes → Access granted
```

**Protocols for SSO:**
- **SAML 2.0** - XML-based, enterprise standard. Used by Okta, Azure AD. Older but everywhere in corporate environments.
- **OIDC** - JSON/JWT-based, modern. Used by Google, Auth0. Lighter and better for web/mobile apps.

| SAML 2.0 | OIDC |
|----------|------|
| XML tokens | JWT tokens |
| Enterprise-focused | Web/mobile-focused |
| Heavier, more verbose | Lighter, easier to implement |
| Mature ecosystem | Growing ecosystem |
| Browser redirects | Browser redirects + API calls |

---

## Multi-Factor Authentication (MFA)

MFA requires two or more independent factors to verify identity.

| Factor Type | What It Means | Examples |
|-------------|---------------|----------|
| Something you **know** | Secret knowledge | Password, PIN, security question |
| Something you **have** | Physical possession | Phone (TOTP app), hardware key (YubiKey), SMS code |
| Something you **are** | Biometric | Fingerprint, face scan, voice |

**The strength hierarchy of second factors:**

```
Weakest ──────────────────────────────── Strongest
SMS codes → Email codes → TOTP apps → Push notifications → Hardware keys
(SIM swap   (email       (Google       (Duo, MS            (YubiKey,
 attacks)    compromise)  Authenticator) Authenticator)      FIDO2)
```

SMS-based MFA is better than no MFA, but it's the weakest option. SIM-swap attacks are trivial for motivated attackers. TOTP (Time-based One-Time Password) apps like Google Authenticator generate codes locally on the device, making them immune to interception. Hardware security keys using FIDO2/WebAuthn are the gold standard - they're phishing-resistant because they bind to the domain.

---

## Real-World Auth Architectures

### Google's Auth Stack

```
User → Google Sign-In (OIDC) → Google Identity Platform
                                    │
                              ┌─────┴─────┐
                              │ OAuth 2.0  │
                              │ tokens     │
                              └─────┬─────┘
                                    │
                         ┌──────────┼──────────┐
                         ▼          ▼          ▼
                      Gmail    Google     YouTube
                               Drive
```

Google uses OIDC for user-facing auth and OAuth 2.0 for API access. Internally, services use mTLS (mutual TLS) and Google's BeyondCorp zero-trust framework - no VPN needed, every request is authenticated individually.

### Typical SaaS Architecture

```
┌─────────────────────────────────────────────────────┐
│                   API Gateway                        │
│                                                      │
│  1. Extract JWT from Authorization header            │
│  2. Verify signature                                 │
│  3. Check expiration                                 │
│  4. Attach user context to request                   │
│  5. Forward to microservice                          │
└──────────────────────┬──────────────────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
     User Service  Order Service  Payment Service
     (checks RBAC)  (checks RBAC)  (checks RBAC + ABAC)
```

The API gateway handles authentication. Individual services handle authorization. This separation keeps auth logic centralized while letting each service enforce its own access rules.

---

## Common Pitfalls

| Pitfall | Why It's Dangerous | Fix |
|---------|--------------------|-----|
| Storing passwords in plaintext | One breach exposes all users | Use bcrypt/argon2 with salt |
| JWTs in localStorage | XSS attack steals all tokens | Use httpOnly cookies |
| Long-lived access tokens | Leaked token works for months | Short-lived tokens + refresh flow |
| Not validating JWT signature | Attacker can forge tokens | Always verify signature server-side |
| Hardcoded API keys in source | Keys end up in git history | Use environment variables, rotate keys |
| Rolling your own crypto | You will get it wrong | Use established libraries (PyJWT, bcrypt) |
| No rate limiting on login | Brute force attacks succeed | Rate limit + account lockout + MFA |
| Implicit OAuth flow | Token exposed in URL fragment | Use Authorization Code + PKCE |
| Same secret for all JWTs | One leak compromises everything | Rotate secrets, use asymmetric keys (RS256) |
| Checking permissions client-side only | Attacker bypasses UI | Always enforce on the server |

---

## Key Takeaways

1. **Authentication proves identity, authorization checks permissions** - they're separate concerns and should be implemented separately
2. **Never store passwords in plaintext or simple hashes** - use bcrypt, scrypt, or argon2 with a work factor that makes brute-forcing impractical
3. **JWTs trade revocability for scalability** - they're stateless (good for microservices) but you can't invalidate one before expiry without extra infrastructure
4. **OAuth 2.0 is delegation, not authentication** - add OpenID Connect when you need to know *who* the user is, not just *what* they can access
5. **RBAC covers 80% of use cases** - start with roles and permissions, add ABAC-style rules only when you need contextual or attribute-based decisions
6. **The API gateway should handle authentication, services handle authorization** - centralize identity verification, distribute access control
7. **MFA isn't optional for production systems** - hardware keys beat TOTP beat SMS, but any MFA beats none

---

## What's Next?

- **Chapter 29:** [Encryption & Data Security](../29-encryption/) - TLS, encryption at rest, key management, and protecting data in transit and storage
