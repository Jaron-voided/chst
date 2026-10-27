"""AC-ROB-2: truncate and extend a container, and run `chst verify` on each result.

Usage: python3.14 -I tools/acceptance/truncate_sweep.py CHST FILE
Asserts, for a FILE of N bytes:
- every prefix length from 0 to N-1 exits 4 when the length is below 88, and 6 (`trl.magic`) otherwise;
- appending 1 byte, or 4096 bytes, exits non-zero;
- never exit 0, 70 or 101, no `panicked` on stderr, and each run takes under 5 seconds.
Exit 1 if an assertion fails, CHST can't be run, FILE can't be read, or nothing was run.
Standard library only.
"""

import os
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor

TIMEOUT_S = 5


def die(msg):
    print(f"truncate_sweep.py: {msg}", file=sys.stderr)
    sys.exit(1)


def main():
    if len(sys.argv) != 3:
        die("usage: truncate_sweep.py CHST FILE")
    chst, f = sys.argv[1:]
    if not os.path.isfile(chst) or not os.access(chst, os.X_OK):
        die(f"can't find an executable CHST at {chst}")
    try:
        with open(f, "rb") as fh:
            orig = fh.read()
    except OSError as e:
        die(f"can't read {f}: {e}")
    if len(orig) < 88:
        die(f"{f} is too short to be a container")

    with tempfile.TemporaryDirectory() as tmp:
        def verify(data):
            p = os.path.join(tmp, f"m-{threading.get_ident()}.chst")
            with open(p, "wb") as fh:
                fh.write(data)
            start = time.monotonic()
            try:
                r = subprocess.run([chst, "verify", p], capture_output=True, timeout=TIMEOUT_S)
            except subprocess.TimeoutExpired:
                return None, "", TIMEOUT_S
            return r.returncode, r.stderr.decode("utf-8", "replace"), time.monotonic() - start

        try:
            rc = verify(orig)[0]
        except OSError as e:
            die(f"can't run {chst}: {e}")
        if rc != 0:
            die(f"verify of the unmodified {f} exited {rc}, not 0")

        cases = [(f"prefix of {n} bytes", orig[:n], 4 if n < 88 else 6) for n in range(len(orig))]
        cases += [(f"{k} byte(s) appended", orig + b"\x00" * k, None) for k in (1, 4096)]
        problems = []
        with ThreadPoolExecutor(max_workers=min(16, (os.cpu_count() or 2) * 2)) as ex:
            results = ex.map(lambda c: verify(c[1]), cases)
            for (label, _, want), (rc, err, secs) in zip(cases, results):
                if rc is None or secs >= TIMEOUT_S:
                    problems.append(f"{label}: took {TIMEOUT_S} seconds or more")
                elif rc in (0, 70, 101) or "panicked" in err:
                    problems.append(f"{label}: exit {rc}, panic or internal error")
                elif want is not None and rc != want:
                    problems.append(f"{label}: exit {rc}, expected {want}")
                elif want == 6 and "trl.magic" not in err:
                    problems.append(f"{label}: expected trl.magic, stderr was {err.splitlines()[:1]}")
    print(f"runs: {len(cases)}")
    for p in problems[:50]:
        print(f"FAIL: {p}")
    if problems:
        print(f"truncate_sweep.py: {len(problems)} problems")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
