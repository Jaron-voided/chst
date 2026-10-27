"""AC-META-3: check that every Core feature, decision and rule is traced.

Usage: python3.14 -I tools/acceptance/trace.py DESIGN.md FORMAT_SPEC.md ACCEPTANCE.md

Fails (exit 1) if any of these is missing from every `Traces:` line of ACCEPTANCE.md:
- a Core feature ID in DESIGN.md section 2.1 (`#n`, `Gn`);
- a decision D1 to D18;
- a `W-`, `EXT-` or `SEL-` rule in FORMAT_SPEC.md Appendix A.
It also fails when an input is missing or yields nothing to check, so it can't pass without checking.
The last line is `untraced: N`. Standard library only.
"""

import re
import sys

DECISIONS = [f"D{n}" for n in range(1, 19)]
ID_TOKEN = re.compile(r"#\d+[a-z]?|\b[GD]\d+[a-z]?\b|\b[A-Z]+-\d+\b")
# `LIM-3…LIM-5`, `ZST-1…3` and `AC-PACK-1 … AC-PACK-9` style ranges
RANGE = re.compile(r"\b([A-Z]+)-(\d+)\s*…\s*(?:\1-)?(\d+)\b")


def read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError as e:
        print(f"trace.py: can't read {path}: {e}", file=sys.stderr)
        print("untraced: unknown")
        sys.exit(1)


def section(text, start, end):
    """The text from the line starting `start` up to the next line starting `end`."""
    m = re.search(rf"^{re.escape(start)}.*?(?=^{re.escape(end)}|\Z)", text, re.M | re.S)
    return m.group(0) if m else ""


def core_features(design):
    block = section(design, "### 2.1 Core v1", "### 2.2")
    return re.findall(r"^\| (#\d+[a-z]?|G\d+) \|", block, re.M)


def spec_rules(spec):
    block = section(spec, "## Appendix A", "## Appendix B")
    block = block.split("Reader rules are those", 1)[0]
    rules = re.findall(r"\*\*((?:W|EXT|SEL)-\d+)\*\*", block)
    return sorted(set(rules), key=lambda r: (r.split("-")[0], int(r.split("-")[1])))


def traced(acceptance):
    out = set()
    for line in acceptance.splitlines():
        if not re.match(r"^(Core|Extended\S*) · ", line) or "Traces:" not in line:
            continue
        text = line.split("Traces:", 1)[1]
        for m in RANGE.finditer(text):
            lo, hi = int(m.group(2)), int(m.group(3))
            out.update(f"{m.group(1)}-{n}" for n in range(lo, hi + 1))
        out.update(ID_TOKEN.findall(text))
    return out


def main():
    if len(sys.argv) != 4:
        print("usage: trace.py DESIGN.md FORMAT_SPEC.md ACCEPTANCE.md", file=sys.stderr)
        print("untraced: unknown")
        return 1
    design, spec, acceptance = (read(p) for p in sys.argv[1:])
    features, rules, seen = core_features(design), spec_rules(spec), traced(acceptance)
    if not features or not rules or not seen:
        print(f"trace.py: nothing to check (features {len(features)}, rules {len(rules)}, traces {len(seen)})",
              file=sys.stderr)
        print("untraced: unknown")
        return 1
    missing = [i for i in features + DECISIONS + rules if i not in seen]
    for i in missing:
        print(f"untraced: {i}")
    print(f"checked: {len(features)} features, {len(DECISIONS)} decisions, {len(rules)} rules")
    print(f"untraced: {len(missing)}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
