"""Every fixture the acceptance criteria use, defined from FORMAT_SPEC.md.

Each bad fixture starts from a valid base and changes exactly one thing. The structure hash is
recomputed (except for TRL-3 itself), so the reader gets past step 7 to the rule under test.
Blob keys and entry references are recomputed when the stored bytes change.
"""

import hashlib
import struct

import chst
from chst import DIR, FILE, ENC_ZSTD, clone, layout, relayout, sha256

WE_MUTATION = "worked-example"


def d(path):
    return {"path": path.encode("utf-8") if isinstance(path, str) else path, "type": DIR}


def f(path, content, **attrs):
    e = {"path": path.encode("utf-8") if isinstance(path, str) else path, "type": FILE, "content": content}
    e.update(attrs)
    return e


def with_ancestors(entries):
    """Add a directory entry for every missing ancestor (ENT-6)."""
    have = {e["path"] for e in entries}
    out = list(entries)
    for e in entries:
        parts = e["path"].split(b"/")
        for i in range(1, len(parts)):
            p = b"/".join(parts[:i])
            if p not in have:
                have.add(p)
                out.append(d(p))
    return out


def pseudo_random(n, seed):
    out, counter = b"", 0
    while len(out) < n:
        out += hashlib.sha256(seed + counter.to_bytes(8, "little")).digest()
        counter += 1
    return out[:n]


# ---------------------------------------------------------------- valid trees

def worked_example_entries():
    return [d("docs"), f("docs/a.txt", b"hello\n"), f("docs/b.txt", b"hello\n"), d("docs/empty"),
            f("notes.txt", b"hi\n")]


def long_names_entries():
    deep = ["b" * 255] * 15 + ["c" * 128, "d" * 127]
    path = "/".join(deep)
    assert len(path.encode()) == 4096
    return with_ancestors([f("a" * 255, b"long segment\n"), f(path, b"long path\n")])


def deep_entries():
    path = "/".join(["d"] * 255 + ["f"])
    return with_ancestors([f(path, b"deep\n")])


VALID_CORE = {
    "worked-example": worked_example_entries,
    "empty": lambda: [],
    "empty-file": lambda: [f("empty", b"")],
    "dirs-only": lambda: [d("a"), d("a/b"), d("a/b/c"), d("d")],
    "dedup": lambda: with_ancestors([f(f"same/f{i:03d}", b"duplicate content\n") for i in range(100)]
                                    + [f(f"empty/e{i}", b"") for i in (1, 2, 3)]),
    "unicode": lambda: with_ancestors([f("café.txt", b"caf\xc3\xa9\n"), f("日本語/テキスト.txt", b"nihongo\n"),
                                       f("😀.txt", b"emoji\n")]),
    "deep": deep_entries,
    "long-names": long_names_entries,
    "sort-edge": lambda: [d("a"), f("a/b", b"slash\n"), f("a-b", b"dash\n"), f("a.b", b"dot\n")],
}

ATTRS = {"mtime_seconds": 1_700_000_000, "mtime_nanos": 500_000_000}


def attrs_entries():
    return [dict(e, mode=0o755 if e["type"] == DIR else 0o644, **ATTRS) for e in worked_example_entries()] + \
        [f("run.sh", b"#!/bin/sh\necho hi\n", mode=0o755, **ATTRS)]


def zstd_mixed_entries(zeros=8192):
    return [f("random.bin", pseudo_random(4096, b"chst-random")), f("tiny.txt", b"hi\n"),
            f("zeros.bin", b"\x00" * zeros)]


KV_PAIRS = [("comment", "example archive"), ("creator", "chst fixture generator")]

VALID_EXTENDED = {
    "zstd-mixed": (zstd_mixed_entries, {"compress": True}),
    "attrs": (attrs_entries, {"attrs": True}),
    "kv": (worked_example_entries, {"kv": KV_PAIRS}),
}


# ---------------------------------------------------------------- helpers for mutations

def we():
    return layout(worked_example_entries())


