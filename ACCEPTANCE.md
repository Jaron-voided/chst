# Chst — Acceptance Criteria

> Status: **DRAFT for independent review.** Every criterion below has a runnable check and
> an observable pass condition. Statements of success without a passing `check.sh` report
> do not count.
> References: feature IDs (`#n`, `Gn`) and decisions (`Dn`) are in [`DESIGN.md`](DESIGN.md);
> rule IDs (`HDR-1`, …) are in [`FORMAT_SPEC.md`](FORMAT_SPEC.md) Appendix A.

## 1. How to run

| Command | Runs | Exit code |
|---|---|---|
| `./check.sh` | Every criterion except the `full-only` ones (AC-ROB-4 fuzzing and the AC-ROB-7 5 GiB round-trip), which are reported as `NOT RUN` | 0 all PASS or N/A · 1 any FAIL · **2 no FAIL, but at least one NOT RUN** |
| `./check.sh --full` | Every criterion, including the full-only ones | Same |
| `./check.sh --only AC-POS-1,AC-NEG-2` | Only the named criteria (development aid; never evidence of done) | Same |
| `./check.sh --list-ids` | Prints every AC ID it implements, one per line | 0 |
| `./check.sh --done <ci-run-id>` | Only AC-XP-1, the final done check over the CI reports from all three OSes | Same |

So a fast run can never exit 0: it always reports AC-ROB-4 and AC-ROB-7 as NOT RUN, and
exits 2 if nothing failed. Fast mode still covers 64-bit sizes through AC-ROB-8 (small
fixtures that declare sizes over 4 GiB) and AC-ROB-9 (a sparse, valid 5 GiB container).

**Report.** Every run writes `target/acceptance/report.json`:

```json
{
  "schema": "chst-acceptance/1",
  "run": "fast | full | partial",
  "os": "linux | macos | windows",
  "commit": "<git sha>",
  "dirty": false,
  "results": [
    {"id": "AC-POS-1", "status": "PASS | FAIL | NOT RUN | N/A", "exit_code": 0,
     "duration_s": 1.2, "log": "target/acceptance/logs/AC-POS-1.log"}
  ]
}
```

- `N/A` is allowed only for criteria whose **OS** line excludes the current OS, for AC-XP-1
  outside `--done`, and for Extended criteria whose feature isn't built yet (§3.13).
- Each check's combined stdout and stderr is saved to its `log` file. The logs are the
  evidence.
- `check.sh` runs each check **exactly as written below**, in a fresh empty working
  directory `$W`, under `bash -euo pipefail`. On Windows CI it runs under the runner's
  bash (Git Bash, `shell: bash`).
- **Local versus CI evidence.** The owner develops and runs checks locally on Linux (WSL).
  Run them from the Linux filesystem, not `/mnt/<drive>`, which has Windows filesystem
  semantics. Local runs count as Linux evidence only. **The only evidence for macOS and
  Windows is a CI run**, and `EVIDENCE.md` MUST link it (§2).

### 1.1 Conventions used by checks

| Name | Meaning |
|---|---|
| `$CHST` | `target/release/chst`, the full build with default features |
| `$CHST_CORE` | A build with `--no-default-features`. Core only: Extended features are behind Cargo features that are on by default |
| `$FX` | `fixtures` |
| `$GEN` | `python3 -I tools/fixturegen/gen.py` |
| `$W` | A fresh temporary directory per criterion |
| `jqn FILE` | `jq -S 'walk(if type=="object" then del(.message) else . end)' FILE`: normalised JSON for comparison (FORMAT_SPEC Appendix B) |
| `expect_exit N CMD…` | Runs CMD and fails unless its exit code is exactly N |
| `mk_sparse FILE SIZE` | Creates a sparse file of SIZE. On Linux and macOS this is `truncate -s`. On Windows: create the file empty, run `fsutil sparse setflag` on it, then `truncate -s`. |
| `$CHST_BIG_TMP` | A scratch directory with at least 12 GiB free, set by the CI workflow per runner (§1.2). Locally it defaults to `$W`. |

**Fixture layout**, produced only by `$GEN` (V1):

- **Valid fixtures:** `fixtures/core/valid/<name>/` holds:
  - `tree.json`: the source tree as data, so empty directories and awkward names survive git;
  - `container.chst`;
  - `list.json`, `verify.json` and `inspect.json`: the expected reports.
