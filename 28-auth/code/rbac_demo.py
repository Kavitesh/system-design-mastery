"""
Role-Based Access Control (RBAC)
================================
Demonstrates RBAC with users, roles, permissions,
and an audit log of every access decision.

Run: python rbac_demo.py
"""

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Permission:
    resource: str
    action: str
    def __str__(self):
        return f"{self.resource}:{self.action}"

@dataclass
class Role:
    name: str
    permissions: set = field(default_factory=set)

    def grant(self, resource, action):
        self.permissions.add(Permission(resource, action))

    def can(self, resource, action):
        return Permission(resource, action) in self.permissions

@dataclass
class User:
    username: str
    roles: list = field(default_factory=list)

    def add_role(self, role):
        if role not in self.roles:
            self.roles.append(role)

    def remove_role(self, name):
        self.roles = [r for r in self.roles if r.name != name]

    def can(self, resource, action):
        return any(r.can(resource, action) for r in self.roles)

    def all_permissions(self):
        perms = set()
        for r in self.roles:
            perms.update(r.permissions)
        return perms

# ---------------------------------------------------------------------------
# RBAC engine with audit log
# ---------------------------------------------------------------------------

class RBACEngine:
    def __init__(self):
        self.roles, self.users, self.log = {}, {}, []

    def create_role(self, name, perms):
        role = Role(name)
        for res, act in perms:
            role.grant(res, act)
        self.roles[name] = role
        return role

    def create_user(self, username, role_names):
        user = User(username)
        for rn in role_names:
            if rn in self.roles:
                user.add_role(self.roles[rn])
        self.users[username] = user
        return user

    def check(self, username, resource, action):
        user = self.users.get(username)
        granted = user.can(resource, action) if user else False
        self.log.append({"user": username, "target": f"{resource}:{action}", "granted": granted})
        return granted

# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("ROLE-BASED ACCESS CONTROL (RBAC)")
    print("=" * 60)

    e = RBACEngine()

    print("\n--- Roles ---\n")
    e.create_role("admin", [
        ("users", "read"), ("users", "write"), ("users", "delete"),
        ("articles", "read"), ("articles", "write"), ("articles", "delete"),
        ("settings", "read"), ("settings", "write"),
    ])
    e.create_role("editor", [
        ("articles", "read"), ("articles", "write"), ("users", "read"),
    ])
    e.create_role("viewer", [("articles", "read"), ("users", "read")])

    for name, role in e.roles.items():
        print(f"  {name:8s} -> {', '.join(sorted(str(p) for p in role.permissions))}")

    print("\n--- Users ---\n")
    e.create_user("alice", ["admin"])
    e.create_user("bob", ["editor"])
    e.create_user("charlie", ["viewer"])
    e.create_user("diana", [])

    for uname, user in e.users.items():
        roles = ", ".join(r.name for r in user.roles) or "(none)"
        print(f"  {uname:10s} -> {roles}")

    print("\n--- Access Checks ---\n")
    checks = [
        ("alice",   "users",    "delete",  "Admin deletes user"),
        ("bob",     "articles", "write",   "Editor writes article"),
        ("bob",     "articles", "delete",  "Editor deletes article"),
        ("charlie", "articles", "read",    "Viewer reads article"),
        ("charlie", "settings", "read",    "Viewer reads settings"),
        ("diana",   "articles", "read",    "No-role reads article"),
    ]
    for user, res, act, desc in checks:
        ok = e.check(user, res, act)
        tag = "GRANTED" if ok else "DENIED "
        print(f"  [{tag}] {desc:30s}  ({user} -> {res}:{act})")

    print("\n--- Dynamic Role Change ---\n")
    print("  Promoting charlie to editor...")
    e.users["charlie"].add_role(e.roles["editor"])
    ok = e.check("charlie", "articles", "write")
    print(f"  Charlie can write now: {ok}")

    print("\n  Revoking bob's editor role...")
    e.users["bob"].remove_role("editor")
    ok = e.check("bob", "articles", "write")
    print(f"  Bob can write now: {ok}")

    print("\n--- Effective Permissions ---\n")
    for uname, user in e.users.items():
        perms = sorted(str(p) for p in user.all_permissions()) or ["(none)"]
        print(f"  {uname}: {', '.join(perms)}")

    print(f"\n--- Audit Log ({len(e.log)} entries) ---\n")
    for entry in e.log:
        tag = "OK" if entry["granted"] else "NO"
        print(f"  [{tag}] {entry['user']:10s} -> {entry['target']}")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
