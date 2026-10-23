# Chst — Acceptance Criteria

> Status: **DRAFT for independent review.** Every criterion below has a runnable check and
> an observable pass condition. Statements of success without a passing `check.sh` report
> do not count.
> References: feature IDs (`#n`, `Gn`) and decisions (`Dn`) are in [`DESIGN.md`](DESIGN.md);
> rule IDs (`HDR-1`, …) are in [`FORMAT_SPEC.md`](FORMAT_SPEC.md) Appendix A.

## 1. How to run

| Command | Runs | Typical exit |
|---|---|---|
| `./check.sh` | **Fast mode:** every applicable ID except the full-only ones (AC-ROB-4, AC-ROB-4W, AC-ROB-7) and the done-only one (AC-XP-1), which are NOT RUN | 2 |
| `./check.sh --full` | **Full mode:** also runs the full-only IDs. AC-XP-1 is NOT RUN. | 2 (AC-XP-1 NOT RUN) |
| `./check.sh --done <ci-run-id>` | **Done mode:** imports every ID's per-OS status from the three CI full-run reports of `<ci-run-id>`, then runs AC-XP-1 | 0 when done |
| `./check.sh --only ID,ID` | Only the named IDs; every other ID is NOT RUN (development aid) | 2 |
| `./check.sh --list-ids` | Prints every acceptance ID it implements, one per line | 0 |
| `./check.sh --self-test` | Runs the harness's built-in self-test IDs (AC-META-7) instead of acceptance IDs | 0 |

### 1.1 Statuses and exit codes

| Status | Meaning |
|---|---|
| **PASS** | The check ran and its pass condition held |
| **FAIL** | The check failed, **or** is missing, **or** can't run (a tool is missing, the build fails, the environment is inadequate), **or** ran zero tests |
| **NOT RUN** | The check needs a mode that wasn't selected: `--full` for full-only IDs, `--done` for AC-XP-1, or `--only` excluded it |
| **N/A** | Only where this document fixes it in advance: (a) every Extended-tier ID while `CURRENT_CUT = Core` (§2), and (b) an ID whose **OS** line excludes the current OS. `check.sh` never decides N/A on its own; it reads only these two facts. |

| Exit code | When |
|---|---|
| 0 | Every applicable ID passes. |
| 2 | Nothing failed, but something was NOT RUN. |
| 1 | Any FAIL. |

**Report.** Every run writes `target/acceptance/report.json`:

```json
{
  "schema": "chst-acceptance/1",
  "mode": "fast | full | done | only | self-test",
  "cut": "core | extended",
  "os": "linux | macos | windows",
  "commit": "<git sha>",
  "dirty": false,
  "results": [
    {"id": "AC-POS-1", "status": "PASS | FAIL | NOT RUN | N/A", "exit_code": 0,
     "duration_s": 1.2, "command": "./check.sh --only AC-POS-1",
     "log": "target/acceptance/logs/AC-POS-1.log"}
  ]
}
```

- Each check's combined stdout and stderr is saved to its `log` file.
- `check.sh` runs each check **exactly as written below**, under `bash -euo pipefail`. On
  Windows CI it runs under the runner's bash (Git Bash, `shell: bash`).
- **Local versus CI evidence.** The owner develops and runs checks locally on Linux (WSL).
  - Run them from the Linux filesystem, not `/mnt/<drive>`, which has Windows filesystem
    semantics.
  - Local runs count as Linux evidence only. **The only evidence for macOS and Windows is a
    CI run,** linked from `EVIDENCE.md` (§2.1).
- **CI** (DESIGN.md D17) runs fast mode on every push and pull request, and full mode on
  manual trigger. A job fails on exit 1. A fast job succeeds on exit 2. A full job succeeds
  on exit 2 only when AC-XP-1 is the sole NOT RUN.

### 1.2 Conventions used by checks

| Name | Meaning |
|---|---|
| `$CHST` | `target/release/chst`, the full build with default features |
| `$CHST_CORE` | A build with `--no-default-features`. Core only: Extended features are behind Cargo features that are on by default |
| `$CHST_OS` | `linux`, `macos` or `windows`, as detected by `check.sh` |
| `$FX` | `fixtures` |
| `python3.14` | Every Python invocation, always by that explicit name (D16). The system `python3` may be older. CI provides `python3.14` on every runner. |
| `$GEN` | `python3.14 -I fixtures/gen/gen.py` |
| `$W` | A **fresh temporary directory** that `check.sh` creates for each ID (`mktemp -d`) and removes after the check, whatever its result |
| `$CHST_BIG_ROOT` | A parent directory on a volume with enough free space, set by the CI workflow per runner (§1.3); locally it defaults to the system temp directory. Checks never write into it directly: they create a fresh `mktemp -d` under it, and remove it on exit. |
| `jqn FILE` | `jq -S 'walk(if type=="object" then del(.message) else . end)' FILE`: normalised JSON for comparison (FORMAT_SPEC Appendix B) |
| `expect_exit N CMD…` | Runs CMD and fails unless its exit code is exactly N |
| *(no `!` negation)* | Scripts run under `bash -e`, which **ignores the failure of a `!`-negated command** unless it's the script's last command. So a check that must fail when something is found is written as `if CMD; then exit 1; fi`, never `! CMD`. `check.sh` rejects any check script containing a line that starts with `! `. |
| `cargo_test_nonempty ARGS…` | **The zero-test guard.** Runs `cargo test ARGS…`, then sums the `N passed` counts of every `test result:` line. It fails if cargo exits non-zero, if there's no `test result:` line, or if the sum is 0. That last case covers an empty test target, a filter matching nothing, and an all-ignored suite. **Every check that runs cargo tests uses it.** |
| `sha256 FILE` | Prints the file's lowercase hex SHA-256: `sha256sum`, or `shasum -a 256` on macOS |
| `mk_sparse FILE SIZE` | Creates a sparse file of SIZE bytes. On Linux and macOS this is `truncate -s`. On Windows: create the file empty, run `fsutil sparse setflag` on it, then `truncate -s`. |
| `free_bytes DIR` | Free bytes on DIR's volume (`df -Pk`) |
| `fixture_file EXPECT.json` | Prints the path of the container an `expect.json` describes: the sibling `.chst`, or, if only a sibling `.recipe.json` exists (sparse recipes, such as `core/invalid/LIM-2`), a sparse file materialised from it under `$W` (`mk_sparse` + `$GEN materialize-sparse`) |
| `$CHST_DET_SEED` | Seed for `$GEN materialize --reverse`. The default is fixed (`chst-det-1`), and it's printed to stderr, so a failing determinism run can be reproduced. |

Rust tests that extract or pack files use only temporary directories (`tempfile`, D15).

**Fixture layout.** Everything under `fixtures/` is produced by the generator in
`fixtures/gen/` (V1), which builds it directly from FORMAT_SPEC.md. The generator uses only
the Python standard library, for Extended too. SHA-256 comes from `hashlib`, and it writes
its own Zstandard frames (D15).

- **Valid fixtures:** `fixtures/core/valid/<name>/` holds:
  - `tree.json`: the source tree as data, so empty directories and awkward names survive git;
  - `container.chst`;
  - `list.json`, `verify.json` and `inspect.json`: the expected reports.
- **Invalid fixtures:** `fixtures/core/invalid/<RULE>[-<sub>].chst` (or `.recipe.json` for a
  sparse one) plus `<RULE>[-<sub>].expect.json`.
