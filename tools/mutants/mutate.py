"""Runs a mutation suite: break the code one way at a time and check that a test catches it.

Usage (from the repository root):
    python3.14 -I tools/mutants/mutate.py tools/mutants/<suite>.toml [--only TEXT] [--list]

A suite is a TOML file:
    build = "<shell command that compiles every test target>"
    [commands]
    <name> = "<shell command>"          # a mutant is caught if any of these fails
    [[mutant]]
    id = "<short id>"
    what = "<what the mutant breaks>"
    file = "<path>"                     # one edit: file, old, new ...
    old = "<exact text, which must occur exactly once>"
    new = "<replacement>"
    [[mutant.edit]]                     # ... or several edits, applied together
    file = "..."; old = "..."; new = "..."
    skip = "<reason>"                   # optional: not run, but its edits must still match

A skipped mutant is one no test can catch yet (for example, an equivalent mutant until a later
feature exists). Its edits are still checked against the code, so it stays current, and it
is listed in every run until the `skip` line is removed.

Commands run under bash from the repository root, with tools/acceptance/lib.sh sourced and
$W set to a fresh temporary directory that is removed afterwards.

Every mutated file is saved before the first mutant and restored after each one, also on an
error or Ctrl-C, with a fresh mtime so cargo rebuilds it, and its SHA-256 is compared with the
original at the end. The unmutated code must pass every command first. Exit 0 only if every
mutant that isn't skipped compiled and was caught.
"""

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib

TIMEOUT_S = 600


def edits_of(m):
    if "edit" in m:
        return m["edit"]
    return [{"file": m["file"], "old": m["old"], "new": m["new"]}]


def sh(cmd, w):
    """Runs cmd under bash; returns 'pass', 'fail' or 'timeout'."""
    script = f'. tools/acceptance/lib.sh || exit 99\nW="{w}"\n{cmd}\n'
    try:
        r = subprocess.run(
            ["bash", "-c", script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return "timeout"
    return "pass" if r.returncode == 0 else "fail"


def digest(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("suite")
    ap.add_argument("--only", help="run only mutants whose id contains this text")
    ap.add_argument("--list", action="store_true", help="list the mutants and exit")
    args = ap.parse_args(argv)

    if not os.path.isfile("tools/acceptance/lib.sh"):
        sys.exit("run this from the repository root")
    with open(args.suite, "rb") as f:
        suite = tomllib.load(f)
    commands = suite["commands"]
    mutants = suite["mutant"]
    ids = [m["id"] for m in mutants]
    if len(set(ids)) != len(ids):
        sys.exit("mutant ids are not unique")
    if args.only:
        mutants = [m for m in mutants if args.only in m["id"]]
        if not mutants:
            sys.exit(f"no mutant id contains {args.only!r}")
    if args.list:
        for m in mutants:
            note = f"  [skipped: {m['skip']}]" if "skip" in m else ""
            print(f"{m['id']}: {m['what']}{note}")
        return 0

    files = sorted({e["file"] for m in mutants for e in edits_of(m)})
    originals = {}
    for path in files:
        with open(path, encoding="utf-8") as f:
            originals[path] = f.read()
    # Every edit must match its file exactly once, before anything is changed.
    bad = []
    for m in mutants:
        for e in edits_of(m):
            n = originals[e["file"]].count(e["old"])
            if n != 1:
                bad.append(f"{m['id']}: {e['file']}: the old text occurs {n} times")
    if bad:
        print("\n".join(bad))
        return 1

    saved = tempfile.mkdtemp(prefix="mutate-saved-")
    work = tempfile.mkdtemp(prefix="mutate-w-")
    hashes = {p: digest(p) for p in files}
    for i, p in enumerate(files):
        shutil.copyfile(p, os.path.join(saved, str(i)))

    def restore():
        # Contents only, with a new mtime: an old mtime would make cargo keep the mutant build.
        for i, p in enumerate(files):
            shutil.copyfile(os.path.join(saved, str(i)), p)
            os.utime(p)

    results = []
    status = run(suite, commands, mutants, originals, restore, work, results)
    restore()
    shutil.rmtree(saved, ignore_errors=True)
    shutil.rmtree(work, ignore_errors=True)
    changed = [p for p in files if digest(p) != hashes[p]]
    if changed:
        print(f"RESTORE FAILED for {changed}")
        return 2
    if status is not None:
        return status

    ran = [r for r in results if r[1] != "SKIPPED"]
    caught = sum(1 for _, v, _ in ran if v == "CAUGHT")
    skipped = len(results) - len(ran)
    print(f"\n{caught} of {len(ran)} caught, {skipped} skipped; sources restored and unchanged")
    for name in commands:
        only = [m["id"] for m, v, by in results if by == [name]]
        print(f"caught only by {name}: {len(only)}")
    return 0 if caught == len(ran) else 1


def run(suite, commands, mutants, originals, restore, work, results):
    """The baseline, then each mutant. Returns an exit status if the baseline fails."""
    try:
        print("baseline ...", flush=True)
        if sh(suite["build"], work) != "pass":
            print("baseline: the unmutated code does not build")
            return 1
        for name, cmd in commands.items():
            if sh(cmd, work) != "pass":
                print(f"baseline: {name} fails on the unmutated code")
                return 1
        for m in mutants:
            if "skip" in m:
                results.append((m, "SKIPPED", []))
                print(f"{'SKIPPED':10} {m['id']}  ({m['what']}; {m['skip']})", flush=True)
                continue
            text = dict(originals)
            for e in edits_of(m):
                text[e["file"]] = text[e["file"]].replace(e["old"], e["new"], 1)
            for p in {e["file"] for e in edits_of(m)}:
                with open(p, "w", encoding="utf-8") as f:
                    f.write(text[p])
            try:
                if sh(suite["build"], work) != "pass":
                    verdict, by = "NO-COMPILE", []
                else:
                    by = [n for n, c in commands.items() if sh(c, work) != "pass"]
                    verdict = "CAUGHT" if by else "SURVIVED"
            finally:
                restore()
            results.append((m, verdict, by))
            shown = f" by {', '.join(by)}" if by else ""
            print(f"{verdict:10} {m['id']}{shown}  ({m['what']})", flush=True)
    finally:
        # Also on Ctrl-C or any error: the sources go back before anything else happens.
        restore()
    return None


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
