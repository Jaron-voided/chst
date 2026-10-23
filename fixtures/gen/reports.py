"""Expected `chst-report/1` JSON (FORMAT_SPEC Appendix B) for list, verify and inspect.

Reports are built from the header, index and trailer bytes only; blob data is never needed.
That is what lets the sparse 5 GiB fixture have expected reports without a 5 GiB file.
"""

import struct

from chst import (DIR, ENC_ZSTD, HEADER_LEN, OPT_ENTRY_ATTRS, OPTIONAL_FLAG_NAMES,
                  REQUIRED_FLAG_NAMES, SECTION_NAMES, SEC_BLOB_TABLE, SEC_ENTRY_TABLE,
                  SEC_KV_METADATA, SEC_PATH_POOL, TRAILER_LEN)

MAX_SAFE = 2 ** 53 - 1


def num(x):
    return x if x <= MAX_SAFE else str(x)


def parse(head, index, trailer, file_length):
    """head: the 32 header bytes; index: the index bytes; trailer: the 56 trailer bytes."""
    h = {
        "magic": head[0:8], "major_version": struct.unpack_from("<H", head, 8)[0],
        "minor_version": struct.unpack_from("<H", head, 10)[0], "hash_alg": head[12],
        "reserved": head[13:16], "required_flags": struct.unpack_from("<Q", head, 16)[0],
        "optional_flags": struct.unpack_from("<Q", head, 24)[0],
    }
    index_offset, index_length = struct.unpack_from("<QQ", trailer, 0)
    secs, pos = [], 0
    while pos < len(index):
        t, rs, cnt = struct.unpack_from("<IIQ", index, pos)
        secs.append({"type": t, "record_size": rs, "record_count": cnt,
                     "offset": index_offset + pos, "payload": index[pos + 16:pos + 16 + rs * cnt]})
        pos += 16 + rs * cnt
    by_type = {s["type"]: s for s in secs}
    bt, et, pp = by_type[SEC_BLOB_TABLE], by_type[SEC_ENTRY_TABLE], by_type[SEC_PATH_POOL]
    blobs = []
    for i in range(bt["record_count"]):
        r = bt["payload"][i * bt["record_size"]:]
        off, sl, rl, enc = struct.unpack_from("<QQQB", r, 32)
        blobs.append({"key": r[:32], "offset": off, "stored_length": sl, "raw_length": rl, "encoding": enc})
    attrs = bool(h["optional_flags"] & OPT_ENTRY_ATTRS) and et["record_size"] >= 64
    entries = []
    for i in range(et["record_count"]):
        r = et["payload"][i * et["record_size"]:(i + 1) * et["record_size"]]
        po, pl, typ = struct.unpack_from("<QIB", r, 0)
        e = {"path": pp["payload"][po:po + pl], "type": typ, "blob_key": r[16:48]}
        if attrs:
            e["mtime_seconds"], e["mtime_nanos"], e["mode"] = struct.unpack_from("<qIH", r, 48)
        entries.append(e)
    return {"header": h, "sections": secs, "blobs": blobs, "entries": entries, "attrs": attrs,
            "index_offset": index_offset, "index_length": index_length,
            "structure_hash": trailer[16:48], "trailer_magic": trailer[48:56], "file_length": file_length}


def parse_bytes(data):
    n = len(data)
    io, il = struct.unpack_from("<QQ", data, n - TRAILER_LEN)
    return parse(data[:HEADER_LEN], data[io:io + il], data[n - TRAILER_LEN:], n)


def common(command):
    return {"schema": "chst-report/1", "command": command, "ok": True, "error": None, "warnings": []}


def list_report(c, core_view=False):
    blobs = {b["key"]: b for b in c["blobs"]}
    out = []
    for e in c["entries"]:
        d = {"path": e["path"].decode("utf-8"), "type": "dir" if e["type"] == DIR else "file"}
        if e["type"] != DIR:
            b = blobs[e["blob_key"]]
            d.update({"size": num(b["raw_length"]), "stored_size": num(b["stored_length"]),
                      "encoding": "zstd" if b["encoding"] == ENC_ZSTD else "stored", "blob": b["key"].hex()})
        if c["attrs"] and not core_view:
            d.update({"mtime_seconds": e["mtime_seconds"], "mtime_nanos": e["mtime_nanos"], "mode": e["mode"]})
        out.append(d)
    r = common("list")
    r["entries"] = out
    return r


def flag_names(value, names):
    return [names[bit] for bit in sorted(names) if value & bit]