- **Invalid fixtures:** `fixtures/core/invalid/<RULE>[-n].chst` plus `<RULE>[-n].expect.json`
  containing `{"rule", "category", "detail", "exit", "base", "mutation"}`.
- `fixtures/core/attacks/`, `fixtures/core/hostile/`, `fixtures/compat/` and
  `fixtures/extended/{valid,invalid}/` follow the same pattern.
- `fixtures/fuzz-regressions/<target>/`: every input that ever crashed a fuzz target.
- `fixtures/MANIFEST.blake3`: a `b3sum` listing of every other file under `fixtures/`.

`$GEN materialize TREE.json DIR [--reverse]` creates the tree on disk. `--reverse` creates
entries in reverse order and sets random mtimes and modes, to stress determinism.
`$GEN materialize-sparse RECIPE.json FILE` writes a recipe's head bytes at offset 0 and
its tail bytes at the end of an existing sparse FILE, without filling the hole.

### 1.2 CI runners and heavy checks

The workflow (an early task; see DESIGN.md §10) runs `./check.sh --full` on
`ubuntu-latest`, `macos-latest` and `windows-latest`. Two criteria stress the runners.
Neither is confirmed yet, because the workflow doesn't exist. **The first full CI run is
the confirmation.**

| Check | ubuntu-latest (x64) | macos-latest (arm64, M1) | windows-latest (x64) |
|---|---|---|---|
| AC-ROB-4 cargo fuzz (nightly, ASan) | Supported per the cargo-fuzz book | Supported (Apple Silicon is listed) | Supported per the book, via MSVC AddressSanitizer. The least-proven of the three. |
| AC-ROB-7 5 GiB round-trip, about 10 GiB peak disk (5 GiB container plus 5 GiB extracted; sparse source) | Documented SSD 14 GB, so tight. The workflow frees preinstalled toolchains first and uses the largest volume for `$CHST_BIG_TMP`. | Documented SSD 14 GB and no second volume, so **most at risk** | Documented SSD 14 GB. `$CHST_BIG_TMP` goes on the larger of `C:` and `D:`. |

Rules, so no check is dropped silently:

- On every OS these two criteria run in full mode. If one can't run on a runner (the tool is
  missing, the build fails, or there's too little disk), it reports **FAIL** for that OS,
  never N/A. Core is then not done.
- Before AC-ROB-7 runs, the workflow logs free space at `$CHST_BIG_TMP` (`df -h`) and the
  output of `cargo +nightly fuzz --version`.
- **Proposed relocation if a runner can't do it.** The owner must approve any relocation by
  editing that criterion's OS line, in a commit that cites the failing CI run.
  - AC-ROB-7 on macOS or Windows, if disk is short: run it on that OS's GitHub larger
    runner, which has more disk but costs money. The cheaper alternative is a
    4 GiB + 1 MiB file there (about 8 GiB peak). It still puts the high 32 bits into use in
    every size field.
  - AC-ROB-4 on Windows, if cargo-fuzz or ASan fails: the format crate has no OS code
    (AC-ENG-2), so Linux and macOS fuzzing cover its logic. Windows keeps AC-ROB-1, AC-ROB-3
    and AC-ROB-5 (sweeps and the regression corpus) and adds a 10-minute run of those
    sweeps with randomised inputs.

## 2. Definition of Done

- **Core v1 is done** when all of the following hold:
  - `./check.sh --full` passes on Linux, macOS and Windows CI for the same commit, with
    `dirty: false`, and the three reports are attached to that CI run;
  - `EVIDENCE.md` has an entry linking that CI run (§2.1);
  - `./check.sh --done <ci-run-id>` (AC-XP-1) then exits 0.

  Every Core criterion must be PASS, or N/A where its OS line excludes that OS.
- **Each Extended feature is done** when, for one commit, its own criteria (§3.13) pass and
  every Core criterion still passes, by the same full-run, three-OS rule.
- **Fuzz findings:** any crash, timeout or out-of-memory found by any fuzz run (including
  optional longer runs) MUST be minimised and added to `fixtures/fuzz-regressions/`. The
  fix is not done until AC-ROB-5 passes with it.
- **Changes to fixtures or this document** require owner approval. AC-META-2 enforces this
  for fixtures.

### 2.1 EVIDENCE.md

`EVIDENCE.md` (repo root) is the ledger of claimed results. Each claim is one table row:

```
| <date> | <commit sha> | <scope: Core | Extended:<feature>> | https://github.com/<owner>/<repo>/actions/runs/<id> | linux: PASS | macos: PASS | windows: PASS |
```

