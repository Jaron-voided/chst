"""Rule checker used only to validate the generated fixtures against FORMAT_SPEC.md.

check(data) returns the rules a container violates, as a list in the reporting order of
FORMAT_SPEC §13. The first element is the one a conforming reader must report. Steps 1-7
stop at their first violation, because later steps can't be evaluated; steps 8-11 keep
collecting, so the generator can see every co-violation, not just the reported one.
A reader that hits HDR-6 or SEC-2 evaluates nothing after step 9 (§13).

reader="extended" knows every 1.0 feature; reader="core" knows none (Core-only build).
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
ZSTD_WINDOW_MAX = 8 * 1024 * 1024
RESERVED_STEMS = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"} | {f"COM{i}" for i in range(10)} \
    | {f"LPT{i}" for i in range(10)} | {"COM¹", "COM²", "COM³", "LPT¹", "LPT²", "LPT³"}
FORBIDDEN_CHARS = set('\\<>:"|?*')
_ASCII_UPPER = {c: c - 32 for c in range(97, 123)}
READERS = {
    "extended": {"req": REQ_ZSTD, "opt": OPT_ENTRY_ATTRS | OPT_KV_METADATA,
                 "sections": {SEC_BLOB_TABLE, SEC_ENTRY_TABLE, SEC_PATH_POOL, SEC_KV_METADATA}},
    "core": {"req": 0, "opt": 0, "sections": {SEC_BLOB_TABLE, SEC_ENTRY_TABLE, SEC_PATH_POOL}},
}


def banned_char(ch):
    """PATH-6: C0, DEL, C1, and every bidirectional control (U+061C, U+200E/F, U+202A-E, U+2066-9)."""
    o = ord(ch)
    return (o < 0x20 or 0x7F <= o <= 0x9F or o in (0x061C, 0x200E, 0x200F)
            or 0x202A <= o <= 0x202E or 0x2066 <= o <= 0x2069)


def path_violations(path):
    """PATH-1..PATH-10 for one path, in §13 (g) order: 1, 2, 4, 3, 5, 6, 7, 8, 9, 10."""
    v = []
    try:
        s = path.decode("utf-8")
    except UnicodeDecodeError:
        v.append("PATH-1")
        s = None
    if s is not None and not unicodedata.is_normalized("NFC", s):
        v.append("PATH-2")
    segs = path.split(b"/")
    if path.startswith(b"/") or path.endswith(b"/") or b"//" in path:
        v.append("PATH-4")
    if not 1 <= len(path) <= 4096 or any(not 1 <= len(g) <= 255 for g in segs):
        v.append("PATH-3")
    if any(g in (b".", b"..") for g in segs):
        v.append("PATH-5")
    text = s if s is not None else path.decode("latin-1")
    if (any(banned_char(ch) for ch in text) if s is not None else any(c < 0x20 or c == 0x7F for c in path)):
        v.append("PATH-6")
    if any(ch in FORBIDDEN_CHARS for ch in text):
        v.append("PATH-7")
    names = text.split("/")
    if any((g.endswith(".") or g.endswith(" ")) and g not in (".", "..") for g in names):
        v.append("PATH-8")
    if any(g.split(".", 1)[0].rstrip(" ").translate(_ASCII_UPPER) in RESERVED_STEMS for g in names):
        v.append("PATH-9")
    if len(segs) > 256:
        v.append("PATH-10")
    return v


# ---------------------------------------------------------------- Zstandard (RFC 8878)

def zstd_header(frame):
    """Parse the frame header. Returns dict or None if malformed."""
    if len(frame) < 6 or frame[:4] != ZSTD_MAGIC:
        return None
    fhd = frame[4]
    fcs_flag, single, reserved, checksum, did_flag = fhd >> 6, (fhd >> 5) & 1, (fhd >> 3) & 1, (fhd >> 2) & 1, fhd & 3
    if reserved:
        return None
    pos, window = 5, None
    if not single:
        wd = frame[pos]
        pos += 1
        base = 1 << (10 + (wd >> 3))
        window = base + (base // 8) * (wd & 7)
    did_len = (0, 1, 2, 4)[did_flag]
    did = int.from_bytes(frame[pos:pos + did_len], "little")
    pos += did_len
    fcs_len = (1 if single else 0, 2, 4, 8)[fcs_flag]
    fcs = None
    if fcs_len:
        if pos + fcs_len > len(frame):
            return None
        fcs = int.from_bytes(frame[pos:pos + fcs_len], "little") + (256 if fcs_len == 2 else 0)
    pos += fcs_len
    if single:
        window = fcs
    return {"pos": pos, "window": window, "dict": did, "fcs": fcs, "checksum": checksum}


# XXH64 (seed 0), written here so content checksums are verified without libzstd (N19).
_P1, _P2, _P3, _P4, _P5 = (0x9E3779B185EBCA87, 0xC2B2AE3D27D4EB4F, 0x165667B19E3779F9,
                           0x85EBCA77C2B2AE63, 0x27D4EB2F165667C5)
_M = (1 << 64) - 1


def _rotl(x, r):
    return ((x << r) | (x >> (64 - r))) & _M


def _round(acc, lane):
    return (_rotl((acc + lane * _P2) & _M, 31) * _P1) & _M


def xxh64(data, seed=0):
    n, p = len(data), 0
    if n >= 32:
        v = [(seed + _P1 + _P2) & _M, (seed + _P2) & _M, seed & _M, (seed - _P1) & _M]
        while p + 32 <= n:
            for i in range(4):
                v[i] = _round(v[i], int.from_bytes(data[p + 8 * i:p + 8 * i + 8], "little"))
            p += 32
        h = (_rotl(v[0], 1) + _rotl(v[1], 7) + _rotl(v[2], 12) + _rotl(v[3], 18)) & _M
        for lane in v:
            h = ((h ^ _round(0, lane)) * _P1 + _P4) & _M
    else:
        h = (seed + _P5) & _M
    h = (h + n) & _M
    while p + 8 <= n:
        h = (_rotl(h ^ _round(0, int.from_bytes(data[p:p + 8], "little")), 27) * _P1 + _P4) & _M
        p += 8
    if p + 4 <= n:
        h = (_rotl(h ^ (int.from_bytes(data[p:p + 4], "little") * _P1 & _M), 23) * _P2 + _P3) & _M
        p += 4
    while p < n:
        h = (_rotl(h ^ (data[p] * _P5 & _M), 11) * _P1) & _M
        p += 1
    h ^= h >> 33
    h = (h * _P2) & _M
    h ^= h >> 29
    h = (h * _P3) & _M
    return h ^ (h >> 32)


def zstd_check(frame, raw_length):
    """§13 step 11 for one encoded blob (N1): header -> ZST-2; FCS != raw_length -> ZST-1;
    then one capped decoding pass, where every failure is ZST-2. Returns a rule or None."""
    h = zstd_header(frame)
    if h is None or h["dict"] != 0 or h["window"] is None or h["window"] > ZSTD_WINDOW_MAX:
        return "ZST-2"
    if h["fcs"] is not None and h["fcs"] != raw_length:
        return "ZST-1"
    block_max = min(h["window"], 128 * 1024)
    pos, produced, pieces, simple = h["pos"], 0, [], True
    while True:
        if pos + 3 > len(frame):
            return "ZST-2"  # truncated
        hdr = int.from_bytes(frame[pos:pos + 3], "little")
        pos += 3
        last, btype, size = hdr & 1, (hdr >> 1) & 3, hdr >> 3
        if btype == 3 or size > block_max:
            return "ZST-2"  # reserved block type, or Block_Size over min(Window, 128 KiB)
        body = 1 if btype == 1 else size
        if pos + body > len(frame):
            return "ZST-2"
        if btype == 2:
            simple = False
        else:
            produced += size
            if produced > raw_length:
                return "ZST-2"  # output cap: never materialise more than raw_length
            pieces.append(frame[pos:pos + size] if btype == 0 else frame[pos:pos + 1] * size)
        pos += body
        if last:
            break
    body_end = pos
    pos += 4 if h["checksum"] else 0
    if pos != len(frame):
        return "ZST-2"  # trailing bytes, a second frame, or a truncated checksum
    if simple:
        out = b"".join(pieces)
    else:
        # Compressed blocks are decoded by the standard library's libzstd binding, with the
        # checksum flag cleared so the checksum below is verified independently (XXH64).
        from compression import zstd  # decoding only; the generator never compresses with it
        plain = frame[:4] + bytes([frame[4] & ~0x04]) + frame[5:body_end]
        try:
            d = zstd.ZstdDecompressor()
            out = d.decompress(plain, max_length=raw_length + 1)
        except zstd.ZstdError:
            return "ZST-2"
    if len(out) != raw_length:
        return "ZST-2"  # short or long output
    if h["checksum"] and (xxh64(out) & 0xFFFFFFFF).to_bytes(4, "little") != frame[body_end:body_end + 4]:
        return "ZST-2"
    return None


# ---------------------------------------------------------------- the reader algorithm

def head_trailer_checks(head, trailer, n, lim):
    """Steps 1-6 from the header, the trailer and the file length only (sparse recipes)."""
    if n < HEADER_LEN + TRAILER_LEN:
        return ["HDR-1"]
    if head[:8] != MAGIC:
        return ["HDR-2"]
    major, minor, alg = struct.unpack_from("<HHB", head, 8)
    if major != 1:
        return ["HDR-3"]
    if alg != 1:
        return ["HDR-4"]
    if trailer[-8:] != TRAILER_MAGIC:
        return ["TRL-1"]
    ioff, ilen = struct.unpack_from("<QQ", trailer, 0)
    if ioff < HEADER_LEN or ioff + ilen + TRAILER_LEN >= U64 or ioff + ilen + TRAILER_LEN != n:
        return ["TRL-2"]
    if ilen > 2 ** 32:
        return ["LIM-2"]
    if ilen > lim["index"]:
        return ["LIM-4"]
    return []


def check(data, limits=None, mode="verify", reader="extended"):
    lim = dict(DEFAULT_LIMITS, **(limits or {}))
    known = READERS[reader]
    n = len(data)
    first = head_trailer_checks(data[:HEADER_LEN], data[-TRAILER_LEN:], n, lim)
    if first:
        return first
    ioff, ilen = struct.unpack_from("<QQ", data, n - TRAILER_LEN)
    index = data[ioff:ioff + ilen]
    if hashlib.sha256(data[:HEADER_LEN] + index + data[n - TRAILER_LEN:n - 40]).digest() != data[n - 40:n - 8]:
        return ["TRL-3"]
    v = []

    def add(rule):
        if rule not in v:
            v.append(rule)

    # step 8: HDR-6, then HDR-5
    req, opt = struct.unpack_from("<QQ", data, 16)
    if req & ~known["req"]:
        add("HDR-6")
        return v
    if data[13:16] != b"\x00\x00\x00":
        add("HDR-5")
    zstd_on = bool(req & REQ_ZSTD and known["req"] & REQ_ZSTD)
    attrs_on = bool(opt & OPT_ENTRY_ATTRS and known["opt"] & OPT_ENTRY_ATTRS)
    kv_known = SEC_KV_METADATA in known["sections"]
    knows_all_flags = (opt & ~known["opt"]) == 0
    # step 9: SEC-1 framing, SEC-2, SEC-3, SEC-4, SEC-5, LIM-3
    secs, pos = [], 0
    while pos < ilen:
        if pos + 16 > ilen:
            add("SEC-1")
            return v
        t, rs, cnt = struct.unpack_from("<IIQ", index, pos)
        size = rs * cnt
        if size >= U64 or pos + 16 + size > ilen:
            add("SEC-1")
            return v
        secs.append((t, rs, cnt, index[pos + 16:pos + 16 + size]))
        pos += 16 + size
    if any(t & MUST_UNDERSTAND and t not in known["sections"] for t, *_ in secs):
        add("SEC-2")
        return v
    types = [t for t, *_ in secs]
    rest = types[3:]
    if types[:3] != [SEC_BLOB_TABLE, SEC_ENTRY_TABLE, SEC_PATH_POOL] or any(
            a >= b for a, b in zip(rest, rest[1:])) or any(t in types[:3] for t in rest):
        add("SEC-3")
        return v
    (_, brs, bcnt, bpay), (_, ers, ecnt, epay), (_, prs, _, pool) = secs[:3]
    kv = [s for s in secs[3:] if s[0] == SEC_KV_METADATA and kv_known]
    if brs < BLOB_RECORD or ers < ENTRY_RECORD or prs != 1 or any(s[1] != 1 for s in kv):
        add("SEC-4")
        return v
    if knows_all_flags and (brs != BLOB_RECORD or ers != (ENTRY_RECORD_ATTRS if attrs_on else ENTRY_RECORD)):
        add("SEC-5")
    if ecnt > lim["entries"]:
        add("LIM-3")
    # step 10, items (a)-(p)
    blobs = []
    for i in range(bcnt):
        r = bpay[i * brs:i * brs + BLOB_RECORD]
        off, sl, rl, enc = struct.unpack_from("<QQQB", r, 32)
        blobs.append({"key": r[:32], "offset": off, "stored": sl, "raw": rl, "enc": enc, "res": r[57:64]})
    entries = []
    for i in range(ecnt):
        r = epay[i * ers:(i + 1) * ers]
        po, pl, typ = struct.unpack_from("<QIB", r, 0)
        entries.append({"po": po, "pl": pl, "type": typ, "res": r[13:16], "key": r[16:48], "tail": r[48:]})
    for b in blobs:  # (a)
        encoded = b["enc"] == ENC_ZSTD and zstd_on
        if b["res"] != b"\x00" * 7:
            add("BLB-1")
        if not (b["enc"] == ENC_STORED or encoded):
            add("BLB-2")
        if b["enc"] == ENC_STORED and b["stored"] != b["raw"]:
            add("BLB-3")
        if encoded and b["stored"] < 4:
            add("ZST-2")
        if encoded and b["stored"] >= b["raw"]:
            add("ZST-3")
        if encoded and b["raw"] > lim["ratio"] * b["stored"]:
            add("LIM-6")
    expect = HEADER_LEN  # (b)
    for b in blobs:
        if b["offset"] != expect:
            add("BLB-4")
        expect = b["offset"] + b["stored"]
    if expect != ioff:
        add("BLB-4")
    keys = [b["key"] for b in blobs]
    if len(set(keys)) != len(keys):  # (c)
        add("BLB-5")
    for e in entries:  # (d)
        if e["type"] not in (DIR, FILE):
            add("ENT-1")
        if e["res"] != b"\x00\x00\x00":
            add("ENT-2")
        if e["type"] == DIR and e["key"] != ZERO_KEY:
            add("ENT-3")
        if e["type"] == FILE and e["key"] not in keys:
            add("ENT-4")
    paths = []
    for e in entries:  # (e)
        if e["po"] + e["pl"] > len(pool):
            add("ENT-5")
            paths.append(None)
        else:
            paths.append(pool[e["po"]:e["po"] + e["pl"]])
    acc = 0  # (f)
    for e in entries:
        if e["po"] != acc:
            add("CAN-3")
        acc += e["pl"]
    if acc != len(pool):
        add("CAN-3")
    for p in paths:  # (g)
        if p is not None:
            for r in path_violations(p):
                add(r)
    real = [p for p in paths if p is not None]
    if any(a >= b for a, b in zip(real, real[1:])):  # (h)
        add("CAN-1")
    dirs = {p for p, e in zip(paths, entries) if p is not None and e["type"] == DIR}
    for p in paths:  # (i)
        if p is not None and b"/" in p and p.rsplit(b"/", 1)[0] not in dirs:
            add("ENT-6")
    folds = {}  # (j)
    for p in real:
        folds.setdefault(fold_key(p), set()).add(p)
    if any(len(s) > 1 for s in folds.values()):
        add("PATH-11")
    referenced = [e["key"] for e in entries if e["type"] == FILE and e["key"] in keys]
    if any(k not in referenced for k in keys):  # (k)
        add("BLB-7")
    order = list(dict.fromkeys(referenced))  # (l) CAN-2: the first |K| records hold K, in order
    if keys[:len(order)] != order:
        add("CAN-2")
    if zstd_on and not any(b["enc"] == ENC_ZSTD for b in blobs):  # (m) FLG-1, for flags the reader knows
        add("FLG-1")
    if attrs_on and ers < ENTRY_RECORD_ATTRS:  # N9: one direction only; "clear => 48" is SEC-5's job
        add("FLG-1")
    if known["opt"] & OPT_KV_METADATA and bool(opt & OPT_KV_METADATA) != bool(kv):
        add("FLG-1")
    if attrs_on and ers >= ENTRY_RECORD_ATTRS:  # (n)
        for e in entries:
            _, nanos, mode_ = struct.unpack_from("<qIH", e["tail"], 0)
            if nanos >= 1_000_000_000 or mode_ > 0o777 or e["tail"][14:16] != b"\x00\x00":
                add("ATT-1")
    if kv and known["opt"] & OPT_KV_METADATA and not kv_ok(kv[0][3]):  # (o)
        add("KV-1")
    if mode in ("verify", "extract"):  # (p)
        by_key = {b["key"]: b for b in blobs}
        if sum(by_key[e["key"]]["raw"] for e in entries if e["type"] == FILE and e["key"] in by_key) > lim["total"]:
            add("LIM-5")
    if mode == "list":
        return v
    for b in blobs:  # step 11, in blob-table order; evaluated even after earlier violations (N18)
        if b["offset"] + b["stored"] > n:
            continue  # BLB-4 already describes it; there are no bytes to hash
        stored = data[b["offset"]:b["offset"] + b["stored"]]
        if hashlib.sha256(stored).digest() != b["key"]:
            add("BLB-6")
        elif b["enc"] == ENC_ZSTD and zstd_on:
            r = zstd_check(stored, b["raw"])
            if r:
                add(r)
    return v


def kv_ok(payload):
    pos, prev = 0, None
    if not payload:
        return False  # KV-1: at least one pair
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