def summary(c):
    blobs = {b["key"]: b for b in c["blobs"]}
    files = [e for e in c["entries"] if e["type"] != DIR]
    return {
        "entries": len(c["entries"]),
        "files": len(files),
        "directories": len(c["entries"]) - len(files),
        "blobs": len(c["blobs"]),
        "stored_bytes": num(sum(b["stored_length"] for b in c["blobs"])),
        "raw_bytes": num(sum(b["raw_length"] for b in c["blobs"])),
        "extracted_bytes": num(sum(blobs[e["blob_key"]]["raw_length"] for e in files)),
        "required_flags": flag_names(c["header"]["required_flags"], REQUIRED_FLAG_NAMES),
        "optional_flags": flag_names(c["header"]["optional_flags"], OPTIONAL_FLAG_NAMES),
    }


def verify_report(c):
    r = common("verify")
    r["summary"] = summary(c)
    return r


def field(name, offset, length, value=None):
    f = {"name": name, "offset": num(offset), "length": num(length)}
    if value is not None:
        f["value"] = value if isinstance(value, str) else num(value)
    return f


def inspect_report(c):
    h = c["header"]
    header = {"offset": 0, "length": HEADER_LEN, "fields": [
        field("magic", 0, 8, h["magic"].hex()),
        field("major_version", 8, 2, h["major_version"]),
        field("minor_version", 10, 2, h["minor_version"]),
        field("hash_alg", 12, 1, h["hash_alg"]),
        field("reserved", 13, 3, h["reserved"].hex()),
        field("required_flags", 16, 8, h["required_flags"]),
        field("optional_flags", 24, 8, h["optional_flags"]),
    ]}
    data_len = c["index_offset"] - HEADER_LEN
    data = {"offset": HEADER_LEN, "length": num(data_len),
            "fields": [field(f"blob[{i}].data", b["offset"], b["stored_length"]) for i, b in enumerate(c["blobs"])]}
    sections = []
    for s in c["sections"]:
        base, rs, cnt = s["offset"], s["record_size"], s["record_count"]
        sec = {"type": f"0x{s['type']:08x}", "name": SECTION_NAMES.get(s["type"], "unknown"),
               "offset": num(base), "length": num(16 + rs * cnt), "record_size": rs, "record_count": num(cnt),
               "fields": [field("type", base, 4, s["type"]), field("record_size", base + 4, 4, rs),
                          field("record_count", base + 8, 8, cnt)],
               "records": []}
        p = s["payload"]
        if s["type"] == SEC_BLOB_TABLE:
            for i in range(cnt):
                o, r = base + 16 + i * rs, p[i * rs:(i + 1) * rs]
                off, sl, rl, enc = struct.unpack_from("<QQQB", r, 32)
                fs = [field("key", o, 32, r[:32].hex()), field("offset", o + 32, 8, off),
                      field("stored_length", o + 40, 8, sl), field("raw_length", o + 48, 8, rl),
                      field("encoding", o + 56, 1, enc), field("reserved", o + 57, 7, r[57:64].hex())]
                if rs > 64:
                    fs.append(field("extra", o + 64, rs - 64, r[64:].hex()))
                sec["records"].append({"index": i, "offset": num(o), "length": rs, "fields": fs})
        elif s["type"] == SEC_ENTRY_TABLE:
            for i in range(cnt):
                o, r = base + 16 + i * rs, p[i * rs:(i + 1) * rs]
                po, pl, typ = struct.unpack_from("<QIB", r, 0)
                fs = [field("path_offset", o, 8, po), field("path_length", o + 8, 4, pl),
                      field("type", o + 12, 1, typ), field("reserved", o + 13, 3, r[13:16].hex()),
                      field("blob_key", o + 16, 32, r[16:48].hex())]
                if c["attrs"]:
                    ms, mn, mode = struct.unpack_from("<qIH", r, 48)
                    fs += [field("mtime_seconds", o + 48, 8, ms),
                           field("mtime_nanos", o + 56, 4, mn), field("mode", o + 60, 2, mode),
                           field("attrs_reserved", o + 62, 2, r[62:64].hex())]
                elif rs > 48:
                    fs.append(field("extra", o + 48, rs - 48, r[48:].hex()))
                sec["records"].append({"index": i, "offset": num(o), "length": rs, "fields": fs})
        else:
            try:
                val = p.decode("utf-8") if s["type"] in (SEC_PATH_POOL, SEC_KV_METADATA) else p.hex()
            except UnicodeDecodeError:
                val = p.hex()
            if s["type"] == SEC_KV_METADATA:
                val = p.hex()
            if len(p):
                sec["fields"].append(field("payload", base + 16, len(p), val))
        sections.append(sec)
    t0 = c["file_length"] - TRAILER_LEN
    trailer = {"offset": num(t0), "length": TRAILER_LEN, "fields": [
        field("index_offset", t0, 8, c["index_offset"]),
        field("index_length", t0 + 8, 8, c["index_length"]),
        field("structure_hash", t0 + 16, 32, c["structure_hash"].hex()),
        field("trailer_magic", t0 + 48, 8, c["trailer_magic"].hex()),
    ]}
    r = common("inspect")
    r.update({"file_length": num(c["file_length"]), "header": header, "data": data,
              "sections": sections, "trailer": trailer})
    return r