- **Each directory's `expect.json` schema (F44).** In every schema, `detail` is the exact
  detail code that a reader reporting in FORMAT_SPEC §13's order must give.

  | Directory | Fields |
  |---|---|
  | `core/invalid/`, `extended/invalid/` | `rule`, `category`, `detail`, `exit`, `base`, `mutation`; optionally `args` (CLI limit flags) and `also_violates` (detail codes of rules also broken but reported later in §13's order; informational only, never compared) |
  | `core/attacks/` | `rule`, `category`, `detail`, `exit` |
  | `core/hostile/` | `rule`, `category`, `detail`, `exit`, `base`, `mutation` |
  | `core/hostile64/` | as hostile, plus `details`: a one-element list for AC-ROB-8 |
  | `core/extract-cases/` | `exit`, `note`; plus `rule`, `category`, `detail` when the case fails. A sibling `<name>.tree.json` describes valid trees. |
  | `compat/` | `exit`, `detail` (`null` when the exit is 0), `note`. Exit-0 fixtures also have `<name>.list.json`, `.verify.json` and `.inspect.json`: the **Core-only reader's** reports (FORMAT_SPEC Appendix B, "What the reader implements shapes its report"). |
- `fixtures/core/valid/`, `fixtures/core/sparse/` and `fixtures/extended/valid/` hold
  directories, as above (sparse: `recipe.json` instead of `container.chst` and `tree.json`).
- `fixtures/fuzz-regressions/<target>/`: every input that ever crashed a fuzz target.
- `fixtures/MANIFEST.sha256`: a `sha256sum`-format listing of every other file under
  `fixtures/`, including `fixtures/gen/`.

Generator commands used by checks:
- `$GEN --out DIR` regenerates everything except `gen/` itself.
- `$GEN materialize TREE.json DIR [--reverse]` creates a tree on disk. It never merges two
  entries: a name that already exists is an error. `--reverse` creates directories
  deepest-first and files in reverse order, and sets seeded random mtimes and modes
  (`$CHST_DET_SEED`), to stress determinism.
- `$GEN materialize-sparse RECIPE.json FILE` writes a recipe's head bytes at offset 0 and
  its tail bytes at the end of an existing sparse FILE, without filling the hole.
- `$GEN synth-entries N FILE` and `$GEN synth-amplify N SIZE FILE` build large synthetic
  containers on demand.

### 1.3 CI runners and heavy checks

These are the decisions for each runner. **Feasibility is unconfirmed until the first full
CI run.**

| Check | ubuntu-latest (x64) | macos-latest (arm64) | windows-latest (x64) |
|---|---|---|---|
| AC-ROB-4: cargo-fuzz, 10 minutes per target | Runs | Runs | Doesn't apply (the OS line excludes it). AC-ROB-4W runs instead: the fallback, **approved provisionally until the first full CI run**. That run also tries cargo-fuzz on Windows, as a non-gating, logged workflow step, so the owner can decide whether to switch. |
| AC-ROB-7: large-file round-trip | 5 GiB (about 10 GiB peak disk). The workflow frees preinstalled toolchains first. | **4 GiB + 1 MiB** (about 8 GiB peak) | 5 GiB if `$CHST_BIG_ROOT` has at least 12 GiB free, otherwise 4 GiB + 1 MiB. The size used is logged. |

- **No paid runners.**
- A check that can't run on a runner reports **FAIL**, never N/A.
- Moving a check to another OS, or changing a variant, is an open item. Until `plan-v1` it
  goes in DESIGN.md §9; from `plan-v1` on, under "Needs decision" in PROGRESS.md.
- Either size still puts every size and offset field above 2³².

## 2. Definition of Done

**This section is the single definition of done.** `CLAUDE.md` refers to it.

```
CURRENT_CUT = Core
```

The cut is **done** when `./check.sh --done <ci-run-id>` exits 0, where `<ci-run-id>` is a
manually triggered full-mode CI run of one commit on Linux, macOS and Windows. That
requires all of the following, and AC-XP-1 checks every item:

1. All three reports are for the same commit, with `mode: full` and `dirty: false`, and
   that commit is the CI run's head commit.
2. In every report, every ID is PASS, or N/A as fixed in §1.1. The only exception is
   AC-XP-1, which is NOT RUN in the per-OS reports.
3. `EVIDENCE.md` has one row per acceptance ID that matches those statuses, with that
   commit and the CI run link (§2.1).

Changing `CURRENT_CUT` to `Extended` is an owner decision. After that, every Extended ID
applies, and the same rule defines Extended done.

**Fuzz findings:** any crash, timeout or out-of-memory found by any fuzz run, including
optional longer runs, MUST be minimised and added to `fixtures/fuzz-regressions/`. The fix
isn't done until AC-ROB-5 passes with it.

Which files are protected, and who may change them, is defined only in `CLAUDE.md`.

### 2.1 EVIDENCE.md

`EVIDENCE.md` (repo root) has **exactly one row per acceptance ID**, in the order of this
document:

```
| ID | Linux | macOS | Windows | Command | Commit | CI run |
| AC-POS-1 | PASS | PASS | N/A | ./check.sh --only AC-POS-1 | <sha> | https://github.com/<owner>/<repo>/actions/runs/<id> |
```

- Status cells use exactly PASS, FAIL, NOT RUN or N/A. Rows are updated from
  `report.json`, and a status is never entered for a check that didn't run.
- **macOS and Windows statuses MUST come from the CI run in that row's "CI run" column.**
  The Linux status may come from that run or from a local WSL run. A local run is noted as
  `local` in the CI column, and a macOS or Windows status can't come from it.
- The Command column holds the command that reproduces the result.

## 3. Criteria

Each criterion lists four things:
- its **tier**, either Core or Extended:<feature>;
- the **OS** it applies to; an OS it excludes gives N/A there;
- its **mode**: fast, full-only, or done-only;
- what it **traces to**.

Pass means the shown script exits 0, unless stated otherwise. Each script runs in its own
fresh `$W`.

### 3.1 Meta: evidence integrity

#### AC-META-1 — `check.sh` implements exactly the criteria in this document
Core · OS all · fast · Traces: Layer B
```sh
diff <(./check.sh --list-ids | sort) \
     <(grep -oE '^#### AC-[A-Z0-9-]+' ACCEPTANCE.md | cut -c6- | sort)
```
Pass: empty diff.

#### AC-META-2 — Fixtures are untampered and fully listed
Core · OS all · fast · Traces: V1, #28
```sh
test "$(sha256 fixtures/MANIFEST.sha256)" = "$PINNED_MANIFEST_HASH"
(cd fixtures && { sha256sum --check --quiet MANIFEST.sha256 2>/dev/null || shasum -a 256 -c -s MANIFEST.sha256; })
diff <(cd fixtures && find . -type f ! -name MANIFEST.sha256 | sed 's|^\./||' | sort) \
     <(sed 's/^[0-9a-f]* [ *]//' fixtures/MANIFEST.sha256 | sort)
```
`$PINNED_MANIFEST_HASH` is the value in §5. The manifest covers `fixtures/gen/` as well.
Pass: exit 0.

#### AC-META-3 — Every Core feature, decision and rule is traced
Core · OS all · fast · Traces: Layer B
```sh
python3.14 -I tools/acceptance/trace.py DESIGN.md FORMAT_SPEC.md ACCEPTANCE.md
```
Pass: exit 0 and the final line is `untraced: 0`.

`trace.py` MUST fail if any of the following is missing from at least one `Traces:` line:
- a Core feature ID in DESIGN.md §2.1;
- every decision `D1`–`D18`;
- every `W-`, `EXT-` or `SEL-` rule in FORMAT_SPEC Appendix A.

Reader rules are covered collectively by AC-NEG-1.

#### AC-META-4 — The fixture generator is independent and uses only approved libraries
Core · OS all · fast · Traces: V1, D6, D15
```sh
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
```
Pass: exit 0.
- The generator uses only the Python standard library: SHA-256 from `hashlib`, NFC from
  `unicodedata`, and its own Zstandard frame writer. `requirements.txt` stays empty.
- It contains no hand-written SHA-256: the third line looks for SHA-256's initial values
  and round constants.
- It never invokes or reads the Rust code.

#### AC-META-5 — Fixtures regenerate exactly
Core · OS linux · fast · Traces: V1, D9
```sh
$GEN --out "$W/fx" && diff -r -x gen "$W/fx" fixtures
```
Pass: empty diff.

#### AC-META-6 — The worked example in FORMAT_SPEC §18 is the golden fixture
Core · OS all · fast · Traces: V1, #14, D1, D3, D4, D6
```sh
f=$FX/core/valid/worked-example/container.chst
test "$(wc -c < $f | tr -d ' ')" = 556
test "$(sha256 $f)" = 1939236c4b281cf517f7ca1b1746b93b75a0e6afb485107f56d1eea1a7e33332
python3.14 -I tools/acceptance/spec_hexdump.py FORMAT_SPEC.md | cmp - $f
```
`spec_hexdump.py` parses the §18.3 hex dump back into bytes. Pass: exit 0.

#### AC-META-7 — The harness reports FAIL for empty, missing and unrunnable checks
Core · OS all · fast · Traces: Layer B, D16
```sh
./check.sh --self-test > /dev/null || true
r=target/acceptance/report.json
jq -e '.mode == "self-test"' $r
for id in SELFTEST-EMPTY-TARGET SELFTEST-ZERO-FILTER SELFTEST-MISSING-CHECK SELFTEST-CANT-RUN; do
  jq -e --arg id $id '.results[] | select(.id == $id) | .status == "FAIL"' $r
done
jq -e '.results[] | select(.id == "SELFTEST-PASS") | .status == "PASS"' $r
```
`--self-test` builds a throwaway cargo crate in a fresh temporary directory and runs five
synthetic IDs through the same code path as real IDs:

| Self-test ID | Check it runs | Required status |
|---|---|---|
| `SELFTEST-EMPTY-TARGET` | `cargo_test_nonempty --test empty`, where the test file is empty | FAIL |
| `SELFTEST-ZERO-FILTER` | `cargo_test_nonempty --test one -- no_such_filter` | FAIL |
| `SELFTEST-MISSING-CHECK` | An ID with no check implemented | FAIL |
| `SELFTEST-CANT-RUN` | A check whose command doesn't exist | FAIL |
| `SELFTEST-PASS` | `cargo_test_nonempty --test one`, with one passing test | PASS |

The self-test IDs never appear in `--list-ids` or in normal reports. Pass: exit 0.

### 3.2 Engineering

#### AC-ENG-1 — Clean build, lint and format
Core · OS all · fast · Traces: #27
```sh
cargo build --release --workspace --locked
cargo build --release -p chst-cli --no-default-features --locked
cargo clippy --workspace --all-targets --locked -- -D warnings
cargo fmt --all --check
```

#### AC-ENG-2 — The format crate has no filesystem access and no unsafe code
Core · OS all · fast · Traces: D13, #26
```sh
grep -q '#!\[forbid(unsafe_code)\]' crates/chst-format/src/lib.rs
if grep -rnE 'std::fs|std::env|std::process|std::net|unsafe' crates/chst-format/src; then exit 1; fi
cargo tree -p chst-format -e normal --depth 1 --prefix none --no-default-features \
  | tail -n +2 | awk '{print $1}' | sort -u > "$W/deps"
diff "$W/deps" <(printf 'sha2\nunicode-normalization\n')
```
Pass: exit 0, meaning the Core build's direct dependencies are exactly `sha2` and
`unicode-normalization`.

#### AC-ENG-3 — The CLI is thin
Core · OS all · fast · Traces: D13, #27
```sh
cargo tree -p chst-cli -e normal --depth 1 --prefix none > "$W/cli-deps"
if grep -E '^(sha2|unicode-normalization|zstd) ' "$W/cli-deps"; then exit 1; fi
```
Pass: exit 0. The CLI reaches hashing, normalisation and compression only through
`chst-format` and `chst-fs`.

#### AC-ENG-4 — The test suite passes
Core · OS all · fast · Traces: #27
```sh
cargo_test_nonempty --workspace --locked --release
```

#### AC-ENG-5 — Every direct dependency is on the approved list
Core · OS all · fast · Traces: D15
```sh
allow='chst-format|chst-fs|chst-cli|chst-fuzz|sha2|unicode-normalization|rustix|windows-sys|lexopt|serde_json|zstd|tempfile|libfuzzer-sys'
git ls-files --error-unmatch Cargo.lock fuzz/Cargo.lock > /dev/null       # lockfiles are committed
for m in Cargo.toml fuzz/Cargo.toml; do
  cargo tree --manifest-path $m --workspace --target all --all-features -e normal,build,dev \
    --depth 1 --prefix none | awk 'NF {print $1}' | sort -u > "$W/direct"
  if grep -vxE "$allow" "$W/direct"; then exit 1; fi
done
```
Pass: exit 0. Both lockfiles are committed, and every build uses `--locked`, so every
version, transitive ones included, is pinned. Python dependencies are checked by
AC-META-4, and TypeScript dependencies by AC-X-TS-3.

#### AC-ENG-6 — The pinned environment is the one in use
Core · OS all · fast · Traces: D16
```sh
grep -qxE 'channel = "1\.99\.1"' rust-toolchain.toml
test "$(rustc --version | cut -d' ' -f2)" = 1.99.1
grep -qxE 'channel = "nightly-2026-10-01"' fuzz/rust-toolchain.toml
command -v python3.14 > /dev/null
python3.14 -I -c 'import sys, unicodedata, compression.zstd       # N19: the generator needs compression.zstd
assert sys.version_info[:2] == (3, 14), sys.version
assert unicodedata.unidata_version == "16.0.0", unicodedata.unidata_version'
jq --version | grep -qE '^jq-1\.([7-9]|[1-9][0-9])'
```
Pass: exit 0. The Node pin is checked by AC-X-TS-3, which applies only to the Extended cut.

#### AC-ENG-8 — Every reader uses exactly the Unicode 16.0 tables
Core · OS all · fast · Traces: D8, D16, PATH-2
```sh
cargo_test_nonempty --release -p chst-format --test unicode_tables
```
The test asserts that `unicode_normalization::UNICODE_VERSION` is `(16, 0, 0)`, and that
the path from `core/invalid/PATH-2-unicode16` is judged not NFC (F12). The Python side is
checked by AC-ENG-6 and the TypeScript side by AC-X-TS-3. AC-NEG-2 then checks the fixture
end to end.

#### AC-ENG-7 — Unsafe code only where D18 allows it, and justified there
Core · OS all · fast · Traces: D18, #26
```sh
fsw=crates/chst-fs/src/lib.rs; ca=crates/chst-format/tests/support/counting_alloc.rs
ca_users='crates/chst-format/tests/hostile_sizes.rs crates/chst-format/tests/zstd_bombs.rs'
# 1. forbid in every crate root except chst-fs and the two counting-allocator test crates
for f in $(ls crates/*/src/lib.rs crates/*/src/main.rs crates/*/tests/*.rs 2>/dev/null); do
  case " $fsw $ca_users " in *" $f "*) continue;; esac
  grep -qx '#!\[forbid(unsafe_code)\]' "$f" || { echo "missing forbid: $f"; exit 1; }
done
# 2. chst-fs: deny + SAFETY lints; exactly one allow, on the Windows module
grep -qx '#!\[deny(unsafe_code)\]' $fsw
grep -qx '#!\[deny(clippy::undocumented_unsafe_blocks, clippy::missing_safety_doc)\]' $fsw
grep -B1 -A1 'allow(unsafe_code)' $fsw | grep -q 'cfg(windows)'
grep -A1 'allow(unsafe_code)' $fsw | grep -qE '^\s*mod windows;'
# 3. the counting-allocator exception: deny in its two users, allow only in the named file
for f in $ca_users; do grep -qx '#!\[deny(unsafe_code)\]' "$f"; grep -q 'counting_alloc' "$f"; done
grep -qx '#!\[allow(unsafe_code)\]' $ca
test "$(grep -rln 'allow(unsafe_code)' crates fuzz --include='*.rs' | sort | tr '\n' ' ')" = "$ca $fsw "
# 4. every unsafe item in the allocator file is preceded by a SAFETY comment
awk '/unsafe/ && !/allow\(unsafe_code\)/ { if (prev !~ /SAFETY:/) { print FILENAME": "FNR": undocumented unsafe"; bad=1 } } { if ($0 !~ /^\s*$/) prev=$0 } END { exit bad }' $ca
# 5. the word unsafe appears nowhere else
grep -rnw 'unsafe' crates fuzz --include='*.rs' > "$W/unsafe-lines" || true
if grep -vE "^($fsw:.*(deny|allow)\(unsafe_code\)|crates/chst-fs/src/windows(\.rs|/)|$ca:|crates/chst-format/tests/(hostile_sizes|zstd_bombs)\.rs:.*deny\(unsafe_code\))" "$W/unsafe-lines"; then exit 1; fi
# 6. fuzz targets: forbid, or the documented exemption (D18 exception 2)
for f in $(ls fuzz/fuzz_targets/*.rs); do
  grep -qx '#!\[forbid(unsafe_code)\]' "$f" || grep -q 'unsafe_code' fuzz/FORBID_EXEMPTION.txt || { echo "fuzz target without forbid or exemption: $f"; exit 1; }
done
```
Pass: exit 0.
- Every crate root and integration-test crate has `forbid(unsafe_code)`, except `chst-fs`
  and the two test crates that use the counting allocator.
- `chst-fs` denies unsafe code, and the `// SAFETY:` lints, at crate level. Its only `allow`
  is on `#[cfg(windows)] mod windows;`.
- The only other `allow(unsafe_code)` is in `crates/chst-format/tests/support/counting_alloc.rs`,
  where every `unsafe` line follows a `// SAFETY:` comment.
- Fuzz targets carry `forbid`, unless `fuzz/FORBID_EXEMPTION.txt` records the compiler's
  `unsafe_code` lint error (D18 exception 2).
- The clippy `// SAFETY:` lints for the Windows module run on the Windows runner through
  AC-ENG-1.

### 3.3 Positive conformance (V2)

#### AC-POS-1 — Pack reproduces every golden container byte for byte
Core · OS all · fast · Traces: #1, #15, #17, #19, #21, W-1, D2, D9, V1
```sh
for d in $FX/core/valid/*/; do
  rm -rf "$W/t" "$W/o.chst"
  $GEN materialize "$d/tree.json" "$W/t"
  $CHST pack "$W/t" -o "$W/o.chst"
  cmp "$W/o.chst" "$d/container.chst"
done
```

#### AC-POS-2 — `list`, `verify` and `inspect` JSON match exactly
Core · OS all · fast · Traces: #2, #4, #5, #8, G9
```sh
for d in $FX/core/valid/*/; do for c in list verify inspect; do
  expect_exit 0 $CHST $c --json "$d/container.chst" > "$W/r.json"
  diff <(jqn "$W/r.json") <(jqn "$d/$c.json")
done; done
```

#### AC-POS-3 — `inspect` offsets and values agree with the raw bytes
Core · OS all · fast · Traces: #5, #14
```sh
for d in $FX/core/valid/*/; do
  $CHST inspect --json "$d/container.chst" > "$W/i.json"
  python3.14 -I tools/acceptance/inspect_check.py "$W/i.json" "$d/container.chst"
done
```
`inspect_check.py` MUST check four things:
- every field's `offset + length` lies within the file;
- fields don't overlap;
- the fields together cover every byte of the file;
- each integer or hex `value` equals the bytes at its offset, decoded little-endian.

#### AC-POS-4 — Extract reproduces the tree, including empty directories
Core · OS all · fast · Traces: #3, #17, D10, EXT-10
```sh
for d in $FX/core/valid/*/; do
  rm -rf "$W/t" "$W/x"
  $GEN materialize "$d/tree.json" "$W/t"
  expect_exit 0 $CHST extract "$d/container.chst" -C "$W/x"
  python3.14 -I tools/acceptance/tree_eq.py "$W/t" "$W/x"
done
```
`tree_eq.py` walks both trees one directory handle at a time (never by full path string,
so paths beyond PATH_MAX work). It compares the set of paths, entry types and file bytes,
and prints the
differences.

The valid fixture set MUST include at least the following:

| Fixture | Contents |
|---|---|
| `worked-example` | The §18 example |
| `empty` | Zero entries |
| `empty-file` | One empty file |
| `dirs-only` | Nested empty directories |
| `dedup` | 100 identical files plus 3 empty files |
| `unicode` | NFC names: `é`, `日本語`, emoji |
| `deep` | Depth 256 |
| `long-names` | A 255-byte segment and a 4096-byte path |
| `sort-edge` | `a`, `a-b`, `a/b`, `a.b`, which exercises bytewise order |
| `nonprinting` | A name containing U+200B, which is allowed but doesn't print (AC-CLI-3) |

### 3.4 Negative conformance (V3, G7)

#### AC-NEG-1 — Every reader rule has at least one negative fixture
Core · OS all · fast · Traces: G7, D12, all reader rules in FORMAT_SPEC Appendix A
```sh
for r in $(grep -oE '^\| \*\*(HDR|TRL|SEC|BLB|ENT|PATH|CAN|LIM)-[0-9]+\*\*' FORMAT_SPEC.md | tr -d '|* ' | sort -u); do
  [ "$r" = LIM-6 ] && continue                                  # Extended-only (encoded blobs)
  compgen -G "$FX/core/invalid/$r.*" > /dev/null || compgen -G "$FX/core/invalid/$r-*.chst" > /dev/null \
    || { echo "missing $r"; exit 1; }
done
for n in TRL-2-low TRL-2-overflow SEC-1-straddle SEC-3-repeat SEC-5-entry BLB-4-zero-blobs BLB-4-short-last \
         ENT-1-type0 PATH-2-unicode16 PATH-3-empty PATH-3-2 PATH-6-c1 PATH-6-bidi PATH-6-isolate PATH-9-2 PATH-9-3 \
         PATH-9-com0 PATH-9-com1sup PATH-9-com2sup PATH-9-com3sup PATH-9-lpt1sup PATH-9-lpt2sup PATH-9-lpt3sup ENT-6-2 \
         PATH-6-rlm PATH-6-alm; do
  test -f "$FX/core/invalid/$n.expect.json" || { echo "missing sub-condition fixture $n"; exit 1; }
done
```
- For each configurable-limit rule (LIM-3 to LIM-5), the fixture's `expect.json` carries
  the CLI limit flag that triggers it, in an `args` field.
- Rules that can only be broken in a file using Extended features are covered by
  AC-X-NEG-1:
  - FLG-1: Core knows no flags, so it has nothing to check;
  - LIM-6: the ratio limit applies only to encoded blobs;
  - the ZST, ATT and KV rules.
- LIM-1 is retired (FORMAT_SPEC §10.1), so it's no longer in Appendix A. LIM-2 is a sparse
  recipe, `core/invalid/LIM-2.recipe.json`.
- **Sub-conditions (F35).** A rule with several independent conditions needs one fixture
  per condition. The required Core names are listed in the second loop above; AC-X-NEG-1
  lists the Extended ones.
- **A condition no fixture can reach:** FLG-1 for an `encoding` 1 blob without the `ZSTD`
  flag, because BLB-2 always fires first in §13's order. (FLG-1 for `ENTRY_ATTRS` is now
  one direction only and is reachable: `FLG-1-attrs-short`, N9.)

