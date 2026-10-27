"""AC-ROB-1: flip every byte of a container, one at a time, and run `chst verify` on each result.

Usage: python3.14 -I tools/acceptance/flip_sweep.py [--rehash] [--min-distinct N] CHST FILE...

For every byte offset, and for each of XOR 0x01 and XOR 0xFF, the mutated file is verified.
Plain mode asserts: the exit code is 4, 5, 6 or 7 (never 0, 70 or 101), stderr has no `panicked`,
and each run takes under 5 seconds. It prints a histogram of the detail codes.
--rehash mode (F13) recomputes the structure hash after each flip, so the damage reaches the
section, entry, path and canonical rules. It skips trailer bytes 16..47 (the hash itself). It
asserts: no exit 70 or 101 and no panic; at least --min-distinct distinct detail codes occur; and
exit 0 only for a flip that gives a different valid container, meaning a flip in minor_version, in
optional_flags, or in the path pool.
Exit 1 if an assertion fails, CHST can't be run, a FILE can't be read, or nothing was run.
Standard library only.
"""

import hashlib
import os
import re
import struct
import subprocess
import sys
import tempfile
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

TIMEOUT_S = 5
ERROR_LINE = re.compile(r"error\[([^/\]]+)/([^\]]+)\]")
PATH_POOL = 0x80000003


def die(msg):
    print(f"flip_sweep.py: {msg}", file=sys.stderr)
    sys.exit(1)


def run_verify(chst, path):
    """Returns (exit code, stderr text, seconds), or raises OSError / TimeoutExpired."""
    start = time.monotonic()
    p = subprocess.run([chst, "verify", path], capture_output=True, timeout=TIMEOUT_S)
    return p.returncode, p.stderr.decode("utf-8", "replace"), time.monotonic() - start


def path_pool_range(data):
    """The byte range of the PATH_POOL payload, parsed straight from FORMAT_SPEC sections 5 and 6."""
    index_offset, index_length = struct.unpack_from("<QQ", data, len(data) - 56)
    pos, end = index_offset, index_offset + index_length
    while pos + 16 <= end:
        typ, rec_size, count = struct.unpack_from("<IIQ", data, pos)
        size = rec_size * count
        if typ == PATH_POOL:
            return pos + 16, pos + 16 + size
        pos += 16 + size
    die("the file has no PATH_POOL section")


def rehash(buf):
    """Recompute the structure hash in place: SHA-256 over header, index, trailer[0..16)."""
    t = len(buf) - 56
    index_offset, index_length = struct.unpack_from("<QQ", buf, t)
    h = hashlib.sha256(bytes(buf[:32]) + bytes(buf[index_offset:index_offset + index_length]) + bytes(buf[t:t + 16]))
    buf[t + 16:t + 48] = h.digest()


def main():
    args = sys.argv[1:]
    do_rehash, min_distinct = False, 0
    while args and args[0].startswith("--"):
        if args[0] == "--rehash":
            do_rehash = True
            args = args[1:]
        elif args[0] == "--min-distinct" and len(args) > 1 and args[1].isdigit():
            min_distinct = int(args[1])
            args = args[2:]
        else:
            die(f"unknown option {args[0]}")
    if len(args) < 2:
        die("usage: flip_sweep.py [--rehash] [--min-distinct N] CHST FILE...")
    chst, files = args[0], args[1:]
    if not os.path.isfile(chst) or not os.access(chst, os.X_OK):
        die(f"can't find an executable CHST at {chst}")

    problems, details, runs = [], Counter(), 0
    with tempfile.TemporaryDirectory() as tmp:
        for f in files:
            try:
                with open(f, "rb") as fh:
                    orig = fh.read()
            except OSError as e:
                die(f"can't read {f}: {e}")
            if len(orig) < 88:
                die(f"{f} is too short to be a container")
            pool = path_pool_range(orig) if do_rehash else (0, 0)
            try:
                base = os.path.join(tmp, "base.chst")
                with open(base, "wb") as fh:
                    fh.write(orig)
                rc, err, _ = run_verify(chst, base)
            except (OSError, subprocess.TimeoutExpired) as e:
                die(f"can't run {chst}: {e}")
            if rc != 0:
                die(f"verify of the unmodified {f} exited {rc}, not 0")

            jobs = []
            for off in range(len(orig)):
                if do_rehash and len(orig) - 56 + 16 <= off < len(orig) - 56 + 48:
                    continue
                for x in (0x01, 0xFF):
                    jobs.append((off, x))

            def one(job, f=f, orig=orig, pool=pool):
                off, x = job
                buf = bytearray(orig)
                buf[off] ^= x
                if do_rehash:
                    rehash(buf)
                p = os.path.join(tmp, f"m-{threading.get_ident()}.chst")
                with open(p, "wb") as fh:
                    fh.write(buf)
                try:
                    rc, err, secs = run_verify(chst, p)
                except subprocess.TimeoutExpired:
                    return job, None, "", TIMEOUT_S
                return job, rc, err, secs

            with ThreadPoolExecutor(max_workers=min(16, (os.cpu_count() or 2) * 2)) as ex:
                for (off, x), rc, err, secs in ex.map(one, jobs):
                    runs += 1
                    where = f"{os.path.basename(os.path.dirname(f))} offset {off} xor {x:#04x}"
                    m = ERROR_LINE.search(err)
                    if rc is None:
                        problems.append(f"{where}: took {TIMEOUT_S} seconds or more")
                        continue
                    if rc in (70, 101) or "panicked" in err:
                        problems.append(f"{where}: exit {rc}, panic or internal error")
                    elif secs >= TIMEOUT_S:
                        problems.append(f"{where}: took {secs:.1f} seconds")
                    elif not do_rehash and rc not in (4, 5, 6, 7):
                        problems.append(f"{where}: exit {rc}, expected 4, 5, 6 or 7")
                    elif do_rehash and rc == 0:
                        allowed = 10 <= off < 12 or 24 <= off < 32 or pool[0] <= off < pool[1]
                        if not allowed:
                            problems.append(f"{where}: accepted, but it isn't a minor_version, optional_flags or path-pool flip")
                    if m and rc not in (None, 0):
                        details[f"{m.group(1)}/{m.group(2)}"] += 1
    if runs == 0:
        die("no mutated file was run")
    for d, n in sorted(details.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"{n:8d}  {d}")
    print(f"runs: {runs}, distinct detail codes: {len(details)}")
    if do_rehash and len(details) < min_distinct:
        problems.append(f"only {len(details)} distinct detail codes, expected at least {min_distinct}")
    for p in problems[:50]:
        print(f"FAIL: {p}")
    if problems:
        print(f"flip_sweep.py: {len(problems)} problems")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
