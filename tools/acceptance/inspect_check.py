"""AC-POS-3: check `chst inspect --json` output against the raw bytes of the container.

Usage: python3.14 -I tools/acceptance/inspect_check.py INSPECT.json CONTAINER
Every leaf field is one of `fields` in the header, the data region, a section, a record or the
trailer. It checks:
1. every field's offset + length lies within the file (and so does every region and record);
2. fields don't overlap;
3. the fields together cover every byte of the file;
4. each `value` equals the bytes at its offset, by the field's kind (FORMAT_SPEC Appendix B): an
   integer is little-endian (signed for mtime_seconds) and is a decimal string beyond +-(2^53 - 1),
   hex is lowercase hex, and the PATH_POOL payload is UTF-8 text. Blob data fields have no value.
Exit 1 on any violation, or if either file can't be read or parsed. Standard library only.
"""

import json
import sys


def die(msg):
    print(f"inspect_check.py: {msg}", file=sys.stderr)
    sys.exit(1)


HEX_FIELDS = {"magic", "reserved", "key", "blob_key", "structure_hash", "trailer_magic", "extra", "attrs_reserved"}
MAX_JSON_INT = 2**53 - 1


def check_value(label, name, section, raw, v):
    """Returns a problem string, or None."""
    if name in HEX_FIELDS or (name == "payload" and section != "PATH_POOL"):
        return None if v == raw.hex() else f"{label}: value {v!r}, bytes are {raw.hex()}"
    if name == "payload":
        try:
            return None if v == raw.decode("utf-8") else f"{label}: value {v!r} isn't the payload text"
        except UnicodeDecodeError:
            return f"{label}: the payload isn't UTF-8"
    n = int.from_bytes(raw, "little", signed=name == "mtime_seconds")
    want = n if abs(n) <= MAX_JSON_INT else str(n)
    if v != want or type(v) is not type(want):
        return f"{label}: value {v!r}, bytes decode to {want!r}"
    return None


def leaf_fields(report):
    """Yields (where, region, field) for every field, and (where, region, None) for every region."""
    regions = [("header", report.get("header")), ("data", report.get("data")), ("trailer", report.get("trailer"))]
    for i, s in enumerate(report.get("sections") or []):
        regions.append((f"sections[{i}]", s))
        for r in s.get("records") or []:
            regions.append((f"sections[{i}].records[{r.get('index')}]", r))
    for where, region in regions:
        if not isinstance(region, dict):
            die(f"{where} is missing from the report")
        yield where, region, None
        for fld in region.get("fields") or []:
            yield where, region, fld


def main():
    if len(sys.argv) != 3:
        die("usage: inspect_check.py INSPECT.json CONTAINER")
    try:
        with open(sys.argv[1], encoding="utf-8") as f:
            report = json.load(f)
        with open(sys.argv[2], "rb") as f:
            data = f.read()
    except (OSError, ValueError) as e:
        die(f"can't read the inputs: {e}")
    if not isinstance(report, dict):
        die("the report isn't a JSON object")

    problems, spans = [], []
    if report.get("file_length") != len(data):
        problems.append(f"file_length is {report.get('file_length')}, the file has {len(data)} bytes")
    n_fields = 0
    for where, region, fld in leaf_fields(report):
        item = region if fld is None else fld
        label = where if fld is None else f"{where}.{fld.get('name')}"
        off, length = item.get("offset"), item.get("length")
        if not (isinstance(off, int) and isinstance(length, int) and off >= 0 and length >= 0):
            problems.append(f"{label}: offset or length isn't a non-negative integer")
            continue
        if off + length > len(data):
            problems.append(f"{label}: offset {off} + length {length} is past the end ({len(data)})")
            continue
        if fld is None:
            continue
        n_fields += 1
        if length:
            spans.append((off, off + length, label))
        if "value" in fld:
            bad = check_value(label, fld.get("name"), region.get("name"), data[off:off + length], fld["value"])
            if bad:
                problems.append(bad)

    spans.sort()
    pos = 0
    for start, end, label in spans:
        if start < pos:
            problems.append(f"{label}: overlaps the previous field (starts at {start}, previous ends at {pos})")
        elif start > pos:
            problems.append(f"bytes {pos}..{start} are in no field (next is {label})")
        pos = max(pos, end)
    if pos < len(data):
        problems.append(f"bytes {pos}..{len(data)} are in no field")
    if n_fields == 0:
        problems.append("the report has no fields")

    print(f"fields: {n_fields}, file bytes: {len(data)}")
    for p in problems[:50]:
        print(f"FAIL: {p}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