#### AC-NEG-2 — Each negative fixture gives exactly the expected category, detail and exit code
Core · OS all · fast · Traces: D12, #25, #26
```sh
for e in $FX/core/invalid/*.expect.json; do
  f=$(fixture_file $e); args=$(jq -r '.args // [] | join(" ")' $e)
  set +e; $CHST verify --json $args "$f" > "$W/r.json" 2> "$W/err"; rc=$?; set -e
  test $rc = "$(jq .exit $e)"
  test "$(jq -r .error.category "$W/r.json")" = "$(jq -r .category $e)"
  test "$(jq -r .error.detail "$W/r.json")" = "$(jq -r .detail $e)"
  test "$(jq -c 'keys' "$W/r.json")" = '["command","error","ok","schema","warnings"]'
  head -1 "$W/err" | grep -qF "chst: error[$(jq -r .category $e)/$(jq -r .detail $e)]: "
done
```
Readers report the first violation in FORMAT_SPEC §13's total order (F2), so every fixture
has exactly one expected `detail`. Where a fixture also breaks later rules,
`also_violates` records them for information only.

#### AC-NEG-3 — `list` and `inspect` also reject structurally invalid files
Core · OS all · fast · Traces: #2, #5, D12
```sh
for e in $FX/core/invalid/*.expect.json; do
  case "$(jq -r .rule $e)" in BLB-6|LIM-5) continue;; esac   # step 11 / verify+extract only
  f=$(fixture_file $e); args=$(jq -r '.args // [] | join(" ")' $e)
  for c in list inspect; do expect_exit "$(jq .exit $e)" $CHST $c --json $args "$f" >/dev/null; done
done
# F34: list and inspect MUST NOT perform step 11, so a blob-hash error is invisible to them
for c in list inspect; do expect_exit 0 $CHST $c --json $FX/core/invalid/BLB-6.chst > /dev/null; done
```

#### AC-NEG-4 — Negative fixtures are documented single mutations
Core · OS all · fast · Traces: G7, D12
```sh
for e in $FX/core/invalid/*.expect.json $FX/extended/invalid/*.expect.json; do
  jq -e '(.base|length>0) and (.mutation|length>0) and (.rule|test("^[A-Z]+-[0-9]+$"))' $e >/dev/null
done
```
Each fixture names its valid base fixture and the one mutation applied. Unless the rule
being tested is TRL-3, the generator recomputes the structure hash after mutating.

### 3.5 Determinism and dedup (V4)

#### AC-DET-1 — Output doesn't depend on creation order, mtimes, modes or umask
Core · OS all · fast · Traces: #19, D9
```sh
for d in $FX/core/valid/*/; do
  rm -rf "$W/t" "$W/o.chst"
  $GEN materialize --reverse "$d/tree.json" "$W/t"
  (umask 077; $CHST pack "$W/t" -o "$W/o.chst")
  cmp "$W/o.chst" "$d/container.chst"
done
```

