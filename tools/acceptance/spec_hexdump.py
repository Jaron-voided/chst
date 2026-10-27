"""AC-META-6: parse the hex dump of FORMAT_SPEC.md section 18.3 back into bytes.

Usage: python3.14 -I tools/acceptance/spec_hexdump.py FORMAT_SPEC.md > bytes
Writes the bytes to stdout. Fails (exit 1, nothing written) if the section or its dump is missing,
an offset isn't contiguous, a line isn't 16 bytes (except the last), or an ASCII gutter doesn't
match its bytes. Standard library only.
"""

import re
import sys

LINE = re.compile(r"^([0-9a-f]{8})  ((?:[0-9a-f]{2} ?)+?) *\|(.*)\|$")


def fail(msg):
    print(f"spec_hexdump.py: {msg}", file=sys.stderr)
    sys.exit(1)


def main():
    if len(sys.argv) != 2:
        fail("usage: spec_hexdump.py FORMAT_SPEC.md")
    try:
        with open(sys.argv[1], encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        fail(f"can't read {sys.argv[1]}: {e}")
    m = re.search(r"^### 18\.3 .*?^```\n(.*?)^```$", text, re.M | re.S)
    if not m:
        fail("no hex dump under '### 18.3'")
    out = bytearray()
    short_seen = False
    for n, line in enumerate(m.group(1).splitlines(), 1):
        lm = LINE.match(line)
        if not lm:
            fail(f"dump line {n} isn't a hex dump line: {line!r}")
        if short_seen:
            fail(f"dump line {n} follows a short line")
        offset, hexpart, gutter = int(lm.group(1), 16), lm.group(2).split(), lm.group(3)
        if offset != len(out):
            fail(f"dump line {n}: offset {offset:#x}, expected {len(out):#x}")
        data = bytes(int(h, 16) for h in hexpart)
        if len(data) > 16:
            fail(f"dump line {n} has {len(data)} bytes")
        short_seen = len(data) < 16
        if gutter != "".join(chr(b) if 0x20 <= b < 0x7F else "." for b in data):
            fail(f"dump line {n}: the ASCII gutter doesn't match the bytes")
        out += data
    if not out:
        fail("the hex dump is empty")
    sys.stdout.buffer.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