def replace_blob_data(plan, i, data, encoding=None):
    """Change a blob's stored bytes; keep keys, entry references and offsets consistent."""
    old = plan["blobs"][i]["key"]
    new = sha256(data)
    plan["blobs"][i]["data"] = data
    plan["blobs"][i]["key"] = new
    if encoding is not None:
        plan["blobs"][i]["encoding"] = encoding
    for e in plan["entries"]:
        if e["blob_key"] == old:
            e["blob_key"] = new
    return relayout(plan)


def blob_index(plan, encoding):
    return next(i for i, b in enumerate(plan["blobs"]) if b["encoding"] == encoding)


def set_(obj, **kw):
    obj.update(kw)


def plan_from(entries, **kw):
    return layout(entries, **kw)


def m(fn):
    """Wrap a plan-mutating function so it returns the mutated plan."""
    def run(plan):
        fn(plan)
        return plan
    return run


def swap_blobs(p):
    p["blobs"].reverse()
    relayout(p)


def swap_entries(p):
    p["entries"][2], p["entries"][3] = p["entries"][3], p["entries"][2]
    relayout(p)


def scramble_pool(p):
    e0, e1 = p["entries"][0], p["entries"][1]
    p["pool"] = e1["path"] + e0["path"] + p["pool"][len(e0["path"]) + len(e1["path"]):]
    e0["path_offset"], e1["path_offset"] = len(e1["path"]), 0


def add_orphan_blob(p):
    p["blobs"].append({"key": sha256(b"orphan\n"), "data": b"orphan\n", "raw_length": 7,
                       "encoding": 0, "reserved": b"\x00" * 7})
    relayout(p)


def dup_blob(p):
    p["blobs"].append(dict(p["blobs"][0]))
    relayout(p)


def corrupt_last_blob(p):
    p["data_override"] = b"hello\nhx\n"


