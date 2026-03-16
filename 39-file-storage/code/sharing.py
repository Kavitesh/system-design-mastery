"""
File Sharing and Permissions
============================
Sharing with viewer/editor/owner permission levels, link sharing,
folder permission inheritance, and access control checks.

    python sharing.py
"""

import secrets, time
from dataclasses import dataclass
from enum import IntEnum

# ---------------------------------------------------------------------------

class Perm(IntEnum):
    NONE = 0; VIEWER = 1; EDITOR = 2; OWNER = 3
    def can_read(self):   return self >= Perm.VIEWER
    def can_write(self):  return self >= Perm.EDITOR
    def can_share(self):  return self >= Perm.EDITOR
    def can_delete(self): return self >= Perm.OWNER

PNAME = {Perm.NONE: "none", Perm.VIEWER: "viewer", Perm.EDITOR: "editor", Perm.OWNER: "owner"}

@dataclass
class FileNode:
    fid: str; name: str; owner: str; parent: str = None; is_folder: bool = False

@dataclass
class ShareLink:
    token: str; fid: str; perm: Perm; expires: float = None
    @property
    def expired(self): return self.expires and time.time() > self.expires

# ---------------------------------------------------------------------------

class SharingService:
    def __init__(self):
        self.files, self.users, self.perms = {}, {}, {}
        self.links, self.log = {}, []

    def add_user(self, uid, email):  self.users[uid] = email
    def add_file(self, fid, name, owner, parent=None, folder=False):
        self.files[fid] = FileNode(fid, name, owner, parent, folder)
        self.perms[(fid, owner)] = Perm.OWNER

    def effective_perm(self, fid, uid):
        direct = self.perms.get((fid, uid), Perm.NONE)
        if direct > Perm.NONE: return direct
        node = self.files.get(fid)
        if node and node.parent: return self.effective_perm(node.parent, uid)
        return Perm.NONE

    def share(self, fid, grantor, grantee, perm):
        gp = self.effective_perm(fid, grantor)
        if not gp.can_share(): return {"error": f"{grantor} can't share"}
        if perm > gp: return {"error": f"Can't grant {PNAME[perm]} (you have {PNAME[gp]})"}
        self.perms[(fid, grantee)] = perm
        self.log.append({"action": "share", "file": fid, "to": grantee, "perm": PNAME[perm]})
        return {"shared": self.files[fid].name, "with": self.users[grantee], "as": PNAME[perm]}

    def revoke(self, fid, revoker, target):
        if not self.effective_perm(fid, revoker).can_share(): return {"error": "can't revoke"}
        if (fid, target) in self.perms:
            del self.perms[(fid, target)]
            self.log.append({"action": "revoke", "file": fid, "target": target})
            return {"revoked": target}
        return {"error": "no permission found"}

    def create_link(self, fid, creator, perm=Perm.VIEWER, ttl=None):
        if not self.effective_perm(fid, creator).can_share(): return {"error": "can't share"}
        token = secrets.token_urlsafe(12)
        self.links[token] = ShareLink(token, fid, perm, time.time() + ttl if ttl else None)
        return {"url": f"https://drive.example.com/s/{token}", "perm": PNAME[perm],
                "expires": f"{ttl}s" if ttl else "never"}

    def use_link(self, token, uid):
        link = self.links.get(token)
        if not link: return {"error": "invalid link"}
        if link.expired: return {"error": "link expired"}
        self.perms[(link.fid, uid)] = link.perm
        return {"granted": PNAME[link.perm], "file": self.files[link.fid].name}

    def check(self, fid, uid, op):
        p = self.effective_perm(fid, uid)
        allowed = {"read": p.can_read(), "write": p.can_write(), "delete": p.can_delete()}[op]
        return f"{self.users.get(uid,'?'):25s} {op:8s} -> {'YES' if allowed else 'NO'} ({PNAME[p]})"

# ---------------------------------------------------------------------------

def demo_basic():
    print("=" * 60); print("DEMO 1: Permission levels"); print("=" * 60)
    s = SharingService()
    for u, e in [("alice","alice@co.com"),("bob","bob@co.com"),("carol","carol@co.com")]: s.add_user(u, e)
    s.add_file("d1", "Q4_report.xlsx", "alice")
    print(f"\n  Share with Bob (editor): {s.share('d1','alice','bob', Perm.EDITOR)}")
    print(f"  Share with Carol (viewer): {s.share('d1','alice','carol', Perm.VIEWER)}")
    print("\n  Access matrix:")
    for uid in ["alice","bob","carol"]:
        for op in ["read","write","delete"]:
            print(f"    {s.check('d1', uid, op)}")
    print(f"\n  Carol tries to share: {s.share('d1','carol','bob', Perm.VIEWER)}")

def demo_inheritance():
    print("\n" + "=" * 60); print("DEMO 2: Folder permission inheritance"); print("=" * 60)
    s = SharingService()
    s.add_user("alice","alice@co.com"); s.add_user("bob","bob@co.com")
    s.add_file("f1", "Project X/", "alice", folder=True)
    s.add_file("d1", "spec.pdf", "alice", parent="f1")
    s.add_file("d2", "design.fig", "alice", parent="f1")
    print(f"\n  Share folder with Bob: {s.share('f1','alice','bob', Perm.EDITOR)}")
    print("  Inherited access to children:")
    for fid, name in [("d1","spec.pdf"),("d2","design.fig")]:
        print(f"    {name}: {PNAME[s.effective_perm(fid, 'bob')]} (inherited)")
    print(f"    Bob writes spec.pdf: {s.check('d1','bob','write')}")
    print(f"    Bob deletes spec.pdf: {s.check('d1','bob','delete')}")

def demo_links():
    print("\n" + "=" * 60); print("DEMO 3: Share links"); print("=" * 60)
    s = SharingService()
    s.add_user("alice","alice@co.com"); s.add_user("dave","dave@ext.com")
    s.add_file("d1", "slides.pptx", "alice")
    link = s.create_link("d1", "alice", Perm.VIEWER)
    print(f"\n  Created: {link}")
    token = list(s.links.keys())[0]
    print(f"  Dave uses link: {s.use_link(token, 'dave')}")
    print(f"  Dave reads: {s.check('d1','dave','read')}")
    print(f"  Dave writes: {s.check('d1','dave','write')}")
    expired = s.create_link("d1", "alice", Perm.EDITOR, ttl=0)
    print(f"\n  Expiring link: {expired}")
    time.sleep(0.01)
    et = list(s.links.keys())[-1]
    print(f"  After expiry: {s.use_link(et, 'dave')}")

def demo_revoke():
    print("\n" + "=" * 60); print("DEMO 4: Revoke and audit"); print("=" * 60)
    s = SharingService()
    s.add_user("alice","alice@co.com"); s.add_user("bob","bob@co.com")
    s.add_file("d1", "budget.xlsx", "alice")
    s.share("d1", "alice", "bob", Perm.EDITOR)
    print(f"\n  Bob reads: {s.check('d1','bob','read')}")
    print(f"  Revoke: {s.revoke('d1','alice','bob')}")
    print(f"  Bob reads: {s.check('d1','bob','read')}")
    print(f"\n  Audit log:")
    for e in s.log: print(f"    {e}")

# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("File Sharing and Permissions Demo\n")
    demo_basic(); demo_inheritance(); demo_links(); demo_revoke()
    print("\nDone.")