- macOS and Windows results MUST come from the linked CI run. A local WSL run may be listed
  for Linux only, with its `report.json` summary and `run: local`, never in place of CI.
- AC-XP-1 checks the row against the CI run itself.

## 3. Criteria

Each criterion lists its **tier** (Core, or Extended:<feature>), the **OS** it runs on, its
**mode** (fast, or full-only), and what it **traces to**. Pass means the shown script exits
0, unless stated otherwise.

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
test "$(b3sum --no-names fixtures/MANIFEST.blake3)" = "$PINNED_MANIFEST_HASH"
(cd fixtures && b3sum --check --quiet MANIFEST.blake3)
diff <(cd fixtures && find . -type f ! -name MANIFEST.blake3 | sed 's|^\./||' | sort) \
     <(sed 's/^[0-9a-f]* *//' fixtures/MANIFEST.blake3 | sort)
```
`$PINNED_MANIFEST_HASH` is the value in §5. Pass: exit 0.

#### AC-META-3 — Every Core feature, decision and rule is traced
Core · OS all · fast · Traces: Layer B
```sh
python3 -I tools/acceptance/trace.py DESIGN.md FORMAT_SPEC.md ACCEPTANCE.md
```
Pass: exit 0 and the final line is `untraced: 0`.

`trace.py` MUST fail if any of the following is missing from at least one `Traces:` line:
- a Core feature ID in DESIGN.md §2.1;
- a decision `D1`–`D14`;
- a `W-`, `EXT-` or `SEL-` rule in FORMAT_SPEC Appendix A.

Reader rules are covered collectively by AC-NEG-1.

#### AC-META-4 — The fixture generator is independent of the implementation
Core · OS all · fast · Traces: V1
```sh
! grep -rnE 'subprocess|os\.system|cargo|chst_|target/' tools/fixturegen
grep -qxE 'blake3==[0-9.]+' tools/fixturegen/requirements.txt
! grep -vxE '(blake3|zstandard)==[0-9.]+' tools/fixturegen/requirements.txt
grep -rqE '^(import blake3|from blake3 import)' tools/fixturegen
! grep -rniE '0x6a09e667|0xbb67ae85|def (compress|g)\(' tools/fixturegen
```
Pass: exit 0.
- The generator uses only the Python standard library, plus the **official** `blake3`
  package (pinned), plus pinned `zstandard` for Extended.
- It contains no hand-written BLAKE3: the last line looks for BLAKE3's IV constants and
  compression function.
- It never invokes the Rust code.

#### AC-META-5 — Fixtures regenerate exactly
Core · OS linux · fast · Traces: V1, D9
```sh
$GEN --out "$W/fx" && diff -r "$W/fx" fixtures
```
Pass: empty diff.

#### AC-META-6 — The worked example in FORMAT_SPEC §18 is the golden fixture
Core · OS all · fast · Traces: V1, #14, D1, D3, D4, D6
```sh
f=$FX/core/valid/worked-example/container.chst
test "$(wc -c < $f | tr -d ' ')" = 556
test "$(b3sum --no-names $f)" = ea72c78adbd0d0e98ebcdecdc060398796c5b3eebc22136da409e6c602b6876a
python3 -I tools/acceptance/spec_hexdump.py FORMAT_SPEC.md | cmp - $f
```
`spec_hexdump.py` parses the §18.3 hex dump back into bytes. Pass: exit 0.

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
! grep -rnE 'std::fs|std::env|std::process|std::net|unsafe' crates/chst-format/src
cargo tree -p chst-format -e normal --depth 1 --prefix none --no-default-features \
  | tail -n +2 | awk '{print $1}' | sort -u > "$W/deps"
diff "$W/deps" <(printf 'blake3\nunicode-normalization\n')
```
Pass: exit 0, meaning the Core build's direct dependencies are exactly `blake3` and
`unicode-normalization`.

#### AC-ENG-3 — The CLI is thin
Core · OS all · fast · Traces: D13, #27
```sh
! cargo tree -p chst-cli -e normal --depth 1 --prefix none | grep -E '^(blake3|unicode-normalization|zstd) '
```
Pass: exit 0. The CLI reaches hashing, normalisation and compression only through
`chst-format` and `chst-fs`.

#### AC-ENG-4 — The test suite passes
Core · OS all · fast · Traces: #27
```sh
cargo test --workspace --locked --release
```

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
  python3 -I tools/acceptance/inspect_check.py "$W/i.json" "$d/container.chst"
