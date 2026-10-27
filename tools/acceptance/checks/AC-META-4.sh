if grep -rnE 'subprocess|os\.system|os\.exec|cargo|chst_|target/|crates/' fixtures/gen; then exit 1; fi
grep -rqE 'hashlib\.sha256' fixtures/gen
# no hand-written SHA-256 (initial values and round constants)
if grep -rniE '0x6a09e667|0x428a2f98|0xbb67ae85' fixtures/gen; then exit 1; fi
test ! -s fixtures/gen/requirements.txt                          # no third-party packages at all
python3.14 -I - fixtures/gen <<'PY'
import ast, pathlib, sys
root = pathlib.Path(sys.argv[1]); local = {p.stem for p in root.rglob("*.py")}
ok = set(sys.stdlib_module_names) | local
bad = []
for f in root.rglob("*.py"):
    for n in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
        mods = [a.name for a in n.names] if isinstance(n, ast.Import) else \
               [n.module] if isinstance(n, ast.ImportFrom) and n.level == 0 else []
        bad += [f"{f}: {m}" for m in mods if m.split(".")[0] not in ok]
print("\n".join(bad)); sys.exit(1 if bad else 0)
PY
