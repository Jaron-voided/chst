"""AC-POS-4: compare two directory trees.

Usage: python3.14 -I tools/acceptance/tree_eq.py A B
Compares the set of paths, the entry types and the bytes of every file, and prints the differences.
Exit 0 if the trees are equal, 1 if they differ or either can't be read.

It walks both trees one directory handle at a time (os.scandir on a file descriptor, children opened
relative to it with dir_fd, never following a link), so paths longer than PATH_MAX work. Where
descriptors aren't supported (Windows), it falls back to extended-length path strings.
Standard library only.
"""

import os
import sys
from collections import deque

CHUNK = 1 << 20
USE_FD = os.scandir in os.supports_fd and os.open in os.supports_dir_fd


def die(msg):
    print(f"tree_eq.py: {msg}", file=sys.stderr)
    sys.exit(1)


def kind(entry):
    if entry.is_symlink():
        return "symlink"
    if entry.is_dir(follow_symlinks=False):
        return "dir"
    if entry.is_file(follow_symlinks=False):
        return "file"
    return "other"


class FdDir:
    """A directory held by an open descriptor."""

    def __init__(self, parent, name):
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        self.fd = os.open(name, flags, dir_fd=parent.fd) if parent else os.open(name, flags)

    def entries(self):
        with os.scandir(self.fd) as it:
            return {e.name: kind(e) for e in it}

    def child(self, name):
        return FdDir(self, name)

    def open_file(self, name):
        return os.open(name, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_BINARY", 0), dir_fd=self.fd)

    def close(self):
        os.close(self.fd)


class PathDir:
    """Fallback: a directory named by an extended-length path string."""

    def __init__(self, parent, name):
        path = name if parent is None else os.path.join(parent.path, name)
        if parent is None and os.name == "nt":
            path = "\\\\?\\" + os.path.abspath(path)
        self.path = path
        if not os.path.isdir(path) or os.path.islink(path):
            raise OSError(f"{path} isn't a directory")

    def entries(self):
        with os.scandir(self.path) as it:
            return {e.name: kind(e) for e in it}

    def child(self, name):
        return PathDir(self, name)

    def open_file(self, name):
        return os.open(os.path.join(self.path, name), os.O_RDONLY | getattr(os, "O_BINARY", 0))

    def close(self):
        pass


def same_bytes(da, db, name):
    fa, fb = da.open_file(name), db.open_file(name)
    try:
        while True:
            a, b = os.read(fa, CHUNK), os.read(fb, CHUNK)
            if a != b:
                return False
            if not a:
                return True
    finally:
        os.close(fa)
        os.close(fb)


def main():
    if len(sys.argv) != 3:
        die("usage: tree_eq.py A B")
    Dir = FdDir if USE_FD else PathDir
    try:
        roots = (Dir(None, sys.argv[1]), Dir(None, sys.argv[2]))
    except OSError as e:
        die(f"can't open a tree: {e}")

    diffs, count = [], 0
    queue = deque([(roots[0], roots[1], "")])
    while queue:
        da, db, rel = queue.popleft()
        try:
            ea, eb = da.entries(), db.entries()
            for name in sorted(set(ea) | set(eb)):
                path = f"{rel}{name}"
                count += 1
                if name not in eb:
                    diffs.append(f"only in A: {path}")
                elif name not in ea:
                    diffs.append(f"only in B: {path}")
                elif ea[name] != eb[name]:
                    diffs.append(f"type differs: {path} is {ea[name]} in A, {eb[name]} in B")
                elif ea[name] == "file":
                    if not same_bytes(da, db, name):
                        diffs.append(f"content differs: {path}")
                elif ea[name] == "dir":
                    queue.append((da.child(name), db.child(name), path + "/"))
        except OSError as e:
            diffs.append(f"can't read {rel or '.'}: {e}")
        finally:
            da.close()
            db.close()
    print(f"compared {count} entries")
    for d in diffs:
        print(d)
    return 1 if diffs else 0


if __name__ == "__main__":
    sys.exit(main())