# Each entry: (rule, suffix, base, mutation text, builder, options)
# builder returns a Plan (serialized with a fresh structure hash) or raw bytes.
def core_invalid():
    WE = worked_example_entries()
    return [
        ("HDR-1", "", WE_MUTATION, "file truncated to its first 87 bytes",
         lambda: chst.serialize(we())[:87], {}),
        ("HDR-2", "", WE_MUTATION, "header magic byte 0 changed from 'C' to 'X'",
         lambda: m(lambda p: set_(p["header"], magic=b"X" + chst.MAGIC[1:]))(we()), {}),
        ("HDR-3", "", WE_MUTATION, "major_version = 2",
         lambda: m(lambda p: set_(p["header"], major_version=2))(we()), {}),
        ("HDR-4", "", WE_MUTATION, "hash_alg = 2",
         lambda: m(lambda p: set_(p["header"], hash_alg=2))(we()), {}),
        ("HDR-5", "", WE_MUTATION, "header reserved byte 14 = 0x01",
         lambda: m(lambda p: set_(p["header"], reserved=b"\x00\x01\x00"))(we()), {}),
        ("HDR-6", "", WE_MUTATION, "required_flags bit 1 (unassigned) set",
         lambda: m(lambda p: set_(p["header"], required_flags=1 << 1))(we()), {}),
        ("TRL-1", "", WE_MUTATION, "last trailer magic byte changed to 'D'",
         lambda: m(lambda p: set_(p["trailer"], magic=chst.TRAILER_MAGIC[:-1] + b"D"))(we()), {}),
        ("TRL-2", "", WE_MUTATION, "trailer index_offset = 40 (actual index starts at 41)",
         lambda: m(lambda p: set_(p["trailer"], index_offset=40))(we()), {}),
        ("TRL-3", "", WE_MUTATION, "first byte of the structure hash XORed with 0x01",
         lambda: m(lambda p: set_(p["trailer"], structure_hash_xor=0x01))(we()), {}),
        ("SEC-1", "", WE_MUTATION, "PATH_POOL record_count = 44 (payload is 43 bytes)",
         lambda: m(lambda p: set_(p["pool_section"], record_count=44))(we()), {}),
        ("SEC-2", "", WE_MUTATION, "extra section type 0xFFFFFFF0 (must-understand, unknown) after PATH_POOL",
         lambda: m(lambda p: p["extra_sections"].append({"type": 0xFFFFFFF0, "record_size": 1, "payload": b"x"}))(we()), {}),
        ("SEC-3", "", WE_MUTATION, "PATH_POOL placed before ENTRY_TABLE",
         lambda: m(lambda p: set_(p, section_order=["blob", "pool", "entry"]))(we()), {}),
        ("SEC-4", "", WE_MUTATION, "BLOB_TABLE record_size = 63 (records truncated to 63 bytes)",
         lambda: m(lambda p: set_(p["blob_section"], record_size=63))(we()), {}),
        ("SEC-5", "", WE_MUTATION, "BLOB_TABLE record_size = 72 (8 zero bytes appended to each record), no flags set",
         lambda: m(lambda p: set_(p["blob_section"], record_size=72))(we()), {}),
        ("BLB-1", "", WE_MUTATION, "blob[0] reserved byte 57 = 0x01",
         lambda: m(lambda p: set_(p["blobs"][0], reserved=b"\x01" + b"\x00" * 6))(we()), {}),
        ("BLB-2", "", WE_MUTATION, "blob[0] encoding = 2 (undefined)",
         lambda: m(lambda p: set_(p["blobs"][0], encoding=2))(we()), {}),
        ("BLB-3", "", WE_MUTATION, "blob[1] raw_length = 4 (stored_length 3, encoding stored)",
         lambda: m(lambda p: set_(p["blobs"][1], raw_length=4))(we()), {}),
        ("BLB-4", "", WE_MUTATION, "blob[1] offset = 39 (should be 38)",
         lambda: m(lambda p: set_(p["blobs"][1], offset=39))(we()), {}),
        ("BLB-5", "", WE_MUTATION, "blob[0] record and bytes repeated as a third blob (same key)",
         lambda: m(dup_blob)(we()), {}),
        ("BLB-6", "", WE_MUTATION, "blob[1] bytes changed from 'hi\\n' to 'hx\\n' (key unchanged)",
         lambda: m(corrupt_last_blob)(we()), {}),
        ("BLB-7", "", WE_MUTATION, "extra blob 'orphan\\n' appended, referenced by no entry",
         lambda: m(add_orphan_blob)(we()), {}),
        ("ENT-1", "", WE_MUTATION, "entry[2] (docs/b.txt) type = 3",
         lambda: m(lambda p: set_(p["entries"][2], type=3))(we()), {}),
        ("ENT-2", "", WE_MUTATION, "entry[1] reserved byte 14 = 0x01",
         lambda: m(lambda p: set_(p["entries"][1], reserved=b"\x00\x01\x00"))(we()), {}),
        ("ENT-3", "", WE_MUTATION, "entry[3] (directory docs/empty) blob_key = blob[1].key",
         lambda: m(lambda p: set_(p["entries"][3], blob_key=p["blobs"][1]["key"]))(we()), {}),
        ("ENT-4", "", WE_MUTATION, "entry[2] (docs/b.txt) blob_key = SHA-256('missing'), not in the blob table",
         lambda: m(lambda p: set_(p["entries"][2], blob_key=sha256(b"missing")))(we()), {}),
        ("ENT-5", "", WE_MUTATION, "entry[4] path_length = 10 (pool ends one byte earlier)",
         lambda: m(lambda p: set_(p["entries"][4], path_length=10))(we()), {"allow": ["CAN-3"]}),
        ("ENT-6", "", WE_MUTATION, "directory entry 'docs' removed",
         lambda: plan_from([e for e in WE if e["path"] != b"docs"]), {}),
        ("ENT-6", "-2", "synthetic: file 'f'", "file 'f/g' added under the file 'f'",
         lambda: plan_from([f("f", b"x\n"), f("f/g", b"y\n")]), {}),
        ("PATH-1", "", WE_MUTATION, "file 'notes.txt' renamed to bytes 'notes\\xff.txt' (invalid UTF-8)",
         lambda: plan_from([e if e["path"] != b"notes.txt" else dict(e, path=b"notes\xff.txt") for e in WE]), {}),
        ("PATH-2", "", WE_MUTATION, "directory 'docs/e\\u0301' added (decomposed, not NFC)",
         lambda: plan_from(WE + [d("docs/e\u0301")]), {}),
        ("PATH-3", "", WE_MUTATION, "directory 'docs/' + 256 x 'a' added (segment over 255 bytes)",
         lambda: plan_from(WE + [d("docs/" + "a" * 256)]), {}),
        ("PATH-3", "-2", WE_MUTATION, "file with a 4097-byte path (16 x 255-byte segments + 'z') added, with its ancestors",
         lambda: plan_from(WE + with_ancestors([f("/".join(["c" * 255] * 16 + ["z"]), b"z\n")])), {}),
        ("PATH-4", "", WE_MUTATION, "directory 'docs//x' added (empty segment)",
         lambda: plan_from(WE + [d("docs//x")]), {"allow": ["PATH-3", "ENT-6"]}),
        ("PATH-5", "", WE_MUTATION, "directory 'docs/..' added",
         lambda: plan_from(WE + [d("docs/..")]), {"allow": ["PATH-8"]}),
        ("PATH-6", "", WE_MUTATION, "directory 'docs/a\\x01' added",
         lambda: plan_from(WE + [d("docs/a\x01")]), {}),
        ("PATH-7", "", WE_MUTATION, "directory 'docs/a:b' added",
         lambda: plan_from(WE + [d("docs/a:b")]), {}),
        ("PATH-8", "", WE_MUTATION, "directory 'docs/x.' added",
         lambda: plan_from(WE + [d("docs/x.")]), {}),
        ("PATH-9", "", WE_MUTATION, "directory 'docs/CON' added",
         lambda: plan_from(WE + [d("docs/CON")]), {}),
        ("PATH-9", "-2", WE_MUTATION, "directory 'docs/con .txt' added (stem 'con' after trailing-space removal)",
         lambda: plan_from(WE + [d("docs/con .txt")]), {}),
        ("PATH-9", "-3", WE_MUTATION, "directory 'docs/CONIN$' added",
         lambda: plan_from(WE + [d("docs/CONIN$")]), {}),
        ("PATH-10", "", WE_MUTATION, "chain of 257 nested directories 'a/a/.../a' added",
         lambda: plan_from(WE + with_ancestors([d("/".join(["a"] * 257))])), {}),
        ("PATH-11", "", WE_MUTATION, "directory 'Docs' added (ASCII case-folds to 'docs')",
         lambda: plan_from(WE + [d("Docs")]), {}),
        ("CAN-1", "", WE_MUTATION, "entries 'docs/b.txt' and 'docs/empty' swapped (path pool follows the new order)",
         lambda: m(swap_entries)(we()), {}),
        ("CAN-2", "", WE_MUTATION, "blob table order reversed (data region follows the new order)",
         lambda: m(swap_blobs)(we()), {}),
        ("CAN-3", "", WE_MUTATION, "first two paths swapped inside the path pool; their offsets updated to match",
         lambda: m(scramble_pool)(we()), {}),
        ("LIM-3", "", WE_MUTATION, "none (5 entries); limit lowered to 4",
         lambda: we(), {"args": ["--max-entries", "4"], "limits": {"entries": 4}}),
        ("LIM-4", "", WE_MUTATION, "none (index is 459 bytes); limit lowered to 458",
         lambda: we(), {"args": ["--max-index-bytes", "458"], "limits": {"index": 458}}),
        ("LIM-5", "", WE_MUTATION, "none (logical size 15 bytes, 9 stored); limit lowered to 14",
         lambda: we(), {"args": ["--max-total-bytes", "14"], "limits": {"total": 14}}),
    ]


