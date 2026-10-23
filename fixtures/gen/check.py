"""Rule checker used only to validate the generated fixtures against FORMAT_SPEC.md.

check(data) returns the set of rule IDs the container violates, following the reader
algorithm of FORMAT_SPEC §13. Steps 1-7 stop at the first violation, as the spec requires.
Steps 8-11 collect every violation they can still evaluate. The generator asserts that each
valid fixture returns an empty set, and that each bad fixture returns only the rules its
expect.json allows.
"""

import hashlib
import struct
import unicodedata

from chst import (BLOB_RECORD, DIR, ENC_STORED, ENC_ZSTD, ENTRY_RECORD, ENTRY_RECORD_ATTRS, FILE,
                  HEADER_LEN, MAGIC, MUST_UNDERSTAND, OPT_ENTRY_ATTRS, OPT_KV_METADATA, REQ_ZSTD,
                  SEC_BLOB_TABLE, SEC_ENTRY_TABLE, SEC_KV_METADATA, SEC_PATH_POOL, TRAILER_LEN,
                  TRAILER_MAGIC, ZERO_KEY, ZSTD_MAGIC, fold_key)

DEFAULT_LIMITS = {"entries": 1_048_576, "index": 268_435_456, "total": 68_719_476_736, "ratio": 1000}
U64 = 2 ** 64
RESERVED_STEMS = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"} | {f"COM{i}" for i in range(10)} \
    | {f"LPT{i}" for i in range(10)} | {"COM¹", "COM²", "COM³", "LPT¹", "LPT²", "LPT³"}
FORBIDDEN_CHARS = set('\\<>:"|?*')


def path_violations(path):
    v = set()
    try:
        s = path.decode("utf-8")
    except UnicodeDecodeError:
        v.add("PATH-1")
        s = None
    if s is not None and not unicodedata.is_normalized("NFC", s):
        v.add("PATH-2")
    segs = path.split(b"/")
    if not 1 <= len(path) <= 4096 or any(len(g) > 255 for g in segs):
        v.add("PATH-3")
    if path.startswith(b"/") or path.endswith(b"/") or b"//" in path:
        v.add("PATH-4")
        v.add("PATH-3")  # an empty segment also breaks PATH-3's 1-255 byte segment length
    if any(g in (b".", b"..") for g in segs):
        v.add("PATH-5")
    if any(c < 0x20 or c == 0x7F for c in path):
        v.add("PATH-6")
    text = s if s is not None else path.decode("latin-1")
    if any(ch in FORBIDDEN_CHARS for ch in text):
        v.add("PATH-7")
    for g in (text.split("/")):
        if g.endswith(".") or g.endswith(" "):
            v.add("PATH-8")
        stem = g.split(".", 1)[0].rstrip(" ")
        if stem.translate(_ASCII_UPPER) in RESERVED_STEMS:
            v.add("PATH-9")
    if len(segs) > 256:
        v.add("PATH-10")
    return v


_ASCII_UPPER = {c: c - 32 for c in range(97, 123)}


def zstd_decode(frame):
    """Decode a frame of Raw/RLE blocks. Returns (content, ok_frame)."""
    if frame[:4] != ZSTD_MAGIC or len(frame) < 5:
        return b"", False
    desc = frame[4]
    if desc != 0xE0 or len(frame) < 13:
        return b"", False
    fcs = struct.unpack_from("<Q", frame, 5)[0]
    pos, out = 13, bytearray()
    while True:
        if pos + 3 > len(frame):
            return bytes(out), False
        hdr = int.from_bytes(frame[pos:pos + 3], "little")
        pos += 3
        last, btype, size = hdr & 1, (hdr >> 1) & 3, hdr >> 3
        if btype == 0:
            if pos + size > len(frame):
                return bytes(out), False
            out += frame[pos:pos + size]
            pos += size
        elif btype == 1:
            if pos + 1 > len(frame):
                return bytes(out), False
            out += frame[pos:pos + 1] * size
            pos += 1
        else:
            return bytes(out), False
        if last:
            break
    return bytes(out), pos == len(frame) and fcs == len(out)


