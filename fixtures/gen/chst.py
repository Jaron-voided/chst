"""Chst container model and writer, written from FORMAT_SPEC.md.

A container is first described as a Plan: every on-disk field with an explicit value.
`layout()` builds a canonical Plan from entries and blobs; fixtures may then change any
field before `serialize()` turns the Plan into bytes. Unless told otherwise, `serialize()`
recomputes the structure hash, so a mutation reaches the rule it targets instead of
stopping at TRL-3.
"""

import copy
import hashlib
import struct

MAGIC = b"CHST\r\n\x1a\x00"
TRAILER_MAGIC = b"\x00\x1a\n\rTSHC"
HEADER_LEN = 32
TRAILER_LEN = 56
HASH_SHA256 = 1

DIR, FILE = 1, 2
ENC_STORED, ENC_ZSTD = 0, 1

SEC_BLOB_TABLE = 0x80000001
SEC_ENTRY_TABLE = 0x80000002
SEC_PATH_POOL = 0x80000003
SEC_KV_METADATA = 0x00000010
MUST_UNDERSTAND = 0x80000000
SECTION_NAMES = {
    SEC_BLOB_TABLE: "BLOB_TABLE",
    SEC_ENTRY_TABLE: "ENTRY_TABLE",
    SEC_PATH_POOL: "PATH_POOL",
    SEC_KV_METADATA: "KV_METADATA",
}

BLOB_RECORD = 64
ENTRY_RECORD = 48
ENTRY_RECORD_ATTRS = 64

REQ_ZSTD = 1 << 0
OPT_ENTRY_ATTRS = 1 << 0
OPT_KV_METADATA = 1 << 1
REQUIRED_FLAG_NAMES = {REQ_ZSTD: "ZSTD"}
OPTIONAL_FLAG_NAMES = {OPT_ENTRY_ATTRS: "ENTRY_ATTRS", OPT_KV_METADATA: "KV_METADATA"}

ZERO_KEY = b"\x00" * 32


def sha256(data):
    return hashlib.sha256(data).digest()


# ---------------------------------------------------------------- Zstandard (RFC 8878)
# Frames are built from Raw and RLE blocks only. That is enough for every fixture, keeps
# the output independent of any compressor version, and gives an encoder that shares no
# code with the zstd library the Rust side uses.

ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"
ZSTD_BLOCK_MAX = 128 * 1024


def zstd_frame(content, declared_size=None):
    """One complete frame: single segment, 8-byte Frame_Content_Size, no checksum."""
    size = len(content) if declared_size is None else declared_size
    out = bytearray(ZSTD_MAGIC)
    out.append(0xE0)  # FCS_Field_Size = 8 bytes, Single_Segment_Flag = 1
    out += struct.pack("<Q", size)
    chunks = [content[i:i + ZSTD_BLOCK_MAX] for i in range(0, len(content), ZSTD_BLOCK_MAX)] or [b""]
    for n, chunk in enumerate(chunks):
        last = 1 if n == len(chunks) - 1 else 0
        if len(chunk) > 1 and chunk.count(chunk[0]) == len(chunk):
            out += ((len(chunk) << 3) | (1 << 1) | last).to_bytes(3, "little")  # RLE block
            out.append(chunk[0])
        else:
            out += ((len(chunk) << 3) | last).to_bytes(3, "little")  # Raw block
            out += chunk
    return bytes(out)


def encode_blob(content, compress):
    """D7: keep the compressed form only if it is strictly smaller."""
    if compress:
        frame = zstd_frame(content)
        if len(frame) < len(content):
            return frame, ENC_ZSTD
    return content, ENC_STORED


# ---------------------------------------------------------------- canonical layout

def fold_key(path):
    return bytes(c + 32 if 65 <= c <= 90 else c for c in path)


def layout(entries, *, compress=False, attrs=False, kv=None, extra_sections=()):
    """Build the canonical Plan (FORMAT_SPEC §11) for a list of entries.

    Each entry is a dict: path (bytes), type (DIR or FILE), content (bytes, files only),
    and with attrs=True: mtime_seconds, mtime_nanos, mode.
    """
    entries = sorted(entries, key=lambda e: e["path"])
    blobs, seen = [], {}
    plan_entries = []
    for e in entries:
        tail = b""
        if attrs:
            tail = struct.pack("<qIH2x", e.get("mtime_seconds", 0), e.get("mtime_nanos", 0), e.get("mode", 0o644))
        if e["type"] == FILE:
            stored, enc = encode_blob(e["content"], compress)
            key = sha256(stored)
            if key not in seen:
                seen[key] = len(blobs)
                blobs.append({"key": key, "data": stored, "raw_length": len(e["content"]),
                              "encoding": enc, "reserved": b"\x00" * 7})
            blob_key = key
        else:
            blob_key = ZERO_KEY
        plan_entries.append({"path": e["path"], "type": e["type"], "reserved": b"\x00" * 3,
                             "blob_key": blob_key, "tail": tail})
    required = REQ_ZSTD if any(b["encoding"] == ENC_ZSTD for b in blobs) else 0
    optional = (OPT_ENTRY_ATTRS if attrs else 0) | (OPT_KV_METADATA if kv else 0)
    sections = list(extra_sections)
    if kv:
        sections = [{"type": SEC_KV_METADATA, "record_size": 1, "payload": kv_payload(kv)}] + sections
    plan = {
        "header": {"magic": MAGIC, "major_version": 1, "minor_version": 0, "hash_alg": HASH_SHA256,
                   "reserved": b"\x00" * 3, "required_flags": required, "optional_flags": optional},
        "blobs": blobs,
        "entries": plan_entries,
        "blob_section": {"type": SEC_BLOB_TABLE, "record_size": BLOB_RECORD},
        "entry_section": {"type": SEC_ENTRY_TABLE, "record_size": ENTRY_RECORD_ATTRS if attrs else ENTRY_RECORD},
        "pool_section": {"type": SEC_PATH_POOL, "record_size": 1},
        "extra_sections": sections,
        "section_order": None,
        "trailer": {},
        "data_override": None,
        "append": b"",
    }
    relayout(plan)
    return plan