def zstd_plan(zeros=8192):
    return layout(zstd_mixed_entries(zeros), compress=True)


def extended_invalid():
    def zst1(p):
        i = blob_index(p, ENC_ZSTD)
        replace_blob_data(p, i, chst.zstd_frame(b"\x00" * (p["blobs"][i]["raw_length"] + 1)))

    def zst2(p):
        i = blob_index(p, ENC_ZSTD)
        replace_blob_data(p, i, p["blobs"][i]["data"] + b"\x00")

    def zst3(p):
        i = next(i for i, b in enumerate(p["blobs"]) if b["raw_length"] == 4096)
        replace_blob_data(p, i, chst.zstd_frame(p["blobs"][i]["data"]), encoding=ENC_ZSTD)

    def att1(p):
        e = p["entries"][1]
        e["tail"] = struct.pack("<qIH2x", ATTRS["mtime_seconds"], 1_000_000_000, 0o644)

    return [
        ("ZST-1", "", "zstd-mixed", "zeros.bin frame decodes to raw_length + 1 bytes",
         lambda: m(zst1)(zstd_plan()), {}),
        ("ZST-2", "", "zstd-mixed", "one byte appended after the zeros.bin frame",
         lambda: m(zst2)(zstd_plan()), {}),
        ("ZST-3", "", "zstd-mixed", "random.bin stored as a Raw-block frame (encoding 1, stored_length > raw_length)",
         lambda: m(zst3)(zstd_plan()), {}),
        ("LIM-6", "", "zstd-mixed", "zeros.bin enlarged to 2 MiB (ratio about 27000:1, default limit 1000)",
         lambda: zstd_plan(2 * 1024 * 1024), {}),
        ("ATT-1", "", "attrs", "entry[1] mtime_nanos = 1000000000",
         lambda: m(att1)(layout(attrs_entries(), attrs=True)), {}),
        ("KV-1", "", "kv", "KV pairs written in descending key order",
         lambda: m(lambda p: set_(p["extra_sections"][0], payload=chst.kv_payload(list(reversed(KV_PAIRS)))))(
             layout(worked_example_entries(), kv=KV_PAIRS)), {}),
        ("FLG-1", "", WE_MUTATION, "optional flag KV_METADATA set, no KV_METADATA section",
         lambda: m(lambda p: set_(p["header"], optional_flags=chst.OPT_KV_METADATA))(we()), {}),
    ]