def check(data, limits=None, mode="verify"):
    lim = dict(DEFAULT_LIMITS, **(limits or {}))
    n = len(data)
    # steps 1-7: in order, stop at the first violation
    if n < HEADER_LEN + TRAILER_LEN:
        return {"HDR-1"}
    if data[:8] != MAGIC:
        return {"HDR-2"}
    major, minor, alg = struct.unpack_from("<HHB", data, 8)
    if major != 1:
        return {"HDR-3"}
    if alg != 1:
        return {"HDR-4"}
    if data[-8:] != TRAILER_MAGIC:
        return {"TRL-1"}
    ioff, ilen = struct.unpack_from("<QQ", data, n - TRAILER_LEN)
    if ioff < HEADER_LEN or ioff + ilen + TRAILER_LEN >= U64 or ioff + ilen + TRAILER_LEN != n:
        return {"TRL-2"}
    if ilen > 2 ** 32:
        return {"LIM-2"}
    if ilen > lim["index"]:
        return {"LIM-4"}
    index = data[ioff:ioff + ilen]
    if hashlib.sha256(data[:HEADER_LEN] + index + data[n - TRAILER_LEN:n - 40]).digest() != data[n - 40:n - 8]:
        return {"TRL-3"}
    v = set()
    # step 8
    if data[13:16] != b"\x00\x00\x00":
        v.add("HDR-5")
    req, opt = struct.unpack_from("<QQ", data, 16)
    if req & ~REQ_ZSTD:
        return v | {"HDR-6"}
    known_all = (opt & ~(OPT_ENTRY_ATTRS | OPT_KV_METADATA)) == 0
    # step 9
    secs, pos = [], 0
    while pos < ilen:
        if pos + 16 > ilen:
            return v | {"SEC-1"}
        t, rs, cnt = struct.unpack_from("<IIQ", index, pos)
        size = rs * cnt
        if size >= U64 or pos + 16 + size > ilen:
            return v | {"SEC-1"}
        secs.append((t, rs, cnt, ioff + pos, index[pos + 16:pos + 16 + size]))
        pos += 16 + size
    known = {SEC_BLOB_TABLE, SEC_ENTRY_TABLE, SEC_PATH_POOL, SEC_KV_METADATA}
    if any(t not in known and t & MUST_UNDERSTAND for t, *_ in secs):
        return v | {"SEC-2"}
    types = [t for t, *_ in secs]
    rest = types[3:]
    if types[:3] != [SEC_BLOB_TABLE, SEC_ENTRY_TABLE, SEC_PATH_POOL] or any(
            a >= b for a, b in zip(rest, rest[1:])) or any(t in types[:3] for t in rest):
        return v | {"SEC-3"}
    (bt, brs, bcnt, _, bpay), (et, ers, ecnt, _, epay), (pt, prs, pcnt, _, pool) = secs[:3]
    kv = [s for s in secs[3:] if s[0] == SEC_KV_METADATA]
    if brs < BLOB_RECORD or ers < ENTRY_RECORD or prs != 1 or any(s[1] != 1 for s in kv):
        return v | {"SEC-4"}
    if req == (req & REQ_ZSTD) and known_all:
        want_e = ENTRY_RECORD_ATTRS if opt & OPT_ENTRY_ATTRS else ENTRY_RECORD
        if brs != BLOB_RECORD or ers != want_e:
            v.add("SEC-5")
    if ecnt > 2 ** 32 - 1:
        return v | {"LIM-1"}
    if ecnt > lim["entries"]:
        return v | {"LIM-3"}
    # step 10
    blobs = []
    for i in range(bcnt):
        r = bpay[i * brs:i * brs + BLOB_RECORD]
        key = r[:32]
        off, sl, rl, enc = struct.unpack_from("<QQQB", r, 32)
        blobs.append({"key": key, "offset": off, "stored": sl, "raw": rl, "enc": enc, "res": r[57:64]})
    entries = []
    for i in range(ecnt):
        r = epay[i * ers:(i + 1) * ers]
        po, pl, typ = struct.unpack_from("<QIB", r, 0)
        entries.append({"po": po, "pl": pl, "type": typ, "res": r[13:16], "key": r[16:48], "tail": r[48:]})
    for b in blobs:
        if b["res"] != b"\x00" * 7:
            v.add("BLB-1")
        if not (b["enc"] == ENC_STORED or (b["enc"] == ENC_ZSTD and req & REQ_ZSTD)):
            v.add("BLB-2")
        if b["enc"] == ENC_STORED and b["stored"] != b["raw"]:
            v.add("BLB-3")
        if b["enc"] == ENC_ZSTD and req & REQ_ZSTD and b["stored"] >= b["raw"]:
            v.add("ZST-3")
        if b["enc"] == ENC_ZSTD and req & REQ_ZSTD and b["stored"] and b["raw"] > lim["ratio"] * b["stored"]:
            v.add("LIM-6")
    expect = HEADER_LEN
    for b in blobs:
        if b["offset"] != expect:
            v.add("BLB-4")
        expect = b["offset"] + b["stored"]
    if expect != ioff or (not blobs and ioff != HEADER_LEN):
        v.add("BLB-4")
    keys = [b["key"] for b in blobs]
    if len(set(keys)) != len(keys):
        v.add("BLB-5")
    paths = []
    for e in entries:
        if e["type"] not in (DIR, FILE):
            v.add("ENT-1")
        if e["res"] != b"\x00\x00\x00":
            v.add("ENT-2")
        if e["type"] == DIR and e["key"] != ZERO_KEY:
            v.add("ENT-3")
        if e["type"] == FILE and e["key"] not in keys:
            v.add("ENT-4")
        if e["po"] + e["pl"] > len(pool):
            v.add("ENT-5")
            paths.append(None)
        else:
            paths.append(pool[e["po"]:e["po"] + e["pl"]])
    referenced = {e["key"] for e in entries if e["type"] == FILE}
    if any(k not in referenced for k in keys):
        v.add("BLB-7")
    dirs = {p for p, e in zip(paths, entries) if p is not None and e["type"] == DIR}
    for p in paths:
        if p is None:
            continue
        v |= path_violations(p)
        if b"/" in p and p.rsplit(b"/", 1)[0] not in dirs:
            v.add("ENT-6")
    real = [p for p in paths if p is not None]
    if any(a >= b for a, b in zip(real, real[1:])):
        v.add("CAN-1")
    folds = {}
    for p in real:
        folds.setdefault(fold_key(p), set()).add(p)
    if any(len(s) > 1 for s in folds.values()):
        v.add("PATH-11")
    order, seen = [], set()
    for e in entries:
        if e["type"] == FILE and e["key"] in keys and e["key"] not in seen:
            seen.add(e["key"])
            order.append(e["key"])
    first = []
    for k in keys:
        if k not in first:
            first.append(k)
    ref_part = [k for k in first if k in referenced]
    if ref_part != order or first[:len(ref_part)] != ref_part:
        v.add("CAN-2")
    acc = 0
    for e in entries:
        if e["po"] != acc:
            v.add("CAN-3")
        acc += e["pl"]
    if acc != len(pool):
        v.add("CAN-3")
    if bool(req & REQ_ZSTD) != any(b["enc"] == ENC_ZSTD for b in blobs):
        v.add("FLG-1")
    if bool(opt & OPT_ENTRY_ATTRS) != (ers >= ENTRY_RECORD_ATTRS):
        v.add("FLG-1")
    if bool(opt & OPT_KV_METADATA) != bool(kv):
        v.add("FLG-1")
    if opt & OPT_ENTRY_ATTRS and ers >= ENTRY_RECORD_ATTRS:
        for e in entries:
            secs_, nanos, mode = struct.unpack_from("<qIH", e["tail"], 0)
            if nanos >= 1_000_000_000 or mode > 0o777 or e["tail"][14:16] != b"\x00\x00":
                v.add("ATT-1")
    if kv and opt & OPT_KV_METADATA:
        if not kv_ok(kv[0][4]):
            v.add("KV-1")
    if mode in ("verify", "extract"):
        by_key = {b["key"]: b for b in blobs}
        total = sum(by_key[e["key"]]["raw"] for e in entries if e["type"] == FILE and e["key"] in by_key)
        if total > lim["total"]:
            v.add("LIM-5")
    if v or mode == "list":
        return v
    # step 11
    for b in blobs:
        stored = data[b["offset"]:b["offset"] + b["stored"]]
        if hashlib.sha256(stored).digest() != b["key"]:
            v.add("BLB-6")
            continue
        if b["enc"] == ENC_ZSTD:
            content, ok = zstd_decode(stored)
            if not ok and len(content) <= b["raw"]:
                v.add("ZST-2")
            elif len(content) != b["raw"]:
                v.add("ZST-1")
    return v


def kv_ok(payload):
    pos, prev = 0, None
    while pos < len(payload):
        if pos + 2 > len(payload):
            return False
        kl = struct.unpack_from("<H", payload, pos)[0]
        key = payload[pos + 2:pos + 2 + kl]
        pos += 2 + kl
        if pos + 4 > len(payload) or not 1 <= kl <= 255 or len(key) != kl:
            return False
        vl = struct.unpack_from("<I", payload, pos)[0]
        val = payload[pos + 4:pos + 4 + vl]
        pos += 4 + vl
        if vl > 65536 or len(val) != vl or pos > len(payload):
            return False
        try:
            key.decode("utf-8")
            val.decode("utf-8")
        except UnicodeDecodeError:
            return False
        if prev is not None and key <= prev:
            return False
        prev = key
    return pos == len(payload)