done
```
`inspect_check.py` MUST check four things:
- every field's `offset + length` lies within the file;
- fields don't overlap;
- the fields together cover every byte of the file;
- each integer or hex `value` equals the bytes at its offset, decoded little-endian.

#### AC-POS-4 — Extract reproduces the tree, including empty directories
Core · OS all · fast · Traces: #3, #17, D10
```sh
for d in $FX/core/valid/*/; do
  rm -rf "$W/t" "$W/x"
  $GEN materialize "$d/tree.json" "$W/t"
  expect_exit 0 $CHST extract "$d/container.chst" -C "$W/x"
  python3 -I tools/acceptance/tree_eq.py "$W/t" "$W/x"
done
```
`tree_eq.py` compares the set of paths, entry types and file bytes, and prints the
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

### 3.4 Negative conformance (V3, G7)

#### AC-NEG-1 — Every reader rule has at least one negative fixture
Core · OS all · fast · Traces: G7, D12, all reader rules in FORMAT_SPEC Appendix A
```sh
for r in $(grep -oE '^\| \*\*(HDR|TRL|SEC|BLB|ENT|PATH|CAN|FLG|LIM)-[0-9]+\*\*' FORMAT_SPEC.md | tr -d '|* '); do
  ls $FX/core/invalid/$r.chst $FX/core/invalid/$r-*.chst 2>/dev/null | grep -q . || { echo "missing $r"; exit 1; }
done
```
For each configurable-limit rule (LIM-3 to LIM-6), the fixture's `expect.json` includes the
CLI limit flag that triggers it, in an `args` field. Extended rules (ZST, ATT, KV) are
covered by AC-X-NEG-1.

#### AC-NEG-2 — Each negative fixture gives exactly the expected category, detail and exit code
Core · OS all · fast · Traces: D12, #25, #26
```sh
for e in $FX/core/invalid/*.expect.json; do
  f=${e%.expect.json}.chst; args=$(jq -r '.args // [] | join(" ")' $e)
  set +e; $CHST verify --json $args "$f" > "$W/r.json" 2> "$W/err"; rc=$?; set -e
  test $rc = "$(jq .exit $e)"
  test "$(jq -r .error.category "$W/r.json")" = "$(jq -r .category $e)"
  test "$(jq -r .error.detail   "$W/r.json")" = "$(jq -r .detail $e)"
  test "$(jq -c 'keys' "$W/r.json")" = '["command","error","ok","schema","warnings"]'
  head -1 "$W/err" | grep -qE "^chst: error\[$(jq -r .category $e)/$(jq -r .detail $e)\]: "
done
```

#### AC-NEG-3 — `list` and `inspect` also reject structurally invalid files
Core · OS all · fast · Traces: #2, #5, D12
```sh
for e in $FX/core/invalid/*.expect.json; do
  case "$(jq -r .rule $e)" in BLB-6|LIM-5) continue;; esac   # need blob data / verify+extract only
  f=${e%.expect.json}.chst; args=$(jq -r '.args // [] | join(" ")' $e)
  for c in list inspect; do expect_exit "$(jq .exit $e)" $CHST $c --json $args "$f" >/dev/null; done
done
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
PROPTEST_CASES=256 cargo test --release -p chst-fs --test roundtrip_prop
```
The property test generates random portable trees (empty directories, duplicate contents,
Unicode names) and checks three things: pack then extract gives an identical tree, packing
twice gives identical bytes, and verify exits 0.

### 3.6 Integrity and robustness (V5, V6)

#### AC-ROB-1 — Flipping any single byte is always detected (CLI, exhaustive)
Core · OS all · fast · Traces: #4, #13, D1, D6, #26
```sh
python3 -I tools/acceptance/flip_sweep.py "$CHST" $FX/core/valid/worked-example/container.chst \
  $FX/core/valid/empty/container.chst $FX/core/valid/dedup/container.chst
```
For every byte offset, and for each of XOR `0x01` and XOR `0xFF`, `flip_sweep.py` runs
`verify` on the mutated file. It asserts that the exit code is one of 4, 5, 6 or 7, never 0,
70 or 101, that stderr has no `panicked`, and that each run takes under 5 seconds. It prints
a histogram of detail codes. Pass: exit 0.

#### AC-ROB-2 — Truncation and extension are always detected
Core · OS all · fast · Traces: #4, D1, #26
```sh
python3 -I tools/acceptance/truncate_sweep.py "$CHST" $FX/core/valid/worked-example/container.chst
```
- Every prefix length from 0 to N−1 must exit with 4 when the length is below 88, and with 6
  (`trl.magic`) otherwise.
- Appending 1 byte, or 4096 bytes, must exit non-zero.
- Never 0, 70 or 101.

#### AC-ROB-3 — Library damage sweep across every valid fixture
Core · OS all · fast · Traces: #26, V5
```sh
cargo test --release -p chst-format --test damage_sweep
```
For every valid fixture up to 64 KiB, at every offset, the test applies single-bit and
single-byte flips plus all truncations. Each must return an error, never success, with no
panic.

#### AC-ROB-4 — Fuzzing: 10 crash-free minutes per target
Core · OS all · **full-only** · Traces: #26, G8, V6
```sh
for t in open_verify list inspect; do
  cargo +nightly fuzz run $t -- -max_total_time=600 -rss_limit_mb=512 -timeout=10 \
    fuzz/corpus/$t $FX/core/valid $FX/core/invalid
  test -z "$(ls -A fuzz/artifacts/$t 2>/dev/null)"
done
```
Pass: exit 0 and no artifacts. In a fast run this criterion is NOT RUN. Runner support
and the relocation rule are in §1.2.

#### AC-ROB-5 — Fuzz regressions stay fixed
Core · OS all · fast · Traces: #26, V6
```sh
cargo test --release -p chst-format --test fuzz_regressions
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

#### AC-ROB-7 — Files over 4 GiB round-trip (64-bit sizes)
Core · OS all · **full-only** (owner-approved exception) · Traces: #15, D3
```sh
B="$CHST_BIG_TMP/AC-ROB-7"; rm -rf "$B"; mkdir -p "$B/t"
df -h "$CHST_BIG_TMP"
mk_sparse "$B/t/huge.bin" 5G
$CHST pack "$B/t" -o "$B/o.chst"
$CHST list --json "$B/o.chst" | jq -e '.entries[0].size == 5368709120'
$CHST verify "$B/o.chst"
$CHST extract "$B/o.chst" -C "$B/x"
test "$(b3sum --no-names "$B/x/huge.bin")" = "$(b3sum --no-names "$B/t/huge.bin")"
rm -rf "$B"
```
The source is sparse. Peak disk is about 10 GiB (the container plus the extracted copy).
Runner feasibility and the relocation rule are in §1.2.

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
values and wrongly accept the file. Each `expect.json` lists the acceptable `details`.
Where one change necessarily breaks two rules, either is accepted. The set MUST cover:

| Value(s) + 2³² | Acceptable details |
|---|---|
| `blob[0].offset` | `blob.layout` |
| `blob[0].stored_length` and `blob[0].raw_length` together (keeps BLB-3 true) | `blob.layout` |
| `blob[0].raw_length` | `blob.raw-length` |
| `entry[1].path_offset` | `entry.path-range`, `canon.path-pool` |
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
```

#### AC-SAFE-3 — A hash failure mid-extract leaves no destination and no staging directory
Core · OS all · fast · Traces: EXT-4, EXT-7, D10
```sh
mkdir -p "$W/p"
expect_exit 7 $CHST extract $FX/core/extract-cases/late-blob-hash.chst -C "$W/p/out" 2> "$W/err"
grep -q 'error\[integrity/blob.hash\]' "$W/err"
test -z "$(ls -A "$W/p")"
```
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
$CHST list --json $FX/core/valid/long-names/container.chst | jq -r '.entries[].path' | while read -r p; do test -e "$W/x/$p"; done
```

#### AC-SAFE-8 — Links and reparse points swapped in during extraction are never followed
Core · OS all · fast · Traces: EXT-8, EXT-6, D10
```sh
cargo test --release -p chst-fs --test swap_race
```
A test hook pauses extraction right after a directory is created in staging. It replaces
that directory with a symlink (Unix) or a junction (Windows) pointing outside, then
resumes. The test asserts three things: the result is `refused/extract.unsafe-object`,
nothing was created or modified outside staging, and staging and the destination are both
gone.

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
fsutil 8dot3name query "$(cygpath -w "$W")" || true          # logged: shows which branch applies
set +e; $CHST extract "$f" -C "$W/p/out" 2> "$W/err"; rc=$?; set -e
if [ $rc = 9 ]; then grep -q 'extract.collision' "$W/err" && test -z "$(ls -A "$W/p")"
else test $rc = 0 && test "$(ls "$W/p/out/ABCDEFGHIJ")" = a && test "$(ls "$W/p/out/ABCDEF~1")" = b; fi
```
`short-name.chst` holds `ABCDEFGHIJ/a` and then `ABCDEF~1/b`, in canonical order. If the
volume generates 8.3 names, the second directory collides with the first one's short name
and must be refused. Otherwise both are distinct directories. Either way, `b` never lands
inside `ABCDEFGHIJ`.

#### AC-SAFE-11 — macOS: decomposed source names round-trip as NFC
Core · OS macos · fast · Traces: W-9, PATH-2, D8
```sh
mkdir -p "$W/t" && echo x > "$W/t/$(printf 'e\xcc\x81')"          # NFD é
$CHST pack "$W/t" -o "$W/c.chst"
$CHST list --json "$W/c.chst" | jq -e '[.entries[].path] == ["\u00e9"]'
$CHST extract "$W/c.chst" -C "$W/x"
python3 -I tools/acceptance/tree_eq.py --nfc "$W/t" "$W/x"
```

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
cargo test --release -p chst-fs --test source_changed
```
The test uses a fault-injecting source that returns different bytes on its second read. It
asserts `refused/pack.source-changed` and that no output file exists.

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

#### AC-PACK-5 — An output path inside the source tree is refused
Core · OS all · fast · Traces: W-6
```sh
mkdir -p "$W/t" && echo x > "$W/t/f"
expect_exit 9 $CHST pack "$W/t" -o "$W/t/self.chst" 2> "$W/err"
grep -q 'pack.output-in-source' "$W/err" && test ! -e "$W/t/self.chst"
```

### 3.9 Limits (V8)

#### AC-LIM-1 — Hostile declared sizes fail fast with bounded memory
Core · OS all · fast · Traces: #24, D11, #26
```sh
cargo test --release -p chst-format --test hostile_sizes
for e in $FX/core/hostile/*.expect.json; do
  expect_exit "$(jq .exit $e)" timeout 2 $CHST verify "${e%.expect.json}.chst"
done
```
The hostile fixtures declare an `index_length` near 2⁶⁴, a `record_count` of 2⁶⁰, 2³²
entries, and a path length of 2³²−1, all inside files under 1 KiB. `hostile_sizes` uses a
counting allocator and asserts peak heap under 1 MiB per fixture.

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
```

#### AC-CLI-2 — Warnings never change the exit code and appear in the JSON
Core · OS linux, macos · fast · Traces: D12, W-5
```sh
mkdir -p "$W/t" && mkfifo "$W/t/p" && echo x > "$W/t/f"
expect_exit 0 $CHST pack --json "$W/t" -o "$W/c.chst" | jq -e '.warnings[0].detail == "pack.skipped"'
```
`pack --json` emits a `chst-report/1` object with `command: "pack"` (FORMAT_SPEC
Appendix B).

### 3.11 Compatibility (V9)

#### AC-COMPAT-1 — A Core build handles Extended and future files as the spec requires
Core · OS all · fast · Traces: #18a, G2, D5, SEC-2, SEC-5, HDR-6
```sh
for e in $FX/compat/*.expect.json; do
  f=${e%.expect.json}.chst
  set +e; $CHST_CORE verify --json "$f" > "$W/r.json"; rc=$?; set -e
  test $rc = "$(jq .exit $e)"
  jq -e --slurpfile x $e '($x[0].detail == null) or (.error.detail == $x[0].detail)' "$W/r.json"
  if [ "$rc" = 0 ]; then diff <($CHST_CORE list --json "$f" | jqn /dev/stdin) <(jqn ${e%.expect.json}.list.json); fi
done
```

The compat set MUST include:

| Fixture | Expected result |
|---|---|
| `ZSTD` required flag | 5 / `hdr.required-flag` |
| Unknown required bit 63 | 5 |
| `ENTRY_ATTRS` (64-byte entry records) | 0, listed without attributes |
| `KV_METADATA` section | 0 |
| Unknown optional bit 63 | 0 |
| Unknown non-critical section `0x7FFFFFF0` | 0 |
| Unknown critical section `0xFFFFFFF0` | 5 / `sec.unknown-critical` |
| `minor_version` 65535 | 0 |
| `major_version` 2 | 5 / `hdr.major-version` |
| `hash_alg` 2 | 5 / `hdr.hash-alg` |

### 3.12 Cross-platform (V10)

#### AC-XP-1 — Full runs pass on all three OSes for one commit, recorded in EVIDENCE.md
Core · OS any · **done-check** (`./check.sh --done <ci-run-id>`; N/A in other runs) · Traces: V10, Definition of Done
```sh
gh run download "$CI_RUN_ID" --pattern 'acceptance-report-*' --dir "$W/r"
test "$(jq -r .os "$W"/r/*/report.json | sort -u | tr '\n' ' ')" = 'linux macos windows '
test "$(jq -r .commit "$W"/r/*/report.json | sort -u | wc -l)" -eq 1
sha=$(jq -r .commit "$W"/r/*/report.json | head -1)
test "$(gh run view "$CI_RUN_ID" --json headSha -q .headSha)" = "$sha"
for r in "$W"/r/*/report.json; do
  jq -e '.run == "full" and .dirty == false and all(.results[] | select(.id != "AC-XP-1"); .status == "PASS" or .status == "N/A")' "$r"
done
grep -F "actions/runs/$CI_RUN_ID" EVIDENCE.md | grep -F "$sha" | grep -q 'macos: PASS' 
grep -F "actions/runs/$CI_RUN_ID" EVIDENCE.md | grep -F "$sha" | grep -q 'windows: PASS'
```
The CI workflow runs `./check.sh --full` on `ubuntu-latest`, `macos-latest` and
`windows-latest`, and uploads `target/acceptance/report.json` as `acceptance-report-<os>`.
On Windows it runs under the runner's bash.

### 3.13 Extended criteria

These criteria are reported as `N/A` until their feature's Cargo feature exists. After
that they are mandatory for that feature's done.

#### AC-X-NEG-1 — Extended negative fixtures (ZST, ATT, KV)
Extended:all · OS all · fast · Traces: ZST-1…3, ATT-1, KV-1, D7
Same script as AC-NEG-1 and AC-NEG-2, over `$FX/extended/invalid` with prefixes
`ZST|ATT|KV`.

#### AC-X-ZSTD-1 — Compressed round-trip; compressed only when smaller
Extended:#12 · OS all · fast · Traces: #12, D7, ZST-3
```sh
for d in $FX/extended/valid/zstd-*/; do
  rm -rf "$W/t" "$W/x"; $GEN materialize "$d/tree.json" "$W/t"
  $CHST pack --compress zstd "$W/t" -o "$W/c.chst"
  diff <($CHST list --json "$W/c.chst" | jq -S '[.entries[] | {path,type,size,encoding}]') \
       <(jq -S '[.entries[] | {path,type,size,encoding}]' "$d/list.json")
  $CHST extract "$W/c.chst" -C "$W/x" && python3 -I tools/acceptance/tree_eq.py "$W/t" "$W/x"
done
```
The fixtures include incompressible random data, which must list as `encoding: "stored"`.
Comparison deliberately excludes compressed sizes and keys (D7).

#### AC-X-ZSTD-2 — Decompression bombs are contained
Extended:#12 · OS all · fast · Traces: ZST-1, LIM-6, D11
```sh
cargo test --release -p chst-format --features zstd --test zstd_bombs
```
The test covers three cases:
- a frame that decodes to more than `raw_length` gives `integrity/zstd.raw-length`;
- a ratio above 1000 gives `limit-exceeded/limit.ratio`;
- peak heap stays under 8 MiB above the baseline.

#### AC-X-ATTR-1 — Modification time and mode round-trip; setuid is never stored or set
Extended:#16 · OS linux · fast · Traces: #16, ATT-1
```sh
mkdir -p "$W/t" && echo x > "$W/t/f" && chmod 4755 "$W/t/f" && touch -d @1700000000.5 "$W/t/f"
$CHST pack --attrs "$W/t" -o "$W/c.chst"
$CHST list --json "$W/c.chst" | jq -e '.entries[0].mode == 493 and .entries[0].mtime_seconds == 1700000000 and .entries[0].mtime_nanos == 500000000'
$CHST extract "$W/c.chst" -C "$W/x"
test "$(stat -c %a "$W/x/f")" = 755
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
```
The behaviour is defined in FORMAT_SPEC §12.8:
- ancestors of selected entries are created;
- selecting a directory selects its whole subtree;
- any pattern that matches nothing is `refused/extract.no-match`, with nothing written.

#### AC-X-EXCL-1 — Exclude patterns when packing
Extended:#7 · OS all · fast · Traces: #7
```sh
mkdir -p "$W/t/logs" "$W/t/src" && echo a > "$W/t/src/a.rs" && echo b > "$W/t/x.log" && echo c > "$W/t/logs/y"
$CHST pack --exclude '*.log' --exclude 'logs' "$W/t" -o "$W/c.chst"
test "$($CHST list --json "$W/c.chst" | jq -c '[.entries[].path]')" = '["src","src/a.rs"]'
```

#### AC-X-TS-1 — The TypeScript reader matches the Rust reports on valid fixtures
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
Extended:TS · OS all · fast · Traces: V11
```sh
! grep -rnE 'chst-format|\.rs|target/|wasm' ts-reader/src
jq -e '.dependencies // {} | keys | all(. == "@noble/hashes" or . == "fzstd")' ts-reader/package.json
```

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
| #26 no panic | AC-ROB-1 … AC-ROB-5, AC-ENG-2 |
| #27 lib + CLI | AC-ENG-1 … AC-ENG-4 |
| #28 fixtures | AC-META-2, AC-META-4, AC-META-5 |
| G1 / G3 paths and collisions | AC-NEG-1 (PATH-*), AC-PACK-1, AC-SAFE-1 |
| G2 versioning | AC-COMPAT-1 |
| G4 extract conflicts | AC-SAFE-2 |
| G5 atomic write | AC-PACK-4, AC-PACK-6 |
| G6 bounded memory | AC-ROB-6, AC-LIM-1 |
| G7 negative fixtures | AC-NEG-1, AC-NEG-4 |
| G8 fuzzing | AC-ROB-4 |
| G9 JSON schema | AC-POS-2, AC-NEG-2 |
| D1 | AC-META-6, AC-ROB-2 |
| D2 | AC-DET-2, AC-PACK-3 |
| D3 | AC-META-6, AC-ROB-7, AC-ROB-8, AC-ROB-9 |
| D4 | AC-META-6, AC-POS-3 |
| D5 | AC-COMPAT-1 |
| D6 | AC-META-6, AC-ROB-1 |
| D7 | AC-X-ZSTD-1, AC-X-ZSTD-2 (Extended) |
| D8 (incl. platform rules) | AC-NEG-1, AC-PACK-1, AC-PACK-7 … AC-PACK-9, AC-SAFE-5 … AC-SAFE-11 |
| D9 | AC-POS-1, AC-DET-1, AC-DET-3 |
| D10 | AC-SAFE-1 … AC-SAFE-4, AC-SAFE-8 |
| D11 | AC-LIM-1 … AC-LIM-4 |
| D12 | AC-NEG-2, AC-CLI-1, AC-CLI-2 |
| D13 | AC-ENG-2, AC-ENG-3 |
| D14 | AC-PACK-4, AC-PACK-6 |

## 5. Pinned fixture manifest

```
PINNED_MANIFEST_HASH = <PENDING — set by the owner when the generated fixture set is first approved>
```

Until this value is set, AC-META-2 FAILs. That's intentional: fixtures need owner approval
before any implementation can claim done.

## 6. Review round 1: resolved items

| Item | Resolution |
|---|---|
| 5 GiB test full-only | Accepted as a full-only exception (AC-ROB-7). Fast mode covers 64-bit sizes through AC-ROB-8 and AC-ROB-9. |
| Pack onto an existing output | Refused unless `--force`, which replaces atomically (W-7, D14; AC-PACK-4, AC-PACK-6). |
| `pack --json` report and `extract.no-match` | Defined in FORMAT_SPEC Appendix B and §12.8 (SEL-1). Selective-extract criteria are Extended:#6. |
| Helper scripts | `trace.py`, `inspect_check.py`, `tree_eq.py` (including `--nfc`), `flip_sweep.py`, `truncate_sweep.py` and `spec_hexdump.py` are early implementation tasks after `plan-v1`. They're reviewed together with `check.sh` at the `checks-v1` checkpoint, before any Rust format code (DESIGN.md §10). |
| AC-ROB-6 memory check | Linux only, because it uses GNU `/usr/bin/time`. macOS and Windows memory bounds rest on AC-LIM-1's counting allocator. |

## 7. Open items for review

1. **Runner feasibility (§1.2)** is unconfirmed until the first full CI run. That applies
   especially to AC-ROB-7 on `macos-latest` (14 GB disk) and AC-ROB-4 on `windows-latest`
   (MSVC ASan). If either fails, it reports FAIL, and the proposed relocations need owner
   approval.