#### AC-DET-2 — Identical content is stored once
Core · OS all · fast · Traces: #21, D2
```sh
$CHST verify --json $FX/core/valid/dedup/container.chst | jq -e '.summary.blobs == 2 and .summary.files == 103'
```
Pass: exit 0. That's one blob for the 100 identical files and one shared empty blob.

#### AC-DET-3 — Random trees round-trip
Core · OS all · fast · Traces: #1, #3, #21, D9, D10
```sh
CHST_PROP_CASES=256 cargo_test_nonempty --release -p chst-fs --test roundtrip_prop
```
The property test uses a seeded generator in test code (no `proptest`; see D15) and prints the seed on failure. It generates random portable trees (empty directories, duplicate contents,
Unicode names) and checks three things: pack then extract gives an identical tree, packing
twice gives identical bytes, and verify exits 0.

### 3.6 Integrity and robustness (V5, V6)

#### AC-ROB-1 — Flipping any single byte is always detected (CLI, exhaustive)
Core · OS all · fast · Traces: #4, #13, D1, D6, #26
```sh
python3.14 -I tools/acceptance/flip_sweep.py "$CHST" $FX/core/valid/worked-example/container.chst \
  $FX/core/valid/empty/container.chst $FX/core/valid/dedup/container.chst
```
```sh
python3.14 -I tools/acceptance/flip_sweep.py --rehash --min-distinct 15 "$CHST" \
  $FX/core/valid/worked-example/container.chst
```
For every byte offset, and for each of XOR `0x01` and XOR `0xFF`, `flip_sweep.py` runs
`verify` on the mutated file.

**Plain mode** (first command). It asserts four things:
- the exit code is one of 4, 5, 6 or 7, never 0, 70 or 101;
- stderr has no `panicked`;
- each run takes under 5 seconds;
- it prints a histogram of detail codes.