# ---------------------------------------------------------------- attacks, hostile, compat

def attacks():
    def one(path, ancestors=()):
        return lambda: layout([d(a) for a in ancestors] + [f(path, b"attack\n")])
    return [
        ("parent-escape-1", "PATH-5", one("../x")),
        ("parent-escape-2", "PATH-5", one("a/../../x", ["a"])),
        ("absolute-unix", "PATH-4", one("/etc/x")),
        ("absolute-drive", "PATH-7", one("C:/x", ["C:"])),
        ("unc-path", "PATH-7", one("\\\\server\\x")),
        ("backslash", "PATH-7", one("a\\..\\x")),
        ("device-con", "PATH-9", one("CON")),
        ("device-aux-ext", "PATH-9", one("aux.txt")),
        ("device-con-space", "PATH-9", one("CON .txt")),
        ("device-conin", "PATH-9", one("CONIN$")),
        ("device-lpt-superscript", "PATH-9", one("lpt\u00b9")),
        ("ads-named", "PATH-7", one("f.txt:evil")),
        ("ads-data", "PATH-7", one("f.txt::$DATA")),
        ("trailing-dot", "PATH-8", one("x.")),
        ("trailing-space", "PATH-8", one("x ")),
        ("nul-char", "PATH-6", one("a\x00b")),
        ("control-char", "PATH-6", one("a\x1fb")),
        ("case-collision", "PATH-11", lambda: layout([f("A", b"upper\n"), f("a", b"lower\n")])),
        ("file-as-parent", "ENT-6", lambda: layout([f("f", b"x\n"), f("f/g", b"y\n")])),
        ("missing-parent", "ENT-6", lambda: layout([f("d/x", b"x\n")])),
        ("non-nfc", "PATH-2", one("e\u0301")),
    ]


TWO32 = 2 ** 32


