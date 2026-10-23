"""Chst fixture generator. Run with python3.14 -I (standard library only).

  gen.py [--out DIR]                       build every fixture (default: the fixtures/ dir)
  gen.py materialize TREE.json DIR [--reverse]
  gen.py materialize-sparse RECIPE.json FILE
  gen.py synth-entries N FILE              N empty files sharing one blob
  gen.py synth-amplify N SIZE FILE         N files sharing one SIZE-byte blob
  gen.py worked-example-hexdump            print FORMAT_SPEC §18.3's hex dump from the fixture

Every fixture is derived from FORMAT_SPEC.md. Rule categories, detail codes and exit codes are
read from FORMAT_SPEC.md itself (Appendix A and §16), so they can't drift from the spec.
"""

import sys

sys.dont_write_bytecode = True  # keep fixtures/gen free of cache files (they'd break the manifest)

import os.path

# -I (isolated mode) leaves the script's directory off sys.path; add only that directory.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import argparse
import hashlib
import json
import os
import pathlib
import random
import re
import shutil
import struct

import catalog
import chst
import reports
from check import check

GEN_DIR = pathlib.Path(__file__).resolve().parent
FIXTURES_DIR = GEN_DIR.parent
SPEC = FIXTURES_DIR.parent / "FORMAT_SPEC.md"


# ---------------------------------------------------------------- spec tables

def spec_tables():
    text = SPEC.read_text(encoding="utf-8")
    appx = text.split("## Appendix A")[1].split("## Appendix B")[0]
    rules = {}
    for rule, cat, det in re.findall(r"^\| \*\*([A-Z]+-\d+)\*\* \| ([a-z-]+|\(warning\)) \| `([a-z0-9.-]+)` \|", appx, re.M):
        rules[rule] = (cat, det)
    errs = text.split("## 16. Error model")[1].split("## 17.")[0]
    exits = {cat: int(code) for cat, code in re.findall(r"^\| `([a-z-]+)` \| .* \| (\d+) \|$", errs, re.M)}
    hexsec = text.split("### 18.3 Hex dump")[1].split("```")[1]
    worked = b"".join(bytes.fromhex(line[10:58].replace(" ", "")) for line in hexsec.strip().splitlines())
    return rules, exits, worked


RULES, EXITS, SPEC_WORKED_EXAMPLE = spec_tables()


def outcome(rule):
    cat, det = RULES[rule]
    return cat, det, EXITS[cat]


# ---------------------------------------------------------------- output helpers