**`--rehash` mode** (second command, F13). After each flip it recomputes the structure
hash, so the damage reaches the section, entry, path and canonical rules instead of
stopping at TRL-3. It asserts:
- no exit 70 or 101, and no panic;
- at least 15 distinct detail codes occur (the generator's checker finds 26);
- exit 0 occurs only for flips that create a different **valid** container. That means
  only flips in `minor_version`, in unknown optional-flag bits, or in path-pool bytes that
  turn one valid name into another. Any other accepted flip fails the check.
- `--rehash` skips trailer bytes 16–47, the structure hash itself: rehashing a flip there
  just restores the original file (N14).

Pass: exit 0 for both.

#### AC-ROB-2 — Truncation and extension are always detected
Core · OS all · fast · Traces: #4, D1, #26
```sh
python3.14 -I tools/acceptance/truncate_sweep.py "$CHST" $FX/core/valid/worked-example/container.chst
```
- Every prefix length from 0 to N−1 must exit with 4 when the length is below 88, and with 6
  (`trl.magic`) otherwise.
- Appending 1 byte, or 4096 bytes, must exit non-zero.
- Never 0, 70 or 101.

#### AC-ROB-3 — Library damage sweep across every valid fixture
Core · OS all · fast · Traces: #26, V5
```sh
cargo_test_nonempty --release -p chst-format --test damage_sweep
```
For every valid fixture up to 64 KiB, at every offset, the test applies single-bit and
single-byte flips plus all truncations. Each must return an error, never success, with no
panic. It then repeats the flips **with the structure hash recomputed** (F13), so the
structural parser is exercised. Those runs must never panic, and any success must be a
fully valid container.

#### AC-ROB-4 — Fuzzing: 10 crash-free minutes per target
Core · OS linux, macos · **full-only** · Traces: #26, G8, V6, D16
```sh
tc=$(sed -n 's/^channel = "\(.*\)"$/\1/p' fuzz/rust-toolchain.toml)
for t in open_verify open_verify_rehash list inspect; do
  cargo +"$tc" fuzz run $t -- -max_total_time=600 -rss_limit_mb=512 -timeout=10 \
    fuzz/corpus/$t $FX/core/valid $FX/core/invalid
  test -z "$(ls -A fuzz/artifacts/$t 2>/dev/null)"
done
```
Pass: exit 0 and no artifacts. In a fast run this criterion is NOT RUN. Windows runs
AC-ROB-4W instead (§1.3).

`open_verify_rehash` (F13) treats its input as an index body. It builds the header, the
trailer and the correct structure hash around that body, then calls the reader, so
coverage-guided fuzzing reaches the section, record, path and canonical rules, which
libFuzzer can't reach through SHA-256. The other targets take raw files.

#### AC-ROB-4W — Windows fuzzing fallback: 10 minutes of randomised damage sweeps
Core · OS windows · **full-only** · *provisional until the first full CI run* · Traces: #26, G8, V6
```sh
CHST_SWEEP_SECONDS=600 cargo_test_nonempty --release -p chst-format --test random_sweep -- --include-ignored
```
For 600 seconds, a seeded generator in the test mutates the valid, invalid and regression
fixtures:
- byte flips, insertions, deletions and truncations;
- splices between fixtures;
- field-aware edits that recompute the structure hash, so the mutations reach past TRL-3.

Every input must produce an error or a valid report, with no panic, within 10 seconds per
input. Any failing input is saved to `fixtures/fuzz-regressions/random_sweep/` (owner
approval, per `CLAUDE.md`). Each run's seed is logged.

`chst-format` has no OS-specific code (AC-ENG-2), so AC-ROB-4 on Linux and macOS covers
its logic with coverage-guided fuzzing. This criterion checks the Windows build.

#### AC-ROB-5 — Fuzz regressions stay fixed
Core · OS all · fast · Traces: #26, V6
```sh
cargo_test_nonempty --release -p chst-format --test fuzz_regressions
```
The test replays every file under `fixtures/fuzz-regressions/`. Each must return an error
or a valid report, with no panic, and within the target's time and memory limits.

#### AC-ROB-6 — Memory stays bounded on large data
Core · OS linux · fast · Traces: G6, #15
```sh
mkdir -p "$W/t" && truncate -s 1G "$W/t/big.bin"
for cmd in "pack $W/t -o $W/o.chst" "verify $W/o.chst" "extract $W/o.chst -C $W/x"; do
  /usr/bin/time -f '%M' -o "$W/rss" $CHST $cmd
  test "$(cat "$W/rss")" -lt 65536      # peak RSS < 64 MiB (KiB units)
done
```

#### AC-ROB-7 — Large files over 4 GiB round-trip (64-bit sizes)
Core · OS all · **full-only** · Traces: #15, D3
```sh
case "$CHST_OS" in
  macos)   size=4296015872 ;;                                   # 4 GiB + 1 MiB
  windows) size=5368709120                                       # 5 GiB …
           [ "$(free_bytes "$CHST_BIG_ROOT")" -ge 12884901888 ] || size=4296015872 ;;  # … unless < 12 GiB free
  *)       size=5368709120 ;;
esac
echo "AC-ROB-7 size: $size"; df -h "$CHST_BIG_ROOT"
B=$(mktemp -d "$CHST_BIG_ROOT/chst-rob7.XXXXXX"); trap 'rm -rf "$B"' EXIT
mkdir "$B/t"; mk_sparse "$B/t/huge.bin" $size
$CHST pack "$B/t" -o "$B/o.chst"
$CHST list --json "$B/o.chst" | jq -e --argjson s $size '.entries[0].size == $s'
$CHST verify "$B/o.chst"
$CHST extract "$B/o.chst" -C "$B/x"
test "$(sha256 "$B/x/huge.bin")" = "$(sha256 "$B/t/huge.bin")"
```
- The source file is sparse. Peak disk is about 10 GiB for 5 GiB, or about 8 GiB for
  4 GiB + 1 MiB.
- The variant for each OS is fixed in §1.3. No paid runners.
- `$B` is a fresh temporary directory, always removed afterwards.

#### AC-ROB-8 — Fast 64-bit check: small fixtures that declare sizes over 4 GiB
Core · OS all · fast · Traces: #15, D3, D11
```sh
for e in $FX/core/hostile64/*.expect.json; do
  set +e; $CHST verify --json "${e%.expect.json}.chst" > "$W/r.json"; rc=$?; set -e
  test $rc = 6
  jq -e --slurpfile x $e '.error.detail as $d | $x[0].details | index($d) != null' "$W/r.json"
done
```
Each fixture is a copy of `worked-example`, under 1 KiB, with 2³² added to the u64
value(s) in one row of the table below. The structure hash is recomputed, so only that
change is wrong. A reader that truncated sizes to 32 bits would see the original, valid
values and wrongly accept the file. Each `expect.json` gives the one expected detail (§13's
order) in `details`. The set MUST cover:

| Value(s) + 2³² | Expected detail |
|---|---|
| `blob[0].offset` | `blob.layout` |
| `blob[0].stored_length` and `blob[0].raw_length` together (keeps BLB-3 true) | `blob.layout` |
| `blob[0].raw_length` | `blob.raw-length` |
| `entry[1].path_offset` | `entry.path-range` |
| BLOB_TABLE `record_count` | `sec.bounds` |
| `trailer.index_offset` | `trl.index-range` |

#### AC-ROB-9 — Fast 64-bit check: a valid sparse 5 GiB container
Core · OS all · fast · Traces: #15, D3
```sh
d=$FX/core/sparse/huge-5g
mk_sparse "$W/h.chst" "$(jq .file_length $d/recipe.json)"
$GEN materialize-sparse $d/recipe.json "$W/h.chst"
for c in list inspect verify; do
  expect_exit 0 $CHST $c --json "$W/h.chst" > "$W/r.json"; diff <(jqn "$W/r.json") <(jqn $d/$c.json)
done
```
The committed recipe is under 2 KiB: the header plus the index and trailer bytes, and the
total length.
- The container holds one 5 GiB all-zero file, so `index_offset`, `stored_length` and
  `raw_length` all exceed 2³².
- `verify` hashes 5 GiB of holes, which uses almost no disk and takes seconds.
- The expected `inspect.json` shows the exact high-bit values.

### 3.7 Safe extraction (V7)

#### AC-SAFE-1 — Attack fixtures write nothing anywhere
Core · OS all · fast · Traces: #23, G3, D8, D10, EXT-3, EXT-4, EXT-6
```sh
for e in $FX/core/attacks/*.expect.json; do
  f=${e%.expect.json}.chst; rm -rf "$W/p"; mkdir -p "$W/p/sentinel"
  expect_exit "$(jq .exit $e)" $CHST extract "$f" -C "$W/p/out"
  test "$(ls -A "$W/p")" = sentinel && test -z "$(ls -A "$W/p/sentinel")"
done
```
The attack set MUST include at least these paths:

| Attack | Path |
|---|---|
| Parent escape | `../x`, `a/../../x` |
| Absolute paths | `/etc/x`, `C:/x`, `\\server\x` |
| Backslash | `a\..\x` |
| Device name | `CON`, `aux.txt`, `CON .txt`, `CONIN$`, `lpt¹` |
| Alternate data stream | `f.txt:evil`, `f.txt::$DATA` |
| Trailing dot or space | `x.`, `x ` |
| NUL and control characters | |
| ASCII case collision | `A` and `a` |
| File used as a parent | `f` is a file, and `f/g` exists |
| Missing parent | |
| Non-NFC name | |

#### AC-SAFE-2 — An existing destination is refused and left untouched
Core · OS all · fast · Traces: G4, EXT-1, D10
```sh
mkdir -p "$W/out" && echo keep > "$W/out/k"
expect_exit 9 $CHST extract $FX/core/valid/worked-example/container.chst -C "$W/out" 2> "$W/err"
grep -q 'error\[refused/extract.dest-exists\]' "$W/err"
test "$(ls -A "$W/out")" = k && test "$(cat "$W/out/k")" = keep
if [ "$CHST_OS" != windows ]; then                       # F16: a dangling symlink also "exists"
  ln -s "$W/nowhere" "$W/link"
  expect_exit 9 $CHST extract $FX/core/valid/worked-example/container.chst -C "$W/link"
  test -L "$W/link" && test ! -e "$W/nowhere"
fi
```

#### AC-SAFE-3 — A hash failure mid-extract leaves no destination and no staging directory
Core · OS all · fast · Traces: EXT-4, EXT-7, D10
```sh
mkdir -p "$W/p"
expect_exit 7 $CHST extract $FX/core/extract-cases/late-blob-hash.chst -C "$W/p/out" 2> "$W/err"
grep -q 'error\[integrity/blob.hash\]' "$W/err"
test -z "$(ls -A "$W/p")"
cargo_test_nonempty --release -p chst-fs --features test-hooks --test late_failure
```
The `late_failure` test (F14) uses the `test-hooks` hook to observe the staging directory
when the BLB-6 error is raised. It asserts that at least one file was already in staging,
which proves verification happens while writing (EXT-7) and not in a pre-pass, and that
staging is gone afterwards.
`late-blob-hash.chst` has a valid structure, but its *last* blob's bytes are corrupted, so
earlier files are already written into staging when the failure happens. Fixtures whose
outcome depends on the OS, or that need a specific failure point, live in
`fixtures/core/extract-cases/`, not in `attacks/`.

#### AC-SAFE-4 — Permissions are safe defaults
Core · OS linux, macos · fast · Traces: EXT-5, D10
```sh
(umask 022; $CHST extract $FX/core/valid/worked-example/container.chst -C "$W/x")
test -z "$(find "$W/x" -perm -4000 -o -perm -2000 -o -perm -1000)"
test "$(find "$W/x" -type f ! -perm 644 | wc -l)" -eq 0
test "$(find "$W/x" -type d ! -perm 755 | wc -l)" -eq 0
```

#### AC-SAFE-5 — Non-ASCII case collisions are caught by the filesystem
Core · OS macos, windows · fast · Traces: EXT-2, D8
```sh
mkdir -p "$W/p"
expect_exit 9 $CHST extract $FX/core/extract-cases/unicode-case.chst -C "$W/p/out" 2> "$W/err"
grep -q 'error\[refused/extract.collision\]' "$W/err" && test -z "$(ls -A "$W/p")"
```
`unicode-case.chst` holds `é` and `É`, both NFC. It is valid per PATH-11. On Linux it
extracts successfully, which AC-SAFE-6 checks.

#### AC-SAFE-6 — Non-ASCII case-distinct names coexist on case-sensitive filesystems
Core · OS linux · fast · Traces: EXT-2, D8
```sh
expect_exit 0 $CHST extract $FX/core/extract-cases/unicode-case.chst -C "$W/x"
test -f "$W/x/é" && test -f "$W/x/É"
```

#### AC-SAFE-7 — Long paths extract on every OS
Core · OS all · fast · Traces: D8, FORMAT_SPEC §15 (Windows long paths)
```sh
expect_exit 0 $CHST extract $FX/core/valid/long-names/container.chst -C "$W/x"
$GEN materialize $FX/core/valid/long-names/tree.json "$W/t"
python3.14 -I tools/acceptance/tree_eq.py "$W/t" "$W/x"
```
The fixture's 4096-byte path, plus the temporary-directory prefix, exceeds PATH_MAX on
Linux (4096) and macOS (1024). So neither this check nor the tools it calls may resolve
full path strings:
- `$GEN materialize` and `tree_eq.py` walk one directory handle at a time (`dir_fd`);
- on Windows they use extended-length paths.

#### AC-SAFE-8 — Links and reparse points swapped in during extraction are never followed
Core · OS all · fast · Traces: EXT-8, EXT-6, D10
```sh
cargo_test_nonempty --release -p chst-fs --features test-hooks --test swap_race
```
The hook is compiled only with the non-default `test-hooks` Cargo feature (DESIGN D13), so
release builds never contain it. The hook points (F19):

- **Unix:** between `mkdirat` and the `openat(O_NOFOLLOW | O_DIRECTORY)` that obtains the
  new directory's handle. The hook replaces the directory with a symlink pointing outside.
  That `openat` must then fail (ELOOP or ENOTDIR), and the result must be
  `refused/extract.unsafe-object`.
- **Windows:** between creating a directory and any later reopening of it by name, if the
  implementation ever reopens. The hook replaces it with a junction. If the implementation
  never reopens by name, there's no window, and the test asserts success instead.

In every case the test asserts that nothing outside staging was created or modified. On
failure it also asserts that staging and the destination are both gone; on success, that
every file is inside the destination.

#### AC-SAFE-9 — Extraction never creates alternate data streams
Core · OS windows · fast · Traces: EXT-9, PATH-7
```sh
$CHST extract $FX/core/valid/worked-example/container.chst -C "$W/x"
n=$(powershell -NoProfile -Command "(Get-ChildItem -Recurse -File -LiteralPath '$(cygpath -w "$W/x")' | ForEach-Object { Get-Item -LiteralPath \$_.FullName -Stream * } | Where-Object Stream -ne ':\$DATA' | Measure-Object).Count")
test "$(echo $n | tr -d '\r')" = 0
```
Archive paths that try to name a stream (`f.txt:evil`) are covered by AC-SAFE-1, where
they must be `malformed`.

#### AC-SAFE-10 — Windows 8.3 short names never alias two entries
Core · OS windows · fast · Traces: EXT-2, D8
```sh
f=$FX/core/extract-cases/short-name.chst; mkdir -p "$W/p"
vol=$(cygpath -w "$W" | cut -c1-2)
fsutil 8dot3name set "$vol" 0                                # enable 8.3 names on this volume (runner is admin)
fsutil 8dot3name query "$vol"                                # logged
expect_exit 9 $CHST extract "$f" -C "$W/p/out" 2> "$W/err"
grep -q 'error\[refused/extract.collision\]' "$W/err" && test -z "$(ls -A "$W/p")"
```
`short-name.chst` holds `ABCDEFGHIJ/a` and then `ABCDEF~1/b`, in canonical order. With 8.3
names enabled (F38), creating `ABCDEFGHIJ` also creates the short name `ABCDEF~1`. So
creating the second directory must fail, with create-new semantics (EXT-2), and the
extraction must be refused with nothing left behind. If 8.3 names can't be enabled on the
runner, `fsutil` fails, and so does this check: it never silently runs only the trivial
branch.

#### AC-SAFE-11 — macOS: decomposed source names round-trip as NFC
Core · OS macos · fast · Traces: W-9, PATH-2, D8
```sh
mkdir -p "$W/t" && echo x > "$W/t/$(printf 'e\xcc\x81')"          # NFD é
$CHST pack "$W/t" -o "$W/c.chst"
$CHST list --json "$W/c.chst" | jq -e '[.entries[].path] == ["\u00e9"]'
$CHST extract "$W/c.chst" -C "$W/x"
python3.14 -I tools/acceptance/tree_eq.py --nfc "$W/t" "$W/x"
```

#### AC-SAFE-12 — The create-entry layer refuses hostile names on its own
Core · OS all · fast · Traces: EXT-6, EXT-8, D10
```sh
cargo_test_nonempty --release -p chst-fs --test create_layer
```
The test calls `chst-fs`'s create-entry layer directly, bypassing format validation (F15),
with the names `..`, `.`, `/x`, `a/../..`, `C:`, `a\b` and a name containing NUL. Each must
be refused, with nothing created outside the test's staging directory.

#### AC-SAFE-13 — The final rename never replaces a destination created mid-extract
Core · OS all · fast · Traces: EXT-1, EXT-4, D10
```sh
cargo_test_nonempty --release -p chst-fs --features test-hooks --test dest_race
```
Just before the final rename, a hook creates something at the destination (F16). The test
runs three cases: an empty directory, a symlink on Unix (a junction on Windows), and a
regular file. In each, the result must be `refused/extract.dest-exists`, the planted object
must be unchanged, and staging must be gone.

#### AC-SAFE-14 — The staging directory is private, unpredictable, and never handled by name
Core · OS all · fast · Traces: EXT-4, D10
```sh
cargo_test_nonempty --release -p chst-fs --features test-hooks --test staging_props
cargo_test_nonempty --release -p chst-fs --features test-hooks --test staging_swap
```
`staging_props`: a hook pauses extraction right after the staging directory is created
(F17). The test asserts:
- its name matches `^\.<dest>\.chst-[0-9a-f]{32}$`;
- with a 250-byte destination name, the staging name is at most 255 bytes, and its prefix
  is truncated at a character boundary (N4);
- two extractions use different names;
- its mode is 0700 on Unix, or its DACL grants only the current user on Windows;
- if the test pre-creates a directory with the exact name the next staging directory will
  use (forced through the hook's random source), the result is
  `refused/extract.collision`, and nothing is written into the pre-created directory (N5);
- after a successful extraction, the destination root has mode `0755 & ~umask` on Unix.
  On Windows, the destination and every extracted file carry exactly the inheritable ACEs
  of the destination's parent and not the private staging ACE (N6).

`staging_swap` (N2): just before the staging directory's final permissions are set, a hook
renames the staging directory away and puts a symlink (a junction on Windows) to an
outside directory under its name. The test asserts that the result is
`refused/extract.unsafe-object`, the outside directory's permissions and contents are
unchanged, nothing was moved to the destination, and the moved-away staging directory was
emptied through its handle.

#### AC-SAFE-15 — Cleanup never follows a link
Core · OS all · fast · Traces: EXT-4, EXT-6, D10
```sh
cargo_test_nonempty --release -p chst-fs --features test-hooks --test cleanup_race
```
Extraction is made to fail late (the BLB-6 fixture `late-blob-hash`) (F18). Before cleanup
runs, a hook replaces a directory inside staging with a symlink (a junction on Windows) to
an outside directory full of sentinel files. After cleanup, every sentinel file must still
exist, and staging must be gone.

### 3.8 Pack behaviour

#### AC-PACK-1 — Unportable source names are refused with no output
Core · OS linux · fast · Traces: G1, G3, W-3, D8
```sh
for n in 'a:b' 'CON.txt' 'trail.' 'sp ' $'bad\xff' 'Aa' ; do
  rm -rf "$W/t" "$W/o"; mkdir -p "$W/t" "$W/o"; touch "$W/t/$n"
  [ "$n" = Aa ] && touch "$W/t/aa"
  expect_exit 9 $CHST pack "$W/t" -o "$W/o/c.chst" 2> "$W/err"
  grep -q 'error\[refused/pack.unportable-name\]' "$W/err" && test -z "$(ls -A "$W/o")"
done
```

#### AC-PACK-2 — Symlinks and special files are skipped with a warning, never followed
Core · OS linux, macos · fast · Traces: N2, W-5, #20
```sh
mkdir -p "$W/t" "$W/outside" && echo secret > "$W/outside/s" && echo ok > "$W/t/f"
ln -s "$W/outside" "$W/t/link" && mkfifo "$W/t/fifo"
expect_exit 0 $CHST pack "$W/t" -o "$W/c.chst" 2> "$W/err"
test "$(grep -c 'pack.skipped' "$W/err")" -eq 2
test "$($CHST list --json "$W/c.chst" | jq -c '[.entries[].path]')" = '["f"]'
```

#### AC-PACK-3 — A source changed between hash and copy is refused
Core · OS all · fast · Traces: D2, W-4
```sh
cargo_test_nonempty --release -p chst-fs --test source_changed
```
The test covers two cases, each asserting `refused/pack.source-changed` and that no output
file exists:
- a fault-injecting source that returns different bytes on its second read;
- a file replaced between pass 1 and pass 2 by a different file (a new inode or file ID)
  with identical bytes. This proves pass 2 checks the file's identity (W-5, F23).

#### AC-PACK-4 — Container writes are atomic, including under `--force`
Core · OS linux, macos · fast · Traces: G5, W-2, W-7
```sh
mkdir -p "$W/t" "$W/o" "$W/o2" && touch "$W/t/a:b"
echo original > "$W/o/c.chst"
expect_exit 9 $CHST pack --force "$W/t" -o "$W/o/c.chst"
test "$(ls -A "$W/o")" = c.chst && test "$(cat "$W/o/c.chst")" = original
expect_exit 9 $CHST pack "$W/t" -o "$W/o2/c.chst"
test -z "$(ls -A "$W/o2")"
```
A failed pack leaves the output path exactly as it was, and no temporary files remain.

#### AC-PACK-6 — An existing output is refused without `--force`, and replaced with it
Core · OS all · fast · Traces: W-7, D14
```sh
d=$FX/core/valid/worked-example
$GEN materialize $d/tree.json "$W/t" && echo original > "$W/c.chst" && mkdir "$W/dir.chst"
expect_exit 9 $CHST pack "$W/t" -o "$W/c.chst" 2> "$W/err"
grep -q 'error\[refused/pack.output-exists\]' "$W/err" && test "$(cat "$W/c.chst")" = original
expect_exit 0 $CHST pack --force "$W/t" -o "$W/c.chst" && cmp "$W/c.chst" $d/container.chst
expect_exit 9 $CHST pack --force "$W/t" -o "$W/dir.chst" && test -d "$W/dir.chst"
```

#### AC-PACK-7 — Windows junctions and reparse points are skipped, never followed
Core · OS windows · fast · Traces: W-8, N2
```sh
mkdir -p "$W/t" "$W/outside" && echo secret > "$W/outside/s" && echo ok > "$W/t/f"
MSYS_NO_PATHCONV=1 cmd /c mklink /J "$(cygpath -w "$W/t/j")" "$(cygpath -w "$W/outside")"
expect_exit 0 $CHST pack --json "$W/t" -o "$W/c.chst" > "$W/r.json"
jq -e '[.warnings[] | .detail] == ["pack.skipped"] and .warnings[0].path == "j"' "$W/r.json"
test "$($CHST list --json "$W/c.chst" | jq -c '[.entries[].path]')" = '["f"]'
```

#### AC-PACK-8 — Windows alternate data streams are not packed
Core · OS windows · fast · Traces: W-8
```sh
mkdir -p "$W/t" && printf 'ok\n' > "$W/t/f"
powershell -NoProfile -Command "Set-Content -LiteralPath '$(cygpath -w "$W/t/f")' -Stream s -Value hidden"
$CHST pack "$W/t" -o "$W/c.chst"
$CHST list --json "$W/c.chst" | jq -e '[.entries[] | {path, size}] == [{"path":"f","size":3}]'
```

#### AC-PACK-9 — Decomposed (NFD) source names are stored as NFC; NFC/NFD twins are refused
Core · OS linux · fast · Traces: W-3, W-9, D8
```sh
mkdir -p "$W/a" "$W/b"; touch "$W/a/$(printf 'e\xcc\x81')"
$CHST pack "$W/a" -o "$W/a.chst"
$CHST list --json "$W/a.chst" | jq -e '[.entries[].path] == ["\u00e9"]'
touch "$W/b/$(printf 'e\xcc\x81')" "$W/b/$(printf '\xc3\xa9')"
expect_exit 9 $CHST pack "$W/b" -o "$W/b.chst" 2> "$W/err" && grep -q pack.unportable-name "$W/err"
```

#### AC-PACK-5 — An output path inside the source tree is refused, however it's spelled
Core · OS all · fast · Traces: W-6
```sh
mkdir -p "$W/t/sub" && echo x > "$W/t/f"
expect_exit 9 $CHST pack "$W/t" -o "$W/t/self.chst" 2> "$W/err"
grep -q 'pack.output-in-source' "$W/err" && test ! -e "$W/t/self.chst"
expect_exit 9 $CHST pack "$W/t" -o "$W/t/sub/../sub/self.chst"           # .. route (F22)
if [ "$CHST_OS" != windows ]; then
  ln -s "$W/t/sub" "$W/alias"                                           # symlinked route
  expect_exit 9 $CHST pack "$W/t" -o "$W/alias/self.chst" && test ! -e "$W/t/sub/self.chst"
fi
```
"Inside" is decided by file identity (W-6). So routes through `..` or through a symlink to
a directory in the source tree are refused too.

#### AC-PACK-10 — A directory swapped for a link during the walk is never followed
Core · OS all · fast · Traces: W-5, W-8, D10
```sh
cargo_test_nonempty --release -p chst-fs --features test-hooks --test walk_race
```
A hook pauses the pack walk after a directory has been listed, and replaces it with a
symlink (a junction on Windows) to an outside directory (F23). No byte of the outside
directory may appear in the output. The pack either fails `refused/pack.source-changed`, or
completes without that directory's contents.

#### AC-PACK-11 — Pack refuses to write what its own verify would reject
Core · OS all · fast · Traces: W-10, D11
```sh
d=$FX/core/valid/worked-example; $GEN materialize $d/tree.json "$W/t"
expect_exit 8 $CHST pack --max-entries 4 "$W/t" -o "$W/a.chst" 2> "$W/err"
grep -q 'error\[limit-exceeded/limit.entries\]' "$W/err" && test ! -e "$W/a.chst"
expect_exit 8 $CHST pack --max-total-bytes 14 "$W/t" -o "$W/b.chst" && test ! -e "$W/b.chst"
expect_exit 0 $CHST pack --max-entries 5 --max-total-bytes 15 "$W/t" -o "$W/c.chst"
```
F24.

#### AC-PACK-12 — Skipped cloud placeholders get their own warning
Core · OS all · fast · Traces: W-8
```sh
cargo_test_nonempty --release -p chst-fs --test skip_classification
```
Real cloud-file placeholders can't be created on CI runners. So the test feeds the walk's
classification function synthetic Windows reparse tags (F46):
- every `IO_REPARSE_TAG_CLOUD*` tag must give `pack.skipped-placeholder`;
- symlink, mount-point and other tags give `pack.skipped`.

AC-CLI-2 checks the `summary.skipped` count end to end.

### 3.9 Limits (V8)

#### AC-LIM-1 — Hostile declared sizes fail fast with bounded memory
Core · OS all · fast · Traces: #24, D11, #26
```sh
cargo_test_nonempty --release -p chst-format --test hostile_sizes
for e in $FX/core/hostile/*.expect.json; do
  expect_exit "$(jq .exit $e)" timeout 2 $CHST verify "${e%.expect.json}.chst"
done
```
The hostile fixtures declare an `index_length` near 2⁶⁴, a `record_count` of 2⁶⁰, 2³²
entries, and a path length of 2³²−1, all inside files under 1 KiB. `hostile_sizes` uses a
counting allocator (`crates/chst-format/tests/support/counting_alloc.rs`, the only test-only
`unsafe` exception in D18) and asserts peak heap under 1 MiB per fixture.

#### AC-LIM-2 — Configured limits trigger at exact boundaries
Core · OS all · fast · Traces: #24, D11, LIM-3…LIM-5
```sh
f=$FX/core/valid/worked-example/container.chst
expect_exit 8 $CHST verify --max-entries 4 $f;        expect_exit 0 $CHST verify --max-entries 5 $f
expect_exit 8 $CHST verify --max-index-bytes 458 $f;  expect_exit 0 $CHST verify --max-index-bytes 459 $f
expect_exit 8 $CHST verify --max-total-bytes 14 $f;   expect_exit 0 $CHST verify --max-total-bytes 15 $f
expect_exit 8 $CHST extract --max-total-bytes 14 $f -C "$W/a"; test ! -e "$W/a"
expect_exit 0 $CHST extract --max-total-bytes 15 $f -C "$W/b"
```
The worked example stores 9 blob bytes, but its logical size is 15 (6 + 6 + 3), because
`docs/a.txt` and `docs/b.txt` share a blob. A limit of 14 must fail, which shows each
reference is counted.

#### AC-LIM-4 — The total-size limit counts every reference to a shared blob
Core · OS all · fast · Traces: LIM-5, D2, D11
```sh
$GEN synth-amplify 1000 65536 "$W/amp.chst"      # 1000 files sharing one 64 KiB blob
test "$(wc -c < "$W/amp.chst" | tr -d ' ')" -lt 200000
$CHST verify --json "$W/amp.chst" | jq -e '.summary.blobs == 1 and .summary.raw_bytes == 65536 and .summary.extracted_bytes == 65536000'
mkdir -p "$W/p"
expect_exit 8 $CHST extract --max-total-bytes 65535999 "$W/amp.chst" -C "$W/p/out" 2> "$W/err"
grep -q 'error\[limit-exceeded/limit.total-size\]' "$W/err" && test -z "$(ls -A "$W/p")"
expect_exit 0 $CHST extract --max-total-bytes 65536000 "$W/amp.chst" -C "$W/p/out"
```
A container under 200 KB that expands to 62.5 MiB is checked against its full logical
size before anything is written. There is no per-blob reference limit (FORMAT_SPEC §10.2).

#### AC-LIM-3 — Defaults accept the must-support minimum and reject one over
Core · OS linux · fast · Traces: D11, LIM-3
```sh
$GEN synth-entries 1048576 "$W/ok.chst" && expect_exit 0 $CHST verify "$W/ok.chst"
$GEN synth-entries 1048577 "$W/over.chst" && expect_exit 8 $CHST verify "$W/over.chst"
```

### 3.10 CLI and errors

#### AC-CLI-1 — Exit codes for usage, I/O and not-a-container
Core · OS all · fast · Traces: #25, D12
```sh
expect_exit 2 $CHST frobnicate
expect_exit 2 $CHST verify
expect_exit 3 $CHST verify "$W/does-not-exist.chst"
head -c 100 /dev/urandom > "$W/r" && expect_exit 4 $CHST verify "$W/r"
: > "$W/e" && expect_exit 4 $CHST verify "$W/e"
f=$FX/core/valid/worked-example/container.chst                         # N23: limit values
expect_exit 2 $CHST verify --max-entries -1 $f
expect_exit 2 $CHST verify --max-entries 18446744073709551616 $f
expect_exit 0 $CHST verify --max-entries 18446744073709551615 $f
expect_exit 0 $CHST verify --max-entries 0 $FX/core/valid/empty/container.chst
```

#### AC-CLI-2 — Warnings never change the exit code and appear in the JSON
Core · OS linux, macos · fast · Traces: D12, W-5
```sh
mkdir -p "$W/t" && mkfifo "$W/t/p" && echo x > "$W/t/f"
expect_exit 0 $CHST pack --json "$W/t" -o "$W/c.chst" > "$W/r.json"
jq -e '.warnings[0].detail == "pack.skipped" and .summary.skipped == 1' "$W/r.json"
```
`pack --json` emits a `chst-report/1` object with `command: "pack"` (FORMAT_SPEC
Appendix B).

#### AC-CLI-3 — list's text output escapes non-printing characters
Core · OS all · fast · Traces: PATH-6, D8
```sh
$CHST list $FX/core/valid/nonprinting/container.chst > "$W/out.txt"
grep -qF 'zero\u{200b}width.txt' "$W/out.txt"
if LC_ALL=C grep -q $'\xe2\x80\x8b' "$W/out.txt"; then exit 1; fi    # the raw U+200B must not appear
```
Code points that PATH-6 allows but that don't print are escaped as `\u{X}` (FORMAT_SPEC
Appendix C, F42).

### 3.11 Compatibility (V9)

#### AC-COMPAT-1 — A Core build handles Extended and future files as the spec requires
Core · OS all · fast · Traces: #18a, G2, D5, SEC-2, SEC-5, HDR-6
```sh
for e in $FX/compat/*.expect.json; do
  f=${e%.expect.json}.chst
  set +e; $CHST_CORE verify --json "$f" > "$W/r.json"; rc=$?; set -e
  test $rc = "$(jq .exit $e)"
  jq -e --slurpfile x $e '($x[0].detail == null) or (.error.detail == $x[0].detail)' "$W/r.json"
  if [ "$rc" = 0 ]; then for c in list verify inspect; do
    $CHST_CORE $c --json "$f" > "$W/c.json"; diff <(jqn "$W/c.json") <(jqn ${e%.expect.json}.$c.json)
  done; fi
done
```
For every exit-0 fixture, the Core-only reader's list, verify and inspect reports must
match the expected Core view (F33). That view names KV_METADATA `unknown`, names
`ENTRY_ATTRS` `bit0`, and shows attribute bytes as `extra`.

The compat set MUST include:

| Fixture | Expected result |
|---|---|
| `ZSTD` required flag | 5 / `hdr.required-flag` |
| Unknown required bit 63 | 5 |
| `ENTRY_ATTRS` (64-byte entry records) | 0, listed without attributes |
| `KV_METADATA` section | 0 |
| Unknown optional bit 63 | 0 |
| Unknown optional bit 63 with 64-byte entry records and no `ENTRY_ATTRS` (a future flag widening records, N9) | 0 |
| Unknown non-critical section `0x7FFFFFF0` | 0 |
| Unknown critical section `0xFFFFFFF0` | 5 / `sec.unknown-critical` |
| `minor_version` 65535 | 0 |
| `major_version` 2 | 5 / `hdr.major-version` |
| `hash_alg` 2 | 5 / `hdr.hash-alg` |

### 3.12 Cross-platform (V10)

#### AC-XP-1 — The CI full run of one commit passes on all three OSes, and EVIDENCE.md matches it
Core · OS all · **done-only** (`./check.sh --done <ci-run-id>`) · Traces: V10, D17, Definition of Done
```sh
gh run download "$CI_RUN_ID" --pattern 'acceptance-report-*' --dir "$W/r"      # gh: read-only use
test "$(jq -r .os "$W"/r/*/report.json | sort -u | tr '\n' ' ')" = 'linux macos windows '
test "$(jq -r .commit "$W"/r/*/report.json | sort -u | wc -l | tr -d ' ')" = 1
sha=$(jq -r .commit "$W"/r/*/report.json | head -1)
test "$(gh run view "$CI_RUN_ID" --json headSha -q .headSha)" = "$sha"
for r in "$W"/r/*/report.json; do
  jq -e '.mode == "full" and .dirty == false and
         all(.results[]; if .id == "AC-XP-1" then .status == "NOT RUN" else (.status == "PASS" or .status == "N/A") end)' "$r"
  col=$(case "$(jq -r .os "$r")" in linux) echo 3;; macos) echo 4;; windows) echo 5;; esac)
  jq -r '.results[] | select(.id != "AC-XP-1") | "\(.id)\t\(.status)"' "$r" | while IFS=$'\t' read -r id st; do
    row=$(grep -E "^\| $id \|" EVIDENCE.md) || { echo "EVIDENCE.md: no row for $id"; exit 1; }
    test "$(awk -F'|' -v c=$col '{gsub(/^ +| +$/, "", $c); print $c}' <<< "$row")" = "$st"
    grep -qF "$sha" <<< "$row" && grep -qF "actions/runs/$CI_RUN_ID" <<< "$row"
  done
done
```
- The CI run must be a manually triggered full-mode run (D17) of one commit on
  `ubuntu-latest`, `macos-latest` and `windows-latest`.
- Each per-OS report is uploaded as `acceptance-report-<os>`.
- In done mode, `check.sh` imports each ID's statuses from those reports and runs this
  check. It then exits 0 only if this check passes (§2).

#### AC-XP-2 — The CI workflow has the agreed triggers, runners and modes
Core · OS all · fast · Traces: D17, V10
```sh
w=.github/workflows/check.yml
for k in 'push:' 'pull_request:' 'workflow_dispatch:' ubuntu-latest macos-latest windows-latest 'shell: bash' \
         './check.sh --full' 'acceptance-report-' 'CHST_BIG_ROOT'; do grep -qF -- "$k" $w; done
grep -qE '^\s+run: \./check\.sh\s*$' $w     # the fast-mode step
```
Pass: exit 0. Whether the workflow actually ran is checked by AC-XP-1, through `gh`.

### 3.13 Extended criteria

Every criterion in this section is **N/A while `CURRENT_CUT = Core`** (§2). Once the
owner changes the cut to Extended, every one of them applies, and a missing check is
FAIL.

#### AC-X-NEG-1 — Extended negative fixtures (ZST, ATT, KV, FLG-1, LIM-6)
Extended:all · OS all · fast · Traces: ZST-1…3, ATT-1, KV-1, FLG-1, LIM-6, D7
The same script as AC-NEG-1 and AC-NEG-2, over `$FX/extended/invalid`, for the rules
ZST-1…3, ATT-1, KV-1, FLG-1, LIM-6 and SEC-4 (KV_METADATA's record size).

The required sub-condition fixtures (F35) are:
- `FLG-1-kv-section-no-flag`, `FLG-1-zstd-unused`;
- `ATT-1-mode`, `ATT-1-reserved`;
- `KV-1-empty`, `KV-1-utf8`, `KV-1-keylen0`, `KV-1-keylen256`, `KV-1-value-too-long`,
  `KV-1-truncated`, `KV-1-duplicate`;
- `SEC-4-kv`;
- `ZST-2-window`, `ZST-2-dictid`, `ZST-2-short`, `ZST-2-checksum`, `ZST-2-no-fcs-overflow`,
  `ZST-2-bomb`, `ZST-2-reserved-fhd`, `ZST-2-block-type`, `ZST-2-block-size`,
  `ZST-2-truncated`, `ZST-2-skippable` (N10, N11);
- `FLG-1-attrs-short` (N9).

#### AC-X-ZSTD-1 — Compressed round-trip; compressed only when smaller
Extended:#12 · OS all · fast · Traces: #12, D7, ZST-3
```sh
for d in $FX/extended/valid/zstd-*/; do
  rm -rf "$W/t" "$W/x"; $GEN materialize "$d/tree.json" "$W/t"
  $CHST pack --compress zstd "$W/t" -o "$W/c.chst"
  diff <($CHST list --json "$W/c.chst" | jq -S '[.entries[] | {path,type,size,encoding}]') \
       <(jq -S '[.entries[] | {path,type,size,encoding}]' "$d/list.json")
  $CHST extract "$W/c.chst" -C "$W/x" && python3.14 -I tools/acceptance/tree_eq.py "$W/t" "$W/x"
done
mkdir -p "$W/big" && head -c 2097152 /dev/zero > "$W/big/zeros.bin"      # N8: over 1000:1 when compressed
$CHST pack --compress zstd "$W/big" -o "$W/big.chst"
$CHST list --json "$W/big.chst" | jq -e '.entries[0].encoding == "stored"'
$CHST verify "$W/big.chst"
```
The fixtures include incompressible random data, which must list as `encoding: "stored"`.
2 MiB of zeros would compress far beyond the 1000:1 ratio limit, so pack must store it
(W-10, N8), and the result must pass the default `verify`.
Comparison deliberately excludes compressed sizes and keys (D7).

#### AC-X-ZSTD-2 — Decompression bombs and huge windows are contained
Extended:#12 · OS linux · fast · Traces: ZST-1, ZST-2, LIM-6, D11
```sh
for t in ZST-2-window:6:zstd.frame ZST-2-dictid:6:zstd.frame ZST-1:7:zstd.raw-length LIM-6:8:limit.ratio \
         ZST-2-no-fcs-overflow:6:zstd.frame ZST-2-bomb:6:zstd.frame; do
  IFS=: read -r n code det <<< "$t"
  set +e; /usr/bin/time -f '%M' -o "$W/rss" timeout 10 $CHST verify --json $FX/extended/invalid/$n.chst > "$W/r.json"; rc=$?; set -e
  test $rc = $code && test "$(jq -r .error.detail "$W/r.json")" = "$det"
  test "$(cat "$W/rss")" -lt 65536                                      # peak RSS < 64 MiB, C allocations included
done
```
The memory limit is measured on the whole process's peak RSS (F10), so libzstd's C
allocations are included; a counting Rust allocator can't see them.
`ZST-2-window` declares a 2 GiB window, which the reader must refuse from the frame header
before allocating anything (FORMAT_SPEC §12.5). `ZST-2-no-fcs-overflow` and `ZST-2-bomb`
have no content size in their headers, so only the decoder's output cap can catch them.
The bomb would decode to 1 GiB for a 1 MiB `raw_length`, and must fail within 10 seconds
and 64 MiB (N10).

#### AC-X-ATTR-1 — Modification time and mode round-trip; setuid is never stored or set
Extended:#16 · OS linux · fast · Traces: #16, ATT-1
```sh
mkdir -p "$W/t" && echo x > "$W/t/f" && chmod 4755 "$W/t/f" && touch -d @1700000000.5 "$W/t/f"
$CHST pack --attrs "$W/t" -o "$W/c.chst"
$CHST list --json "$W/c.chst" | jq -e '.entries[0].mode == 493 and .entries[0].mtime_seconds == 1700000000 and .entries[0].mtime_nanos == 500000000'
$CHST extract "$W/c.chst" -C "$W/x"
test "$(stat -c %a "$W/x/f")" = 755
# F27: modes are applied as stored (not subject to umask); a read-only directory doesn't block
# its children; directory mtimes survive their children being written.
mkdir -p "$W/u/ro" && echo y > "$W/u/ro/g" && chmod 600 "$W/u/ro/g" && touch -d @1600000000 "$W/u/ro" && chmod 555 "$W/u/ro"
$CHST pack --attrs "$W/u" -o "$W/u.chst"
(umask 077; $CHST extract "$W/u.chst" -C "$W/y")
test "$(stat -c %a "$W/y/ro")" = 555 && test "$(stat -c %a "$W/y/ro/g")" = 600
test "$(stat -c %Y "$W/y/ro")" = 1600000000
chmod 755 "$W/u/ro" "$W/y/ro"
```

#### AC-X-ATTR-2 — `--deterministic` neutralises environment-derived attributes
Extended:#16 · OS all · fast · Traces: #19, D9
```sh
$GEN materialize $FX/core/valid/worked-example/tree.json "$W/t1"
$GEN materialize --reverse $FX/core/valid/worked-example/tree.json "$W/t2"
$CHST pack --attrs --deterministic --mtime 0 "$W/t1" -o "$W/a.chst"
$CHST pack --attrs --deterministic --mtime 0 "$W/t2" -o "$W/b.chst"
cmp "$W/a.chst" "$W/b.chst"
```

#### AC-X-KV-1 — Key/value metadata is written only when given
Extended:#18 · OS all · fast · Traces: #18, KV-1, D5
```sh
mkdir -p "$W/t" && echo x > "$W/t/f"
$CHST pack --meta creator=me --meta comment='hi there' "$W/t" -o "$W/k.chst"
$CHST inspect --json "$W/k.chst" | jq -e '[.sections[].name] == ["BLOB_TABLE","ENTRY_TABLE","PATH_POOL","KV_METADATA"]'
$CHST pack "$W/t" -o "$W/n.chst"
$CHST inspect --json "$W/n.chst" | jq -e '[.sections[].name] | index("KV_METADATA") == null'
```

#### AC-X-SEL-1 — Selective extract by path and glob
Extended:#6 · OS all · fast · Traces: #6, SEL-1, D9
```sh
f=$FX/core/valid/worked-example/container.chst
$CHST extract $f -C "$W/x" 'docs/*.txt'
(cd "$W/x" && find . | sort) | diff - <(printf '.\n./docs\n./docs/a.txt\n./docs/b.txt\n')
$CHST extract $f -C "$W/z" 'docs'
(cd "$W/z" && find . | sort) | diff - <(printf '.\n./docs\n./docs/a.txt\n./docs/b.txt\n./docs/empty\n')
expect_exit 9 $CHST extract $f -C "$W/y" 'docs/*.txt' 'nomatch/*' 2> "$W/err"
grep -q 'error\[refused/extract.no-match\]' "$W/err" && grep -q 'nomatch/\*' "$W/err" && test ! -e "$W/y"
$CHST extract $f -C "$W/q" 'docs/?.txt' 'notes.tx[st]'                 # ? and [...]
(cd "$W/q" && find . | sort) | diff - <(printf '.\n./docs\n./docs/a.txt\n./docs/b.txt\n./notes.txt\n')
$CHST extract $f -C "$W/r" 'docs/[!a].txt'                             # negated class
(cd "$W/r" && find . | sort) | diff - <(printf '.\n./docs\n./docs/b.txt\n')
$CHST extract $f -C "$W/s" 'docs/**'                                   # a/** matches a itself
(cd "$W/s" && find . | sort) | diff - <(printf '.\n./docs\n./docs/a.txt\n./docs/b.txt\n./docs/empty\n')
expect_exit 2 $CHST extract $f -C "$W/u" 'docs\a.txt'                  # no escape character
expect_exit 2 $CHST extract $f -C "$W/v" 'docs/[z-a].txt'              # reversed range (N16)
# N7: a damaged blob that isn't selected doesn't fail a selective extract
expect_exit 0 $CHST extract $FX/core/extract-cases/late-blob-hash.chst -C "$W/sel" 'docs/*.txt'
expect_exit 7 $CHST extract $FX/core/extract-cases/late-blob-hash.chst -C "$W/sel2" 'notes.txt'
```
The behaviour is defined in FORMAT_SPEC §12.8 (F25):
- ancestors of selected entries are created, but aren't themselves selected, so
  `docs/*.txt` doesn't bring in `docs/empty`;
- selecting a directory selects its whole subtree;
- `?`, `[...]`, `[!...]` and `**` behave as specified;
- a backslash is a usage error;
- any pattern that matches nothing is `refused/extract.no-match`, with nothing written.

#### AC-X-EXCL-1 — Exclude patterns when packing
Extended:#7 · OS all · fast · Traces: #7
```sh
mkdir -p "$W/t/logs" "$W/t/src" && echo a > "$W/t/src/a.rs" && echo b > "$W/t/x.log" && echo c > "$W/t/logs/y"
$CHST pack --exclude '*.log' --exclude 'logs' "$W/t" -o "$W/c.chst"
test "$($CHST list --json "$W/c.chst" | jq -c '[.entries[].path]')" = '["src","src/a.rs"]'
if [ "$CHST_OS" = linux ]; then                    # F26: excluded names are never checked (W-3) or descended
  touch "$W/t/logs/a:b"; chmod 000 "$W/t/logs"
  expect_exit 0 $CHST pack --exclude 'logs' --exclude '*.log' "$W/t" -o "$W/d.chst"
  chmod 755 "$W/t/logs"
fi
```

#### AC-X-TS-1 — The TypeScript reader matches the generator's expected JSON on valid fixtures
Extended:TS · OS all · fast · Traces: V11, #28, D13
```sh
(cd ts-reader && npm ci && npm run build)
for d in $FX/core/valid/*/ $FX/extended/valid/*/; do for c in list verify; do
  [ -f "$d/$c.json" ] || continue
  node ts-reader/dist/cli.js $c --json "$d/container.chst" > "$W/r.json"
  diff <(jqn "$W/r.json") <(jqn "$d/$c.json")
done; done
```

#### AC-X-TS-2 — The TypeScript reader gives the same errors on invalid and compat fixtures
Extended:TS · OS all · fast · Traces: V11, D12
The same script as AC-NEG-2 and AC-COMPAT-1, with `node ts-reader/dist/cli.js` in place of
`$CHST`. For compat, the reader behaves as a Core reader unless it implements the
feature.

#### AC-X-TS-3 — The TypeScript reader is independent
Extended:TS · OS all · fast · Traces: V11, D15, D16
```sh
if grep -rnE 'chst-format|\.rs|target/|wasm|fixtures/gen' ts-reader/src; then exit 1; fi
grep -rqF 'node:crypto' ts-reader/src
jq -e '(.dependencies // {} | length) == 0' ts-reader/package.json
jq -e '.devDependencies // {} | keys | all(. == "typescript" or . == "@types/node")' ts-reader/package.json
node --version | grep -qE '^v24\.'
test "$(node -p process.versions.unicode)" = 16.0                    # F12: Unicode 16.0 tables
```
The expected values come from the generator's fixtures, never from the Rust code. The
reader has no runtime dependencies (D15): it uses `node:crypto` for SHA-256 and
`node:zlib` for Zstandard. Moving to `fzstd` would need a decision.

## 4. Traceability matrix (Core)

| Feature / decision | Criteria |
|---|---|
| #1 pack | AC-POS-1, AC-DET-3, AC-PACK-1 … AC-PACK-9 |
| #2 list | AC-POS-2, AC-NEG-3 |
| #3 extract | AC-POS-4, AC-SAFE-1 … AC-SAFE-11 |
| #4 verify | AC-POS-2, AC-NEG-2, AC-ROB-1, AC-ROB-2 |
| #5 inspect | AC-POS-2, AC-POS-3, AC-NEG-3 |
| #8 --json | AC-POS-2, AC-NEG-2 |
| #13 checksums | AC-ROB-1 |
| #14 index | AC-POS-1, AC-POS-3, AC-META-6 |
| #15 64-bit | AC-ROB-7 (full), AC-ROB-8, AC-ROB-9 (fast), AC-ROB-6 |
| #17 empty dirs | AC-POS-1, AC-POS-4 |
| #18a extension mechanism | AC-COMPAT-1 |
| #19 deterministic | AC-POS-1, AC-DET-1, AC-META-5 |
| #21 dedup | AC-DET-2, AC-POS-1 |
| #23 safe extract | AC-SAFE-1 … AC-SAFE-11 |
| #24 limits | AC-LIM-1 … AC-LIM-4 |
| #25 errors | AC-NEG-2, AC-CLI-1 |
| #26 no panic | AC-ROB-1 … AC-ROB-5, AC-ROB-4W, AC-ENG-2 |
| #27 lib + CLI | AC-ENG-1 … AC-ENG-4 |
| #28 fixtures | AC-META-2, AC-META-4, AC-META-5 |
| G1 / G3 paths and collisions | AC-NEG-1 (PATH-*), AC-PACK-1, AC-SAFE-1 |
| G2 versioning | AC-COMPAT-1 |
| G4 extract conflicts | AC-SAFE-2 |
| G5 atomic write | AC-PACK-4, AC-PACK-6 |
| G6 bounded memory | AC-ROB-6, AC-LIM-1 |
| G7 negative fixtures | AC-NEG-1, AC-NEG-4 |
| G8 fuzzing | AC-ROB-4, AC-ROB-4W |
| G9 JSON schema | AC-POS-2, AC-NEG-2 |
| D1 | AC-META-6, AC-ROB-2 |
| D2 | AC-DET-2, AC-PACK-3 |
| D3 | AC-META-6, AC-ROB-7, AC-ROB-8, AC-ROB-9 |
| D4 | AC-META-6, AC-POS-3 |
| D5 | AC-COMPAT-1 |
| D6 | AC-META-4, AC-META-6, AC-ROB-1 |
| D7 | AC-X-ZSTD-1, AC-X-ZSTD-2 (Extended) |
| D8 (incl. platform rules) | AC-NEG-1, AC-PACK-1, AC-PACK-7 … AC-PACK-9, AC-SAFE-5 … AC-SAFE-11 |
| D9 | AC-POS-1, AC-DET-1, AC-DET-3 |
| D10 | AC-SAFE-1 … AC-SAFE-4, AC-SAFE-8 |
| D11 | AC-LIM-1 … AC-LIM-4 |
| D12 | AC-NEG-2, AC-CLI-1, AC-CLI-2 |
| D13 | AC-ENG-2, AC-ENG-3 |
| D14 | AC-PACK-4, AC-PACK-6 |
| D15 | AC-ENG-5, AC-META-4, AC-X-TS-3 |
| D16 | AC-ENG-6, AC-META-7 |
| D17 | AC-XP-1, AC-XP-2 |
| D18 | AC-ENG-7, AC-ENG-2 |

## 5. Pinned fixture manifest

```
PINNED_MANIFEST_HASH = <PENDING — set by the owner when the generated fixture set is first approved>
```

Until this value is set, AC-META-2 FAILs. That's intentional: fixtures need owner approval
before any implementation can claim done.