def hostile():
    return [
        ("index-length-huge", "trailer index_length = 2^64 - 100",
         lambda: m(lambda p: set_(p["trailer"], index_length=2 ** 64 - 100))(we())),
        ("record-count-2e60", "BLOB_TABLE record_count = 2^60",
         lambda: m(lambda p: set_(p["blob_section"], record_count=2 ** 60))(we())),
        ("entries-2e32", "ENTRY_TABLE record_count = 2^32",
         lambda: m(lambda p: set_(p["entry_section"], record_count=TWO32))(we())),
        ("path-length-max", "entry[4] path_length = 2^32 - 1",
         lambda: m(lambda p: set_(p["entries"][4], path_length=TWO32 - 1))(we())),
    ]


def hostile64():
    def plus(obj, *keys):
        def run(p):
            o = obj(p)
            for k in keys:
                o[k] += TWO32
        return run
    return [
        ("blob0-offset", "blob[0].offset + 2^32", ["BLB-4"], m(plus(lambda p: p["blobs"][0], "offset"))),
        ("blob0-stored-and-raw", "blob[0].stored_length and raw_length + 2^32", ["BLB-4"],
         m(plus(lambda p: p["blobs"][0], "stored_length", "raw_length"))),
        ("blob0-raw", "blob[0].raw_length + 2^32", ["BLB-3"], m(plus(lambda p: p["blobs"][0], "raw_length"))),
        ("entry1-path-offset", "entry[1].path_offset + 2^32", ["ENT-5", "CAN-3"],
         m(plus(lambda p: p["entries"][1], "path_offset"))),
        ("blob-table-count", "BLOB_TABLE record_count + 2^32", ["SEC-1"],
         m(lambda p: set_(p["blob_section"], record_count=len(p["blobs"]) + TWO32))),
        ("trailer-index-offset", "trailer.index_offset + 2^32", ["TRL-2"],
         m(lambda p: set_(p["trailer"], index_offset=chst.HEADER_LEN + 9 + TWO32))),
    ]


def compat():
    WE = worked_example_entries()
    return [
        ("zstd-required-flag", 5, "HDR-6", lambda: zstd_plan()),
        ("unknown-required-bit63", 5, "HDR-6", lambda: m(lambda p: set_(p["header"], required_flags=1 << 63))(we())),
        ("entry-attrs", 0, None, lambda: layout([dict(e, mode=0o644, **ATTRS) for e in WE], attrs=True)),
        ("kv-metadata", 0, None, lambda: layout(WE, kv=KV_PAIRS)),
        ("unknown-optional-bit63", 0, None, lambda: m(lambda p: set_(p["header"], optional_flags=1 << 63))(we())),
        ("unknown-noncritical-section", 0, None,
         lambda: layout(WE, extra_sections=[{"type": 0x7FFFFFF0, "record_size": 1, "payload": b"future"}])),
        ("unknown-critical-section", 5, "SEC-2",
         lambda: layout(WE, extra_sections=[{"type": 0xFFFFFFF0, "record_size": 1, "payload": b"future"}])),
        ("minor-65535", 0, None, lambda: m(lambda p: set_(p["header"], minor_version=65535))(we())),
        ("major-2", 5, "HDR-3", lambda: m(lambda p: set_(p["header"], major_version=2))(we())),
        ("hash-alg-2", 5, "HDR-4", lambda: m(lambda p: set_(p["header"], hash_alg=2))(we())),
    ]


def extract_cases():
    return [
        ("late-blob-hash", 7, "BLB-6", "worked-example with the last blob's bytes corrupted ('hi\\n' -> 'hx\\n')",
         None, lambda: m(corrupt_last_blob)(we())),
        ("unicode-case", 0, None, "files 'é' and 'É' (both NFC): distinct under PATH-11's ASCII-only folding; "
         "collide on case-insensitive filesystems (AC-SAFE-5, AC-SAFE-6)",
         [f("é", b"lower\n"), f("É", b"upper\n")], None),
        ("short-name", 0, None, "directories 'ABCDEFGHIJ' (file 'a') and 'ABCDEF~1' (file 'b'); the second can "
         "collide with the first's Windows 8.3 short name (AC-SAFE-10)",
         [d("ABCDEFGHIJ"), f("ABCDEFGHIJ/a", b"a\n"), d("ABCDEF~1"), f("ABCDEF~1/b", b"b\n")], None),
    ]
