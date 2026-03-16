"""
File Sync Engine
================
Detects local file changes, syncs with a remote server, and resolves
conflicts using fork-on-conflict (Dropbox-style).

    python sync_engine.py
"""

import hashlib, time
from dataclasses import dataclass
from enum import Enum

# ---------------------------------------------------------------------------

class Change(Enum):
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    UNCHANGED = "unchanged"

@dataclass
class FileState:
    path: str
    content: bytes
    checksum: str
    version: int

    @staticmethod
    def make(path, content, version=1):
        return FileState(path, content, hashlib.sha256(content).hexdigest()[:12], version)

# ---------------------------------------------------------------------------

class Server:
    def __init__(self):
        self.files: dict[str, FileState] = {}

    def get(self, path): return self.files.get(path)

    def put(self, state, client):
        state.version = self.files[state.path].version + 1 if state.path in self.files else 1
        self.files[state.path] = state
        return state

    def delete(self, path):
        self.files.pop(path, None)

# ---------------------------------------------------------------------------

class SyncClient:
    def __init__(self, name, server):
        self.name, self.server = name, server
        self.local: dict[str, FileState] = {}
        self.synced: dict[str, str] = {}

    def add(self, path, content):    self.local[path] = FileState.make(path, content)
    def edit(self, path, content):   self.local[path] = FileState.make(path, content, self.local[path].version)
    def remove(self, path):          self.local.pop(path, None)

    def detect(self):
        changes = []
        for path in sorted(set(self.local) | set(self.synced)):
            loc = self.local.get(path)
            prev = self.synced.get(path)
            if loc and not prev:         changes.append((path, Change.CREATED))
            elif not loc and prev:       changes.append((path, Change.DELETED))
            elif loc and prev and loc.checksum != prev: changes.append((path, Change.MODIFIED))
            else:                        changes.append((path, Change.UNCHANGED))
        return changes

    def sync(self):
        results = []
        for path, change in self.detect():
            remote = self.server.get(path)
            if change == Change.UNCHANGED:
                if remote and remote.checksum != self.synced.get(path):
                    self.local[path] = remote
                    self.synced[path] = remote.checksum
                    results.append(f"[PULL    ] {path} - updated from server v{remote.version}")
            elif change == Change.CREATED:
                if remote:
                    results.extend(self._conflict(path))
                else:
                    u = self.server.put(self.local[path], self.name)
                    self.local[path], self.synced[path] = u, u.checksum
                    results.append(f"[PUSH    ] {path} - uploaded v{u.version}")
            elif change == Change.MODIFIED:
                if remote and remote.checksum != self.synced.get(path):
                    results.extend(self._conflict(path))
                else:
                    u = self.server.put(self.local[path], self.name)
                    self.local[path], self.synced[path] = u, u.checksum
                    results.append(f"[PUSH    ] {path} - pushed v{u.version}")
            elif change == Change.DELETED:
                if remote and remote.checksum != self.synced.get(path):
                    self.local[path] = remote
                    self.synced[path] = remote.checksum
                    results.append(f"[PULL    ] {path} - server had updates, restored")
                else:
                    self.server.delete(path)
                    self.synced.pop(path, None)
                    results.append(f"[DELETE  ] {path} - removed from server")
        return results

    def _conflict(self, path):
        remote, local = self.server.get(path), self.local[path]
        base, ext = (path.rsplit(".", 1) if "." in path else (path, ""))
        cp = f"{base} (conflict-{self.name}).{ext}" if ext else f"{base} (conflict-{self.name})"
        self.local[path], self.synced[path] = remote, remote.checksum
        cs = self.server.put(FileState.make(cp, local.content), self.name)
        self.local[cp], self.synced[cp] = cs, cs.checksum
        return [f"[CONFLICT] {path} - server version wins (v{remote.version})",
                f"[CONFLICT] {cp} - local saved as conflict copy"]

    def pull_all(self):
        for path, state in self.server.files.items():
            self.local[path] = state
            self.synced[path] = state.checksum

# ---------------------------------------------------------------------------

def pr(name, results):
    for r in results: print(f"  {name}: {r}")

def demo_basic():
    print("=" * 60); print("DEMO 1: Two-client sync"); print("=" * 60)
    srv = Server(); a, b = SyncClient("Alice", srv), SyncClient("Bob", srv)
    a.add("notes.txt", b"Meeting notes"); a.add("todo.txt", b"Buy groceries")
    print("\nAlice uploads:"); pr("Alice", a.sync())
    b.pull_all(); print(f"\nBob pulled {len(b.local)} files")
    a.edit("notes.txt", b"Meeting notes - UPDATED")
    print("\nAlice edits:"); pr("Alice", a.sync())
    print("Bob syncs:"); pr("Bob", b.sync())

def demo_conflict():
    print("\n" + "=" * 60); print("DEMO 2: Conflict resolution"); print("=" * 60)
    srv = Server(); a, b = SyncClient("Alice", srv), SyncClient("Bob", srv)
    a.add("report.docx", b"Draft report"); a.sync(); b.pull_all()
    a.edit("report.docx", b"Alice's revenue figures")
    b.edit("report.docx", b"Bob's expense analysis")
    print("\nAlice first:"); pr("Alice", a.sync())
    print("Bob conflict:"); pr("Bob", b.sync())
    print("\nServer files:", sorted(srv.files.keys()))

def demo_delete():
    print("\n" + "=" * 60); print("DEMO 3: Delete propagation"); print("=" * 60)
    srv = Server(); a, b = SyncClient("Alice", srv), SyncClient("Bob", srv)
    a.add("draft.txt", b"old"); a.add("shared.txt", b"shared"); a.sync(); b.pull_all()
    a.remove("draft.txt")
    print("\nAlice deletes:"); pr("Alice", a.sync())
    print("Bob syncs:"); pr("Bob", b.sync())
    print(f"Bob's files: {sorted(b.local.keys())}")

def demo_detection():
    print("\n" + "=" * 60); print("DEMO 4: Change detection"); print("=" * 60)
    srv = Server(); c = SyncClient("Desktop", srv)
    c.add("a.txt", b"A"); c.add("b.txt", b"B"); c.add("c.txt", b"C"); c.sync()
    c.edit("a.txt", b"A!"); c.add("d.txt", b"D"); c.remove("c.txt")
    for p, ch in c.detect(): print(f"  {p:10s} -> {ch.value}")
    print(); pr("Desktop", c.sync())

# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("File Sync Engine Demo\n")
    demo_basic(); demo_conflict(); demo_delete(); demo_detection()
    print("\nDone.")