class Out:
    def __init__(self, root):
        self.root = pathlib.Path(root)

    def write(self, rel, data):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def json(self, rel, obj):
        self.write(rel, (json.dumps(obj, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))


def to_bytes(plan_or_bytes):
    return plan_or_bytes if isinstance(plan_or_bytes, bytes) else chst.serialize(plan_or_bytes)


def require(cond, msg):
    if not cond:
        raise SystemExit(f"self-check failed: {msg}")


def expect_first(name, data, rule, limits=None, reader="extended"):
    """The reader must report `rule` (the first violation in §13 order). Returns all violations."""
    got = check(data, limits=limits, reader=reader)
    require(got and got[0] == rule, f"{name}: expected {rule} first, checker found {got}")
    return got


def write_valid(out, base, entries, *, readers=("extended",), **kw):
    frame = kw.pop("frame", None)
    plan = catalog.with_frame(entries, *frame) if frame else chst.layout(entries, **kw)
    data = chst.serialize(plan)
    for r in readers:
        require(check(data, reader=r) == [], f"{base}: valid fixture violates {check(data, reader=r)} ({r} reader)")
    c = reports.parse_bytes(data)
    out.write(f"{base}/container.chst", data)
    out.json(f"{base}/tree.json", chst.tree_from_entries(entries, with_attrs=kw.get("attrs", False)))
    out.json(f"{base}/list.json", reports.list_report(c))
    out.json(f"{base}/verify.json", reports.verify_report(c))
    out.json(f"{base}/inspect.json", reports.inspect_report(c))
    return data


def invalid_expect(rule, base, mutation, got, args=None):
    cat, det, code = outcome(rule)
    e = {"rule": rule, "category": cat, "detail": det, "exit": code, "base": base, "mutation": mutation}
    if args:
        e["args"] = args
    if len(got) > 1:
        # Informational only: rules also broken, which a reader must not report because they come
        # later in FORMAT_SPEC §13's order. Checks compare only `detail`.
        e["also_violates"] = [RULES[r][1] for r in got[1:]]
    return e


def single_detail_expect(rule, **extra):
    cat, det, code = outcome(rule)
    return {"rule": rule, "category": cat, "detail": det, "exit": code, **extra}


# ---------------------------------------------------------------- build everything

def build(out_root):
    out_root = pathlib.Path(out_root)
    out_root.mkdir(parents=True, exist_ok=True)
    for child in out_root.iterdir():  # rebuild from scratch, but never touch the generator
        if child.name == "gen":
            continue
        shutil.rmtree(child) if child.is_dir() else child.unlink()
    out = Out(out_root)
    counts = {}

    def bump(k):
        counts[k] = counts.get(k, 0) + 1

    # core/valid: valid for both a Core-only and an Extended reader
    for name, fn in catalog.VALID_CORE.items():
        data = write_valid(out, f"core/valid/{name}", fn(), readers=("extended", "core"))
        bump("core/valid")
        if name == "worked-example":
            require(data == SPEC_WORKED_EXAMPLE,
                    "worked example differs from FORMAT_SPEC §18.3; regenerate the spec section from "
                    "'gen.py worked-example-hexdump'")

    # core/invalid
    for rule, suffix, base, mutation, builder, opts in catalog.core_invalid():
        data = to_bytes(builder())
        got = expect_first(f"{rule}{suffix}", data, rule, opts.get("limits"))
        require(check(data, limits=opts.get("limits"), reader="core")[:1] == [rule], f"{rule}{suffix}: core reader differs")
        out.write(f"core/invalid/{rule}{suffix}.chst", data)
        out.json(f"core/invalid/{rule}{suffix}.expect.json", invalid_expect(rule, base, mutation, got, opts.get("args")))
        bump("core/invalid")
    build_lim2_recipe(out)
    bump("core/invalid")

    # core/attacks: the expected first violation is written in the catalog, not taken from the checker
    for name, rule, builder in catalog.attacks():
        data = chst.serialize(builder())
        expect_first(f"attack {name}", data, rule)
        out.write(f"core/attacks/{name}.chst", data)
        out.json(f"core/attacks/{name}.expect.json", single_detail_expect(rule))
        bump("core/attacks")

    # core/extract-cases
    for name, code, rule, note, entries, builder in catalog.extract_cases():
        data = chst.serialize(builder() if builder else chst.layout(entries))
        require(check(data) == ([rule] if rule else []), f"extract-case {name}: got {check(data)}")
        out.write(f"core/extract-cases/{name}.chst", data)
        e = {"exit": code, "note": note}
        if rule:
            e.update(single_detail_expect(rule))
        out.json(f"core/extract-cases/{name}.expect.json", e)
        if entries:
            out.json(f"core/extract-cases/{name}.tree.json", chst.tree_from_entries(entries))
        bump("core/extract-cases")

    # core/hostile (AC-LIM-1): huge declared sizes in tiny files
    for name, rule, mutation, builder in catalog.hostile():
        data = chst.serialize(builder())
        expect_first(f"hostile {name}", data, rule)
        require(len(data) < 1024, f"hostile {name}: {len(data)} bytes")
        out.write(f"core/hostile/{name}.chst", data)
        out.json(f"core/hostile/{name}.expect.json",
                 single_detail_expect(rule, base=catalog.WE_MUTATION, mutation=mutation))
        bump("core/hostile")

    # core/hostile64 (AC-ROB-8): 2^32 added to u64 fields; a 32-bit reader would accept these
    for name, mutation, rules, mut in catalog.hostile64():
        data = chst.serialize(mut(catalog.we()))
        expect_first(f"hostile64 {name}", data, rules[0])
        out.write(f"core/hostile64/{name}.chst", data)
        e = single_detail_expect(rules[0], base=catalog.WE_MUTATION, mutation=mutation)
        e["details"] = [e["detail"]]
        out.json(f"core/hostile64/{name}.expect.json", e)
        bump("core/hostile64")

    # core/sparse (AC-ROB-9): a valid 5 GiB container, stored as a recipe
    build_sparse(out, "core/sparse/huge-5g", 5 * 2 ** 30)
    bump("core/sparse")

    # compat (AC-COMPAT-1): proven with a Core-only reader; reports are the Core reader's view
    for name, code, rule, builder in catalog.compat():
        data = chst.serialize(builder())
        core_got = check(data, reader="core")
        require(core_got == ([rule] if rule else []), f"compat {name}: core reader found {core_got}")
        require(check(data, reader="extended") in ([], [rule]), f"compat {name}: extended reader found {check(data)}")
        out.write(f"compat/{name}.chst", data)
        out.json(f"compat/{name}.expect.json",
                 {"exit": code, "detail": RULES[rule][1] if rule else None,
                  "note": "Expected result for a Core-only reader (built with --no-default-features)."})
        if code == 0:
            c = reports.parse_bytes(data, reader="core")
            out.json(f"compat/{name}.list.json", reports.list_report(c))
            out.json(f"compat/{name}.verify.json", reports.verify_report(c))
            out.json(f"compat/{name}.inspect.json", reports.inspect_report(c))
        bump("compat")

    # extended/valid
    for name, (fn, kw) in catalog.VALID_EXTENDED.items():
        write_valid(out, f"extended/valid/{name}", fn(), **kw)
        bump("extended/valid")

    # extended/invalid
    for rule, suffix, base, mutation, builder, opts in catalog.extended_invalid():
        data = to_bytes(builder())
        got = expect_first(f"{rule}{suffix}", data, rule, opts.get("limits"))
        out.write(f"extended/invalid/{rule}{suffix}.chst", data)
        out.json(f"extended/invalid/{rule}{suffix}.expect.json", invalid_expect(rule, base, mutation, got, opts.get("args")))
        bump("extended/invalid")

    # Binary-exact files: stop git line-ending conversion (core.autocrlf on Windows) from touching them.
    out.write(".gitattributes", b"* -text\n")
    out.write("fuzz-regressions/README.txt",
              b"Inputs that once crashed or hung a fuzz target are added here, one file each, under\n"
              b"<target>/ (ACCEPTANCE.md AC-ROB-5). The generator never creates them.\n")

    write_manifest(out_root)
    return counts


def build_lim2_recipe(out):
    """LIM-2 (F7): an index over 2^32 bytes. Only a header and a trailer are stored: LIM-2 is
    checked in step 6, before the index is read, so the index bytes are never needed."""
    head = chst.header_bytes(catalog.we()["header"])
    index_length = 2 ** 32 + 1
    prefix = struct.pack("<QQ", chst.HEADER_LEN, index_length)
    trailer = prefix + b"\x00" * 32 + chst.TRAILER_MAGIC  # structure hash never reached (step 7)
    file_length = chst.HEADER_LEN + index_length + chst.TRAILER_LEN
    from check import head_trailer_checks, DEFAULT_LIMITS
    require(head_trailer_checks(head, trailer, file_length, DEFAULT_LIMITS) == ["LIM-2"], "LIM-2 recipe")
    out.json("core/invalid/LIM-2.recipe.json",
             {"schema": "chst-sparse-recipe/1", "file_length": file_length, "head_hex": head.hex(),
              "tail_offset": file_length - chst.TRAILER_LEN, "tail_hex": trailer.hex(),
              "note": "Index of 2^32 + 1 bytes (all zero, never read). Create the file sparse, then "
                      "write head and tail (gen.py materialize-sparse)."})
    out.json("core/invalid/LIM-2.expect.json",
             invalid_expect("LIM-2", catalog.WE_MUTATION,
                            "index_length = 2^32 + 1, with only header and trailer stored (sparse recipe)", ["LIM-2"]))


def build_sparse(out, base, size):
    """One all-zero file of `size` bytes. Only the header and index/trailer bytes are stored."""
    h = hashlib.sha256()
    chunk = b"\x00" * (1 << 20)
    left = size
    while left:
        n = min(left, len(chunk))
        h.update(chunk[:n])
        left -= n
    key = h.digest()
    plan = chst.layout([catalog.f("huge.bin", b"")])
    b = plan["blobs"][0]
    b.update({"key": key, "stored_length": size, "raw_length": size, "offset": chst.HEADER_LEN})
    plan["entries"][0]["blob_key"] = key
    head = chst.header_bytes(plan["header"])
    index = b"".join(raw for _, raw, _ in chst.build_sections(plan))
    index_offset = chst.HEADER_LEN + size
    prefix = struct.pack("<QQ", index_offset, len(index))
    trailer = prefix + chst.sha256(head + index + prefix) + chst.TRAILER_MAGIC
    file_length = index_offset + len(index) + chst.TRAILER_LEN
    recipe = {"schema": "chst-sparse-recipe/1", "file_length": file_length, "head_hex": head.hex(),
              "tail_offset": index_offset, "tail_hex": (index + trailer).hex(),
              "note": f"One file 'huge.bin' of {size} zero bytes. Bytes [32, {index_offset}) are zero; "
                      "create the file sparse, then write head and tail (gen.py materialize-sparse)."}
    out.json(f"{base}/recipe.json", recipe)
    c = reports.parse(head, index, trailer, file_length)
    out.json(f"{base}/list.json", reports.list_report(c))
    out.json(f"{base}/verify.json", reports.verify_report(c))
    out.json(f"{base}/inspect.json", reports.inspect_report(c))


def write_manifest(out_root):
    files = []
    for p in sorted(out_root.rglob("*")):
        if p.is_file() and p.name != "MANIFEST.sha256" and p.relative_to(out_root).parts[0] != "gen":
            files.append((p.relative_to(out_root).as_posix(), p))
    for p in sorted(GEN_DIR.rglob("*")):
        if p.is_file():
            files.append((("gen/" + p.relative_to(GEN_DIR).as_posix()), p))
    lines = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {rel}\n" for rel, p in sorted(files)]
    (out_root / "MANIFEST.sha256").write_text("".join(lines), encoding="utf-8")


# ---------------------------------------------------------------- subcommands for checks

def long_path(p):
    p = os.path.abspath(p)
    return "\\\\?\\" + p if os.name == "nt" and not p.startswith("\\\\?\\") else p


def materialize(tree_path, dest, reverse=False):
    tree = json.loads(pathlib.Path(tree_path).read_text(encoding="utf-8"))
    entries = tree["entries"]
    seed = os.environ.get("CHST_DET_SEED", "chst-det-1")
    rng = random.Random(seed)
    if reverse:
        print(f"materialize --reverse: CHST_DET_SEED={seed}", file=sys.stderr)
    os.makedirs(dest, exist_ok=False)
    dirs = [e for e in entries if e["type"] == "dir"]
    files = [e for e in entries if e["type"] == "file"]
    if reverse:  # deepest directories first (their ancestors appear as a side effect), files reversed
        dirs, files = sorted(dirs, key=lambda e: e["path"], reverse=True), files[::-1]
    import base64
    made = set()
    for e in dirs:
        _mkdirs(dest, e["path"].split("/"), made)
    for e in files:
        parts = e["path"].split("/")
        _mkdirs(dest, parts[:-1], made)
        _write_file(dest, parts, base64.b64decode(e["content_b64"]))
    if reverse:
        for e in entries:
            _touch_random(dest, e["path"].split("/"), e["type"], rng)


def _open_dir(root, parts):
    """Open a directory relative to root one segment at a time (long paths on macOS)."""
    fd = os.open(root, os.O_RDONLY)
    for part in parts:
        nfd = os.open(part, os.O_RDONLY, dir_fd=fd)
        os.close(fd)
        fd = nfd
    return fd


def _mkdirs(root, parts, made):
    """Create each missing directory. An existing name we didn't create here means two entries
    collided on this filesystem (for example case-insensitive): fail instead of merging."""
    for i in range(1, len(parts) + 1):
        key = "/".join(parts[:i])
        if key in made:
            continue
        if os.name == "nt":
            p = long_path(os.path.join(root, *parts[:i]))
            os.mkdir(p)  # raises FileExistsError on a collision
        else:
            fd = _open_dir(root, parts[:i - 1])
            try:
                os.mkdir(parts[i - 1], dir_fd=fd)  # raises FileExistsError on a collision
            finally:
                os.close(fd)
        made.add(key)


def _write_file(root, parts, content):
    if os.name == "nt":
        with open(long_path(os.path.join(root, *parts)), "xb") as fh:
            fh.write(content)
        return
    fd = _open_dir(root, parts[:-1])
    try:
        ffd = os.open(parts[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644, dir_fd=fd)
        with os.fdopen(ffd, "wb") as fh:
            fh.write(content)
    finally:
        os.close(fd)


def _touch_random(root, parts, typ, rng):
    when = rng.randrange(0, 2 ** 31)
    mode = rng.choice([0o700, 0o750, 0o755]) if typ == "dir" else rng.choice([0o600, 0o640, 0o644, 0o755])
    if os.name == "nt":
        path = long_path(os.path.join(root, *parts))
        os.utime(path, (when, when))
        return
    fd = _open_dir(root, parts[:-1])
    try:
        os.utime(parts[-1], (when, when), dir_fd=fd)
        os.chmod(parts[-1], mode, dir_fd=fd)
    finally:
        os.close(fd)


def materialize_sparse(recipe_path, file_path):
    r = json.loads(pathlib.Path(recipe_path).read_text(encoding="utf-8"))
    size = os.path.getsize(file_path)
    if size != r["file_length"]:
        raise SystemExit(f"{file_path}: size {size}, recipe needs {r['file_length']} (create it sparse first)")
    with open(file_path, "r+b") as fh:
        fh.write(bytes.fromhex(r["head_hex"]))
        fh.seek(r["tail_offset"])
        fh.write(bytes.fromhex(r["tail_hex"]))


def synth(file_path, n, content):
    entries = [{"path": f"f{i:08d}".encode(), "type": chst.FILE, "content": content} for i in range(n)]
    pathlib.Path(file_path).write_bytes(chst.serialize(chst.layout(entries)))


def worked_example_hexdump():
    data = chst.serialize(chst.layout(catalog.worked_example_entries()))
    for i in range(0, len(data), 16):
        chunk = data[i:i + 16]
        hx = " ".join(f"{b:02x}" for b in chunk)
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        print(f"{i:08x}  {hx:<47}  |{asc}|")


def main(argv):
    if argv and argv[0] == "materialize":
        ap = argparse.ArgumentParser(prog="gen.py materialize")
        ap.add_argument("tree"), ap.add_argument("dest"), ap.add_argument("--reverse", action="store_true")
        a = ap.parse_args(argv[1:])
        materialize(a.tree, a.dest, a.reverse)
    elif argv and argv[0] == "materialize-sparse":
        materialize_sparse(argv[1], argv[2])
    elif argv and argv[0] == "synth-entries":
        synth(argv[2], int(argv[1]), b"")
    elif argv and argv[0] == "synth-amplify":
        size = int(argv[2])
        synth(argv[3], int(argv[1]), bytes(i % 251 for i in range(size)))
    elif argv and argv[0] == "worked-example-hexdump":
        worked_example_hexdump()
    else:
        ap = argparse.ArgumentParser(prog="gen.py")
        ap.add_argument("--out", default=str(FIXTURES_DIR))
        a = ap.parse_args(argv)
        counts = build(a.out)
        for k, v in counts.items():
            print(f"{k}: {v}")
        print(f"total: {sum(counts.values())} fixtures; manifest written")


if __name__ == "__main__":
    main(sys.argv[1:])