def relayout(plan):
    """Recompute derived fields (blob offsets, stored lengths, path offsets and lengths, pool)."""
    off = HEADER_LEN
    for b in plan["blobs"]:
        b["offset"] = off
        b["stored_length"] = len(b["data"])
        off += len(b["data"])
    pool = b""
    for e in plan["entries"]:
        e["path_offset"] = len(pool)
        e["path_length"] = len(e["path"])
        pool += e["path"]
    plan["pool"] = pool
    return plan


def kv_payload(pairs):
    out = b""
    for k, v in pairs:
        k, v = k.encode(), v.encode()
        out += struct.pack("<H", len(k)) + k + struct.pack("<I", len(v)) + v
    return out


def clone(plan):
    return copy.deepcopy(plan)


# ---------------------------------------------------------------- serialization

def header_bytes(h):
    return (h["magic"] + struct.pack("<HHB", h["major_version"], h["minor_version"], h["hash_alg"])
            + h["reserved"] + struct.pack("<QQ", h["required_flags"], h["optional_flags"]))


def blob_record(b):
    return b["key"] + struct.pack("<QQQB", b["offset"], b["stored_length"], b["raw_length"], b["encoding"]) + b["reserved"]


def entry_record(e):
    return struct.pack("<QIB", e["path_offset"], e["path_length"], e["type"]) + e["reserved"] + e["blob_key"] + e["tail"]


def fit(record, size):
    return (record + b"\x00" * size)[:size]


def section_bytes(sec, records=None, payload=None):
    """Section header plus payload. record_count defaults to the real number of records."""
    if records is not None:
        body = b"".join(fit(r, sec["record_size"]) for r in records)
        count = len(records)
    else:
        body = payload
        count = len(payload) // max(sec["record_size"], 1)
    count = sec.get("record_count", count)
    return struct.pack("<IIQ", sec["type"], sec["record_size"], count) + body


def build_sections(plan):
    """Return the sections as (name, bytes, info) in on-disk order."""
    named = {
        "blob": (plan["blob_section"], [blob_record(b) for b in plan["blobs"]], None),
        "entry": (plan["entry_section"], [entry_record(e) for e in plan["entries"]], None),
        "pool": (plan["pool_section"], None, plan["pool"]),
    }
    order = plan["section_order"] or ["blob", "entry", "pool"]
    out = []
    for name in order:
        sec, recs, payload = named[name]
        out.append((name, section_bytes(sec, recs, payload), sec))
    for i, sec in enumerate(plan["extra_sections"]):
        out.append((f"extra{i}", section_bytes(sec, None, sec["payload"]), sec))
    return out


def serialize(plan, *, recompute_hash=True):
    header = header_bytes(plan["header"])
    data = plan["data_override"] if plan["data_override"] is not None else b"".join(b["data"] for b in plan["blobs"])
    index = b"".join(raw for _, raw, _ in build_sections(plan))
    t = plan["trailer"]
    index_offset = t.get("index_offset", HEADER_LEN + len(data))
    index_length = t.get("index_length", len(index))
    prefix = struct.pack("<QQ", index_offset, index_length)
    if recompute_hash or "structure_hash" not in t:
        shash = sha256(header + index + prefix)
    else:
        shash = t["structure_hash"]
    if "structure_hash_xor" in t:
        shash = bytes([shash[0] ^ t["structure_hash_xor"]]) + shash[1:]
    trailer = prefix + shash + t.get("magic", TRAILER_MAGIC)
    return header + data + index + trailer + plan["append"]


# ---------------------------------------------------------------- tree helpers

def entries_from_tree(tree):
    """tree.json entries -> layout() entries."""
    import base64
    out = []
    for e in tree["entries"]:
        d = {"path": e["path"].encode("utf-8"), "type": DIR if e["type"] == "dir" else FILE}
        if e["type"] == "file":
            d["content"] = base64.b64decode(e["content_b64"])
        for k in ("mtime_seconds", "mtime_nanos", "mode"):
            if k in e:
                d[k] = e[k]
        out.append(d)
    return out


def tree_from_entries(entries, *, with_attrs=False):
    import base64
    out = []
    for e in sorted(entries, key=lambda e: e["path"]):
        d = {"path": e["path"].decode("utf-8"), "type": "dir" if e["type"] == DIR else "file"}
        if e["type"] == FILE:
            d["content_b64"] = base64.b64encode(e["content"]).decode()
        if with_attrs:
            for k in ("mtime_seconds", "mtime_nanos", "mode"):
                d[k] = e[k]
        out.append(d)
    return {"schema": "chst-tree/1", "entries": out}
