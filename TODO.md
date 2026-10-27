# Chst — TODO

> Status: Active from plan-v1. Precedence and protection are defined only in CLAUDE.md; this file ranks below FORMAT_SPEC.md, ACCEPTANCE.md and DESIGN.md, and never overrides them.

## How this file works

- Work one task at a time, in order, respecting **Depends**. A task may start only when
  every task it depends on is checked.
- **Checks** lists the acceptance IDs (ACCEPTANCE.md §3) that must report PASS on Linux,
  via `./check.sh --only <IDs>`, before the task is committed. An ID is listed under the
  task that completes it. Earlier tasks may make it pass partly, but a FAIL there doesn't
  block them.
- macOS and Windows statuses come only from CI (ACCEPTANCE.md §2.1). Where a task's IDs
  apply only to macOS or Windows, it's committed when the code builds and lints on Linux.
  Its IDs are then confirmed in the next CI run, and stay unchecked here until that run
  passes them.
- The commit message starts with the task ID. After each task: append to PROGRESS.md, and
  update EVIDENCE.md from `target/acceptance/report.json`.
- **Sub-tasks** are requirements on how a test is written. They interpret ACCEPTANCE.md
  and never relax it. Every sub-task must hold before its parent is checked.
- Anything that needs a decision goes under "Needs decision" in PROGRESS.md (`CLAUDE.md`),
  not here.
- **Sub-steps** (C-6a, C-6b, …) are tasks in their own right: one commit each, in order,
  each with its own Verify line. Each acceptance ID is owned by exactly one task or sub-step.

### Verify lines

Every task has a **Verify** line: the exact command that proves the task is done. Run it
before committing, and record its result in PROGRESS.md.
- It runs under `bash -euo pipefail` from the repository root, after
  `source tools/acceptance/lib.sh` (H-2), in a fresh `W=$(mktemp -d)` that is removed
  afterwards.
- A Verify command must be able to fail. A command that only prints, or that can pass
  with nothing checked, doesn't count. Fixture-driven tests assert exact counts, so an empty
  directory or a skipped file fails them.
- `pass_only ID,…` (an H-2 helper): runs `./check.sh --only ID,…`, then fails unless
  `report.json` has exactly one result for each named ID and every one is `PASS`.
- `ci_pass OS ID,…` (an H-2 helper): reads the newest CI run of `check.yml` with `gh`
  (read-only), downloads `acceptance-report-<OS>`, and fails unless every named ID is
  `PASS` in it. It's used for IDs that only macOS or Windows can run.
- **Task-evidence tests.** Tasks C-2 … C-5 and C-9 have no acceptance ID of their own, so they're
  proved by tests in `crates/chst-cli/tests/`: `task_reader.rs` and `task_writer.rs`.
  - These tests are **development evidence, not conformance evidence.** Conformance is
    decided only by the CLI fixture comparisons in ACCEPTANCE.md (`CLAUDE.md`).
  - They live in `chst-cli` because that's the crate D15 approves `serde_json` for, and
    they need it to read `expect.json`.
  - They start with `#![forbid(unsafe_code)]` (D18), and stay passing in Phase X, because
    AC-ENG-4 runs the whole workspace. Under the Extended features, a compat fixture is
    compared with its `extended` result.
  - The fixture set is fixed (`fixtures/` is protected from `plan-v1`), so the counts
    below are exact.

**The reader fixture set for `task_reader.rs`.** It's every `*.expect.json` in
`fixtures/core/invalid/`, `core/hostile/`, `core/hostile64/`, `core/attacks/`,
`core/extract-cases/` and `compat/` (128 files), plus the 10 `core/valid/*/container.chst`.
- Each file is assigned the §13 step of its first violation:
  - from its `rule`;
  - for `compat/`, from its `detail` (`hdr.*` → step 8, `sec.unknown-critical` → step 9);
  - `exit` 0 → no violation.
- The limits come from each file's `args`.
- `core/invalid/LIM-2` is a sparse recipe. The test reads it from `$CHST_LIM2`, which the
  Verify line sets with `fixture_file`. The test fails if that variable is unset.
- The test fails on any file it can't classify.

| Step reached | Fixtures whose first violation is there | Count | Running total |
|---|---|---|---|
| 1–8 | HDR-1 … HDR-6, TRL-1, TRL-2, TRL-2-low, TRL-2-overflow, TRL-3, LIM-2, LIM-4; hostile `index-length-huge`; hostile64 `trailer-index-offset`; compat `hash-alg-2`, `major-2`, `unknown-required-bit63`, `zstd-required-flag` | 19 | 19 |
| 9 | SEC-1, SEC-1-straddle, SEC-2, SEC-3, SEC-3-repeat, SEC-4, SEC-5, SEC-5-entry, LIM-3; hostile `entries-2e32`, `record-count-2e60`; hostile64 `blob-table-count`; compat `unknown-critical-section` | 13 | 32 |
| 10 | every other `core/invalid` fixture except BLB-6 (48, LIM-5 included); all 23 `core/attacks`; hostile `path-length-max`; hostile64 `blob0-offset`, `blob0-raw`, `blob0-stored-and-raw`, `entry1-path-offset` | 76 | 108 |
| 11 | `core/invalid/BLB-6`, `core/extract-cases/late-blob-hash` | 2 | 110 |
| none | extract-cases `short-name`, `unicode-case`; the 6 exit-0 compat fixtures; the 10 `core/valid` | 18 | 128 |

`reader_step_N` (N = 8, 9, 10, 11) runs the reader through step N on all 128 files. It
asserts:
- every file whose step is ≤ N is rejected with exactly its `expect.json` `detail`;
- every other file passes steps 1 … N;
- the number rejected is exactly the running total for N.

Gates, from DESIGN.md §10:

| Gate | Who | Unlocks |
|---|---|---|
| `plan-v1` tag | Owner | Phase H (harness) and CI |
| `checks-v1` approval | Owner | Phase C (Core) |
| `CURRENT_CUT = Extended` | Owner | Phase X (Extended) |

---

## Phase H: acceptance harness (DESIGN §10 checkpoint 5)

These tasks are done when every ID is reported honestly, not when everything passes. Most
IDs will FAIL here, because the features don't exist yet.

- [x] **H-1 `check.sh` runner core**
  - Depends: `plan-v1`.
  - Builds:
    - the modes in ACCEPTANCE §1: fast, `--full`, `--only`, `--list-ids`;
    - the statuses and exit codes of §1.1;
    - `report.json` (schema `chst-acceptance/1`) and per-ID logs;
    - a fresh `$W` for every ID, removed afterwards;
    - `bash -euo pipefail`;
    - OS detection (`$CHST_OS`).
  - N/A comes only from the two facts in §1.1: `CURRENT_CUT`, read from ACCEPTANCE §2, and
    each ID's **OS** line. A missing check, a check that can't run, and a build failure all
    give FAIL.
  - It rejects any check script with a line starting `! ` (§1.2).
  - Check scripts live at `tools/acceptance/checks/<ID>.sh`.
  - Checks: none on its own; H-3 and H-4 cover it.
  - Verify (at the H-1 commit on Linux, when no check script exists yet):
    `set +e; ./check.sh > /dev/null; rc=$?; set -e; test $rc = 1;
    jq -e '.schema == "chst-acceptance/1" and .mode == "fast" and .os == "linux" and .cut == "core" and (.results | length) == 85 and ([.results[] | select(.status == "FAIL")] | length) == 63 and ([.results[] | select(.status == "N/A")] | length) == 19 and ([.results[] | select(.status == "NOT RUN")] | length) == 3' target/acceptance/report.json;
    diff <(./check.sh --list-ids) <(grep -oE '^#### AC-[A-Z0-9-]+' ACCEPTANCE.md | cut -c6-)`.
    The 63 FAIL are the missing checks. The 19 N/A are the 13 Extended IDs and 6 IDs
    excluded on Linux. The 3 NOT RUN are the two full-only IDs and the done-only ID.
- [x] **H-2 Shared shell helpers**
  - Depends: H-1.
  - `tools/acceptance/`: `expect_exit`, `jqn`, `cargo_test_nonempty`, `sha256`,
    `mk_sparse`, `free_bytes`, `fixture_file`, and the `$CHST`, `$CHST_CORE`, `$FX`, `$GEN`,
    `$CHST_BIG_ROOT` and `$CHST_DET_SEED` conventions (§1.2).
  - `cargo_test_nonempty` sums the `N passed` counts and fails on 0, on no `test result:`
    line, or on a cargo failure.
  - Also the two development helpers `pass_only` and `ci_pass` (see "Verify lines"). No
    acceptance check uses them.
  - Checks: none on its own; H-3 covers it.
  - Verify:
    `expect_exit 3 bash -c 'exit 3'; if expect_exit 0 bash -c 'exit 3'; then exit 1; fi;
    test "$(sha256 fixtures/core/valid/worked-example/container.chst)" = "$(awk '$2 == "core/valid/worked-example/container.chst" {print $1}' fixtures/MANIFEST.sha256)";
    test "$(fixture_file fixtures/core/invalid/HDR-2.expect.json)" = fixtures/core/invalid/HDR-2.chst;
    f=$(fixture_file fixtures/core/invalid/LIM-2.expect.json); test "$(wc -c < "$f" | tr -d ' ')" = 4294967385; test "$(head -c 4 "$f")" = CHST;
    mk_sparse "$W/s" 1048576; test "$(wc -c < "$W/s" | tr -d ' ')" = 1048576`.
- [ ] **H-3 `--self-test`**
  - Depends: H-2.
  - Builds a throwaway crate in a fresh temporary directory and runs the five `SELFTEST-*`
    IDs through the same code path as real IDs. They never appear in `--list-ids` or in
    normal reports.
  - Checks: AC-META-7.
  - Verify: `pass_only AC-META-7; if ./check.sh --list-ids | grep -q SELFTEST; then exit 1; fi`.
- [ ] **H-4 One check script per acceptance ID**
  - Depends: H-2.
  - Each script is the ACCEPTANCE §3 script exactly as written. A script that is missing
    makes its ID FAIL.
  - **TODO coverage preflight.** In fast mode (plain `./check.sh`) and in full mode,
    `check.sh` runs `python3.14 -I tools/todo_coverage.py` before any ID. The script
    exists already and is kept in the repo.
    - Its output goes to `target/acceptance/logs/todo-coverage.log`.
    - If it exits non-zero, `check.sh` exits 1.
    - It's a harness preflight, not an acceptance ID, so it never appears in `--list-ids`
      or in `results`. AC-META-1 requires `--list-ids` to match ACCEPTANCE.md exactly.
    - It fails when an ID is unowned, owned twice, or unknown; when a Re-check bullet lists
      an ID that the same task has under Checks; when a task mentions an ID on neither
      bullet; and on ranges.
  - Checks: AC-META-1, AC-META-2, AC-META-4, AC-META-5. The last three test only the
    fixtures, which already exist, so they should pass as soon as their scripts do.
  - Verify:
    `pass_only AC-META-1,AC-META-2,AC-META-4,AC-META-5; test -s target/acceptance/logs/todo-coverage.log;
    python3.14 -I tools/todo_coverage.py;
    sed '/^  - Checks: AC-META-1, AC-META-2, AC-META-4, AC-META-5\. /d' TODO.md > "$W/T.md"; if cmp -s TODO.md "$W/T.md" || python3.14 -I tools/todo_coverage.py --todo "$W/T.md"; then exit 1; fi;
    test "$(ls tools/acceptance/checks/*.sh | wc -l | tr -d ' ')" = 85`.
- [ ] **H-5 Python helper scripts** (standard library only, run as `python3.14 -I`)
  - Depends: H-4.
  - [ ] `trace.py` (AC-META-3)
  - [ ] `spec_hexdump.py` (AC-META-6)
  - [ ] `inspect_check.py` (for AC-POS-3)
  - [ ] `tree_eq.py` (for AC-POS-4)
  - [ ] `flip_sweep.py` (for AC-ROB-1)
  - [ ] `truncate_sweep.py` (for AC-ROB-2)
  - Each one's pass and fail behaviour is exactly as its criterion describes. A helper that
    can't find its target reports FAIL.
  - Checks: AC-META-3, AC-META-6.
  - Re-check: AC-POS-3 (owned by C-6c), AC-ROB-1, AC-ROB-2 (owned by C-6a), and AC-POS-4
    (owned by C-14b). Each must report FAIL here, because the CLI doesn't exist yet.
  - Verify:
    `pass_only AC-META-3,AC-META-6;
    $GEN materialize fixtures/core/valid/worked-example/tree.json "$W/a"; cp -R "$W/a" "$W/b";
    python3.14 -I tools/acceptance/tree_eq.py "$W/a" "$W/b";
    echo x >> "$W/b/notes.txt"; if python3.14 -I tools/acceptance/tree_eq.py "$W/a" "$W/b"; then exit 1; fi;
    if python3.14 -I tools/acceptance/flip_sweep.py "$W/no-such-chst" fixtures/core/valid/empty/container.chst; then exit 1; fi;
    if python3.14 -I tools/acceptance/truncate_sweep.py "$W/no-such-chst" fixtures/core/valid/worked-example/container.chst; then exit 1; fi`.
- [ ] **H-6 `--done` mode**
  - Depends: H-4.
  - Downloads the three `acceptance-report-<os>` reports with `gh` (read-only), imports each
    ID's per-OS status, then runs the done-only check. It exits 0 only if that check
    passes (§2).
  - Checks: none.
  - Re-check: AC-XP-1 (owned by C-20, the only place it can pass).
  - Verify (no such CI run exists):
    `set +e; ./check.sh --done 1 > /dev/null; rc=$?; set -e; test $rc = 1;
    jq -e '.mode == "done" and ([.results[] | select(.id == "AC-XP-1" and .status == "FAIL")] | length) == 1' target/acceptance/report.json`.
- [ ] **H-7 First honest local run**
  - Depends: H-1 … H-6.
  - Run `./check.sh` on Linux (WSL), from the Linux filesystem.
  - Fill every EVIDENCE.md Linux cell from `report.json`, with `local` in the CI column.
  - Record in PROGRESS.md which IDs pass.
  - Re-check: AC-META-1, AC-META-2, AC-META-3, AC-META-4, AC-META-5, AC-META-6, AC-META-7
    (owned by H-3, H-4 and H-5) should pass; most others FAIL.
  - Verify:
    `set +e; ./check.sh > /dev/null; rc=$?; set -e; test $rc = 1; r=target/acceptance/report.json;
    jq -e '[.results[] | select(.id | startswith("AC-META-"))] | length == 7 and all(.status == "PASS")' $r;
    jq -r '.results[] | "\(.id)\t\(.status)"' $r | while IFS=$'\t' read -r id st; do
      test "$(grep -E "^\| $id \|" EVIDENCE.md | awk -F'|' '{gsub(/^ +| +$/, "", $3); print $3}')" = "$st"; done`.
    EVIDENCE.md's Linux column must match the report, row by row.
- [ ] **CI-1 CI workflow** (`.github/workflows/check.yml`, D17)
  - Depends: H-7.
  - Triggers: `push`, `pull_request` and `workflow_dispatch`.
  - Runners: `ubuntu-latest`, `macos-latest` and `windows-latest`, all with `shell: bash`.
  - Fast mode (`run: ./check.sh`) on push and PR; `./check.sh --full` on manual trigger.
  - Job result:
    - fast mode: 0 or 2 succeeds;
    - full mode: 2 succeeds only when the done-only check is the sole NOT RUN;
    - 1 always fails.
  - Every runner gets:
    - a `python3.14` command (on Windows, a shim to the interpreter `setup-python` installs);
    - `jq` 1.7 or later;
    - the pinned toolchains (D16), plus the nightly and `cargo-fuzz` 0.13.2 `--locked` for
      full mode;
    - `$CHST_BIG_ROOT`.
  - On Ubuntu, free disk space first (§1.3).
  - Upload each report as `acceptance-report-<os>`.
  - In full mode on Windows, try cargo-fuzz once, as a non-gating, logged step (§1.3).
  - Checks: AC-XP-2.
  - Verify: `pass_only AC-XP-2`. After the owner pushes, also check the newest run:
    `gh run download "$(gh run list --workflow check.yml --limit 1 --json databaseId -q '.[0].databaseId')" --pattern 'acceptance-report-*' --dir "$W/r";
    test "$(jq -r .os "$W"/r/*/report.json | sort | tr '\n' ' ')" = 'linux macos windows ';
    for r in "$W"/r/*/report.json; do jq -e '(.results | length) == 85' "$r"; done`.
    That run is red at this stage, because most IDs FAIL. The check is that all three
    reports exist and are complete.
  - The owner pushes. Claude reads the first run with `gh`, read-only, and records in
    PROGRESS.md what it showed for the open items in DESIGN §9g–§9i: runner feasibility,
    nightly components, and the Windows `FILE_SHARE_DELETE` behaviour (P4, once C-17 exists).

**STOP. `checks-v1`:** the owner reviews `check.sh`, the helper scripts and the workflow.
Nothing below starts before that approval.

---

## Phase C: Core implementation (DESIGN §10 checkpoint 7)

### Workspace and format crate

- [ ] **C-1 Workspace skeleton**
  - Depends: `checks-v1`.
  - `rust-toolchain.toml` (D16), the workspace, and `crates/chst-format`, `crates/chst-fs`
    and `crates/chst-cli` (binary `chst`).
  - `rust-version = "1.99"`, edition 2024, and a committed `Cargo.lock`.
  - Only D15 dependencies.
  - Lint headers per D18:
    - `forbid(unsafe_code)` everywhere;
    - in `chst-fs`: `deny`, plus the single `#[cfg(windows)] #[allow(unsafe_code)] mod
      windows;` and the SAFETY lints.
  - `chst-fs` has the non-default `test-hooks` feature (D13).
  - Extended Cargo features are added in Phase X. Until then, `$CHST` and `$CHST_CORE`
    build the same thing.
  - Checks: AC-ENG-1, AC-ENG-5, AC-ENG-6.
  - Re-check: AC-ENG-7 (owned by C-8). It can't pass yet, because the files it inspects
    don't exist until C-7 and C-8.
  - Verify: `pass_only AC-ENG-1,AC-ENG-5,AC-ENG-6; cargo build --release --locked; test -x target/release/chst`.
- [ ] **C-2 Header, trailer and structure hash** (§13 steps 1–8)
  - Depends: C-1.
  - Covers:
    - integer decoding (D3);
    - HDR-1 … HDR-6 and TRL-1 … TRL-3;
    - LIM-2 and LIM-4 before the index is read;
    - the error type with §16 categories and detail codes;
    - the configurable limits of §10.2 with their defaults.
  - All arithmetic is checked, and nothing is allocated before its size is validated (§10.3).
  - Adds `crates/chst-cli/tests/task_reader.rs` with `reader_step_8` (see "Verify lines").
  - Checks: AC-ENG-2, AC-ENG-4.
  - Verify:
    `pass_only AC-ENG-2,AC-ENG-4;
    CHST_LIM2=$(fixture_file fixtures/core/invalid/LIM-2.expect.json) cargo_test_nonempty --release -p chst-cli --test task_reader -- reader_step_8`.
    That's 19 rejections, each with its exact detail, and 109 files passing steps 1–8.
- [ ] **C-3 Sections** (§13 step 9)
  - Depends: C-2.
  - SEC-1 … SEC-5, then LIM-3 before any per-entry allocation. Stop at HDR-6 and SEC-2
    (unsupported, never malformed).
  - Adds `reader_step_9`.
  - Verify:
    `CHST_LIM2=$(fixture_file fixtures/core/invalid/LIM-2.expect.json) cargo_test_nonempty --release -p chst-cli --test task_reader -- reader_step_`.
    That runs `reader_step_8` and `reader_step_9`: 32 rejections in total, and 96 files
    passing steps 1–9.
- [ ] **C-4 Blobs, entries, paths and canonical form** (§13 step 10, the Core rules)
  - Depends: C-3.
  - Step 10 (a) … (p), in that exact order. FLG-1, ATT-1 and KV-1 apply only where the
    reader knows the flag, which a Core reader doesn't.
  - The PATH-2 NFC check uses `unicode-normalization` with Unicode 16.0 tables.
  - Adds `reader_step_10`. LIM-5 is evaluated in verify mode, with `args` from its
    `expect.json`.
  - Checks: AC-ENG-8.
  - Verify:
    `pass_only AC-ENG-8;
    CHST_LIM2=$(fixture_file fixtures/core/invalid/LIM-2.expect.json) cargo_test_nonempty --release -p chst-cli --test task_reader -- reader_step_`.
    That's 108 rejections, including all 23 `core/attacks`, and the 20 step-11 or
    passing files pass steps 1–10.
- [ ] **C-5 Step 11 and structured reports**
  - Depends: C-4.
  - Streaming BLB-6 per blob in table order, with bounded memory (G6).
  - List and inspect stop after step 10 (F34).
  - List, inspect and verify reports as library values (Appendix B, `chst-report/1`),
    including "what the reader implements shapes its report".
  - Adds `reader_step_11` and `reports` to `task_reader.rs`. `reports` asserts:
    - For the 10 `core/valid` fixtures and the 6 exit-0 `compat` fixtures (16 in total):
      - each list report's entries equal the `entries` of its `list.json`, in order: `path`,
        `type`, `size`, `stored_size`, `encoding`, `blob`;
      - each verify report's `summary` equals its `verify.json` `summary`.
    - List and inspect succeed on `core/invalid/BLB-6.chst`, and verify rejects it with
      `blob.hash` (F34).
  - Verify:
    `CHST_LIM2=$(fixture_file fixtures/core/invalid/LIM-2.expect.json) cargo_test_nonempty --release -p chst-cli --test task_reader -- reader_step_ reports`.
    That's 110 rejections, the 18 passing files pass all 11 steps, and 16 report matches.

### CLI, read side

The CLI holds no format or safety logic (D13). Its output, text and `--json`, goes through
`serde_json::Value`.

- [ ] **C-6a CLI: argument parsing and `verify`**
  - Depends: C-5.
  - `lexopt` parsing per Appendix C:
    - limit flags take ASCII digits only, with no sign, no whitespace, and no leading zeros
      (M12);
    - usage errors exit 2.
  - The category → exit code mapping (§16). `verify` in text and `--json`.
  - Checks:
    - AC-ENG-3;
    - AC-NEG-1, AC-NEG-2, AC-NEG-4;
    - AC-CLI-1;
    - AC-LIM-3;
    - AC-ROB-1, AC-ROB-2, AC-ROB-8.
  - Verify: `pass_only AC-ENG-3,AC-NEG-1,AC-NEG-2,AC-NEG-4,AC-CLI-1,AC-LIM-3,AC-ROB-1,AC-ROB-2,AC-ROB-8`.
- [ ] **C-6b CLI: `list`**
  - Depends: C-6a.
  - `list` in text and `--json`. The text output escapes non-printing characters (PATH-6).
    List never runs step 11 (F34).
  - Checks: AC-CLI-3.
  - Verify:
    `pass_only AC-CLI-3;
    for d in fixtures/core/valid/*/; do expect_exit 0 $CHST list --json "$d/container.chst" > "$W/r.json"; diff <(jqn "$W/r.json") <(jqn "$d/list.json"); done;
    expect_exit 0 $CHST list --json fixtures/core/invalid/BLB-6.chst > /dev/null;
    test "$(ls -d fixtures/core/valid/*/ | wc -l | tr -d ' ')" = 10`.
- [ ] **C-6c CLI: `inspect`, and the cross-command checks**
  - Depends: C-6b.
  - `inspect` in text and `--json`, with byte offsets. Inspect never runs step 11 (F34).
  - Checks:
    - AC-POS-2, AC-POS-3;
    - AC-NEG-3;
    - AC-COMPAT-1;
    - AC-ROB-9.
  - Verify: `pass_only AC-POS-2,AC-POS-3,AC-NEG-3,AC-COMPAT-1,AC-ROB-9`.
- [ ] **C-7 Library robustness tests**
  - Depends: C-5.
  - `damage_sweep` (AC-ROB-3).
  - `hostile_sizes` with `tests/support/counting_alloc.rs` (D18 exception 1; the only
    `unsafe` outside `chst-fs::windows`, with SAFETY comments) (AC-LIM-1).
  - Checks: AC-ROB-3, AC-LIM-1.
  - Re-check: AC-ENG-7 (owned by C-8).
  - Verify: `pass_only AC-ROB-3,AC-LIM-1`.
- [ ] **C-8 Fuzzing, and the unsafe-code audit**
  - Depends: C-7.
  - `fuzz/` with its own `rust-toolchain.toml` (the nightly pin) and `Cargo.lock`, and
    targets over `chst-format`.
  - `fuzz_regressions` test over `fixtures/fuzz-regressions/` (AC-ROB-5).
  - `random_sweep` for the Windows fallback.
  - If `fuzz_target!` trips `forbid(unsafe_code)`, commit the compiler error as
    `fuzz/FORBID_EXEMPTION.txt` (D18 exception 2). Never write `unsafe` by hand.
  - Any crash is minimised into `fixtures/fuzz-regressions/`. Changing `fixtures/` after
    `plan-v1` needs the owner's approval, so a crash is logged under "Needs decision" first.
  - Checks: AC-ROB-5, AC-ENG-7.
  - Re-check: AC-ROB-4 and AC-ROB-4W (owned by C-20). They're full-only, so a short local
    run here is only a smoke test.
  - AC-ENG-7 checks only the counting-allocator users that exist, so `zstd_bombs.rs` (X-1)
    isn't needed under the Core cut (DESIGN §9i, post-review edit).
  - Verify: `pass_only AC-ROB-5,AC-ENG-7; (cd fuzz && cargo fuzz list | grep -q .)`.

### Writer and pack

- [ ] **C-9 Canonical writer** (`chst-format`)
  - Depends: C-5.
  - Covers:
    - §14 writer requirements: bytewise-sorted entries, dedup, and blobs in
      first-reference order (D2, D9);
    - `minor_version` 0;
    - the structure hash;
    - W-10: refuse to write anything its own verify would reject, with the limits checked
      in W-10's order.
  - Works over any byte sink.
  - Adds `crates/chst-cli/tests/task_writer.rs`, with two tests:
    - `writer_golden`: for each of the 10 `fixtures/core/valid/*/tree.json`, feeds its
      entries (`path`, `type`, decoded `content_b64`) to the writer in memory. The output
      must equal that directory's `container.chst` byte for byte. Exactly 10 comparisons.
    - `writer_limits`: on `core/valid/worked-example/tree.json`, these three are refused
      with nothing written to the sink:
      - `max_entries` 4 → `limit.entries`;
      - `max_index_bytes` 458 → `limit.index-size`;
      - `max_total_bytes` 14 → `limit.total-size`.

      With 5, 459 and 15, the output equals `container.chst`. (These are the boundaries
      the verify side uses.)
  - Verify: `cargo_test_nonempty --release -p chst-cli --test task_writer -- writer_`.
- [ ] **C-10 Pack (Unix)**
  - Depends: C-9, C-6c.
  - The walk never follows a link, and skips symlinks and special files with warnings (W-5).
  - Converts names to NFC and checks them, refusing the whole pack on any violation (W-3).
  - Hashes twice (W-4).
  - Writes to a temporary file next to the output, then renames it (G5, W-2, W-7).
  - `--force` (D14). An output inside the source tree is refused (W-6).
  - CLI `pack`.
  - Checks:
    - AC-POS-1;
    - AC-DET-1, AC-DET-2;
    - AC-PACK-1, AC-PACK-2, AC-PACK-4, AC-PACK-5, AC-PACK-6, AC-PACK-9, AC-PACK-11;
    - AC-CLI-2.
  - Verify: `pass_only AC-POS-1,AC-DET-1,AC-DET-2,AC-PACK-1,AC-PACK-2,AC-PACK-4,AC-PACK-5,AC-PACK-6,AC-PACK-9,AC-PACK-11,AC-CLI-2`.
- [ ] **C-11 Pack race and classification tests**
  - Depends: C-10.
  - `source_changed` (AC-PACK-3).
  - `walk_race`, under `test-hooks` (AC-PACK-10).
  - `skip_classification` (AC-PACK-12).
  - Checks: AC-PACK-3, AC-PACK-10, AC-PACK-12.
  - Verify: `pass_only AC-PACK-3,AC-PACK-10,AC-PACK-12`.
- [ ] **C-12 Pack (Windows)**
  - Depends: C-10.
  - In the `windows` module: skip junctions and other reparse points
    (`FILE_FLAG_OPEN_REPARSE_POINT`), never pack alternate data streams, and use
    extended-length paths (W-8).
  - Checks (CI): AC-PACK-7, AC-PACK-8.
  - Verify: `cargo clippy --release --locked --workspace -- -D warnings` on Linux at commit
    time, then `ci_pass windows AC-PACK-7,AC-PACK-8` on the next run.

### Extract

- [ ] **C-13 Staging (EXT-4) and the create layer**
  - Depends: C-6c.
  - **Unix holding steps**, in order:
    1. `mkdirat(0700)`;
    2. `openat(O_DIRECTORY|O_NOFOLLOW)`;
    3. `fstat`: owner = euid, `st_mode & 0o077 == 0`, empty;
    4. `fchmod(handle, 0700)`;
    5. confirm `st_mode & 0o777 == 0700`.
  - **Windows:** `NtCreateFile` with `FILE_CREATE`, without `FILE_SHARE_DELETE`, and with
    `DELETE` access.
  - The handle's identity is recorded. Every later operation goes through handles; nothing
    is reopened by name.
  - The create layer (EXT-2, EXT-6, EXT-8) refuses hostile names on its own.
  - Every directory the extractor creates has any inherited setgid bit cleared (EXT-5).
  - Checks: AC-SAFE-12.
  - Verify: `pass_only AC-SAFE-12`.
- [ ] **C-14a Extract: validate before writing**
  - Depends: C-13.
  - CLI `extract`.
  - The destination must not exist (EXT-1); a dangling symlink counts as existing.
  - Full structural validation (steps 1–10) and LIM-5 before anything is created. On
    failure, neither the destination nor a staging directory exists.
  - Checks: AC-SAFE-1, AC-SAFE-2.
  - Verify:
    `pass_only AC-SAFE-1,AC-SAFE-2;
    expect_exit 8 $CHST extract --max-total-bytes 14 fixtures/core/valid/worked-example/container.chst -C "$W/a"; test -z "$(ls -A "$W")";
    expect_exit 6 $CHST extract fixtures/core/invalid/PATH-5.chst -C "$W/b"; test -z "$(ls -A "$W")"`.
- [ ] **C-14b Extract: write and rename**
  - Depends: C-14a, C-10.
  - Writes into the held staging directory, with step 11 run while each file is written,
    reporting exactly as verify does (EXT-7, M2).
  - Identity checks immediately before and after the final rename.
  - Final permissions (`0755 & ~umask`) only after both pass.
  - Checks:
    - AC-POS-4;
    - AC-SAFE-4, AC-SAFE-6, AC-SAFE-7;
    - AC-LIM-2, AC-LIM-4;
    - AC-DET-3 (`roundtrip_prop`, seeded generator);
    - AC-ROB-6.
  - Verify: `pass_only AC-POS-4,AC-SAFE-4,AC-SAFE-6,AC-SAFE-7,AC-LIM-2,AC-LIM-4,AC-DET-3,AC-ROB-6`.
- [ ] **C-14c Extract: cleanup**
  - Depends: C-14b.
  - **Cleanup:**
    - removes only recorded identities;
    - the M9 name check, which applies to the destination after the rename (Q4);
    - restrictive modes are handled with `fchmodat`, relative to the parent's handle.
  - If the final permissions fail: `io`, with cleanup through the same handle.
  - Verify (a late step-11 failure leaves nothing behind):
    `expect_exit 7 $CHST extract fixtures/core/extract-cases/late-blob-hash.chst -C "$W/x" 2> "$W/err"; grep -q 'error\[integrity/blob.hash\]' "$W/err"; rm "$W/err"; test -z "$(ls -A "$W")";
    expect_exit 7 $CHST extract fixtures/core/invalid/BLB-6.chst -C "$W/y"; test -z "$(ls -A "$W")"`.
- [ ] **C-15 Extract (Windows and macOS specifics)**
  - Depends: C-14c.
  - Windows:
    - long paths;
    - no alternate data streams created (EXT-9);
    - 8.3 short-name aliasing caught (EXT-2).
  - macOS: decomposed names round-trip as NFC (W-9).
  - Case collisions are caught by the filesystem (EXT-2).
  - Checks (CI): AC-SAFE-5, AC-SAFE-9, AC-SAFE-10, AC-SAFE-11.
  - Verify: `cargo clippy --release --locked --workspace -- -D warnings` on Linux at commit
    time, then `ci_pass macos AC-SAFE-5,AC-SAFE-11` and
    `ci_pass windows AC-SAFE-5,AC-SAFE-9,AC-SAFE-10` on the next run.

### Extract race tests (`test-hooks`)

Each hook is compiled only with `test-hooks`. Each test asserts what its criterion says, in
its own `$W`.

- [ ] **C-16 `swap_race`** (AC-SAFE-8)
  - Depends: C-14c.
  - [ ] **R4 (review-6):** the hook **deletes** the empty directory created by `mkdirat`
    (`rmdir`), then plants the symlink (a junction on Windows). It never moves the
    directory aside. That way the extractor never leaves behind an object it created but
    couldn't record (its `openat` failed), and "every object the extractor created *inside*
    staging is gone, except the directories on the path to the planted link" holds as
    written.
  - Checks: AC-SAFE-8.
  - Verify: `pass_only AC-SAFE-8`. Then `ci_pass macos AC-SAFE-8` and `ci_pass windows AC-SAFE-8`.
- [ ] **C-17 Staging tests:** `staging_props`, `staging_swap`, `staging_open_race`,
  `staging_rename_race` (AC-SAFE-14)
  - Depends: C-14c.
  - `staging_props`'s first hook fires after the holding steps (Q7).
  - The Windows branches expect the swap to be refused, then the extractor's own rename
    through its handle to succeed (P4).
  - Checks: AC-SAFE-14.
  - Verify: `pass_only AC-SAFE-14`. Then `ci_pass macos AC-SAFE-14` and `ci_pass windows AC-SAFE-14`.
- [ ] **C-18 `dest_race`** (AC-SAFE-13)
  - Depends: C-14c.
  - Checks: AC-SAFE-13.
  - Verify: `pass_only AC-SAFE-13`.
- [ ] **C-19 `cleanup_race`** (AC-SAFE-15)
  - Depends: C-14c.
  - `late_failure` (AC-SAFE-3) shares the BLB-6 `late-blob-hash` failure.
  - [ ] **R4 (review-6):** the hook replaces an **empty** directory inside staging. It
    deletes that directory (`rmdir`), never moves it, then plants the symlink (a junction
    on Windows) to the sentinel directory. So no object the extractor created survives
    outside cleanup's reach, and the "every object the extractor created inside staging is
    gone, except…" assertion holds as written. The test tree includes such an empty
    directory, ordered so the hook can fire before cleanup.
  - Checks: AC-SAFE-15, AC-SAFE-3.
  - Verify: `pass_only AC-SAFE-15,AC-SAFE-3`. Then `ci_pass macos AC-SAFE-15,AC-SAFE-3` and `ci_pass windows AC-SAFE-15,AC-SAFE-3`.

### Done

- [ ] **C-20 Core done run**
  - Depends: every C task, and CI fast runs passing on all three OSes.
  - The owner triggers a full-mode CI run of one clean commit (`workflow_dispatch`).
    AC-ROB-4, AC-ROB-4W and AC-ROB-7 run there.
  - Update every EVIDENCE.md row from that run's reports, with the commit and the run link.
  - Then `./check.sh --done <ci-run-id>` must exit 0 (ACCEPTANCE §2).
  - Checks: AC-ROB-4, AC-ROB-4W, AC-ROB-7, AC-XP-1.
  - Verify: `./check.sh --done <ci-run-id>` exits 0, and then
    `jq -e '.mode == "done" and all(.results[]; .status == "PASS" or .status == "N/A")' target/acceptance/report.json`.

---

## Phase X: Extended (only after the owner sets `CURRENT_CUT = Extended`)

Until then, every ID below is N/A. Each feature is added behind a default-on Cargo feature,
so `$CHST_CORE` (`--no-default-features`) stays Core-only. Each task re-checks AC-COMPAT-1
(owned by C-6c).

- [ ] **X-1 Zstandard blobs (#12)**
  - Depends: C-20, the cut change.
  - `zstd` feature in `chst-format`: ZST-1 … ZST-3, and step 11's order:
    1. BLB-6;
    2. the frame header (ZST-2);
    3. Frame_Content_Size ≠ `raw_length` (ZST-1);
    4. one decoding pass capped at `raw_length` (ZST-2).
  - LIM-6 is computed exactly in at least 128 bits.
  - A blob is compressed only when that's smaller (ZST-3).
  - `crates/chst-format/tests/zstd_bombs.rs` with the counting allocator: `deny(unsafe_code)`,
    and no `unsafe` of its own. It holds the real counting-allocator bomb tests: they decode
    the Extended bomb fixtures through `chst-format` and assert the peak Rust heap. It never
    holds an empty or placeholder test. AC-X-ZSTD-2 fails without the file, and runs it
    with `cargo_test_nonempty`, so at least one test must run and pass.
  - Checks: AC-X-ZSTD-1, AC-X-ZSTD-2.
  - Verify: `pass_only AC-X-ZSTD-1,AC-X-ZSTD-2`.
  - Re-check: AC-ENG-7 (owned by C-8). Under the Extended cut it requires `zstd_bombs.rs`.
- [ ] **X-2 Entry attributes (#16)**
  - Depends: X-1.
  - `ENTRY_ATTRS`: 64-byte entry records (FLG-1 is one-way), ATT-1, mtime and mode, and
    never setuid.
  - Modes are applied as stored, after the children are written (F27).
  - `--deterministic` (AC-X-ATTR-2).
  - Cleanup restores owner permissions with `fchmodat` relative to the parent's handle:
    - with `AT_SYMLINK_NOFOLLOW` where it works;
    - otherwise an `fstatat` identity check first, then the fallback that follows links.
  - Checks: AC-X-ATTR-1, AC-X-ATTR-2.
  - Verify: `pass_only AC-X-ATTR-1,AC-X-ATTR-2`.
- [ ] **X-3 `cleanup_modes`** (AC-X-ATTR-3)
  - Depends: X-2.
  - [ ] **R3 (review-6):** the second hook point is "**immediately before cleanup changes
    `x`'s mode**", whether by `fchmodat` relative to the parent or by `fchmod` on a handle
    cleanup kept open. The hook's assertions apply only when it fires:
    - staging is still 0700 and owned by the extractor's user;
    - on macOS, the swap of `x`;
    - the mode and contents of the outside file.

    An extractor that keeps `x`'s handle open and uses `fchmod` on it must pass. On that
    path there's no by-name change and no identity check, so the Linux "between the
    identity check on `x` and the chmod" wording applies only to the by-name path. The
    test never requires the hook to have fired. Whether or not it fired, it still asserts
    `refused/extract.dest-exists`, that the planted directory is unchanged, the staging
    outcome, and that nothing outside staging changed.
  - [ ] **R4 (review-6):** in the macOS swap case, the hook **deletes** the empty original
    `x` (`rmdir`; `d` is mode 0o777), never moves it, then plants the symlink. So the Q2
    exception holds as written: the planted symlink, `d` and staging remain, and every
    other object the extractor created is gone.
  - Checks: AC-X-ATTR-3.
  - Verify: `pass_only AC-X-ATTR-3`. Then `ci_pass macos AC-X-ATTR-3`.
- [ ] **X-4 Key/value metadata (#18b)**
  - Depends: X-1.
  - The `KV_METADATA` section (skippable) and KV-1. It's written only when given.
  - Checks: AC-X-KV-1.
  - Verify: `pass_only AC-X-KV-1`.
- [ ] **X-5 Selective extract (#6)**
  - Depends: X-1.
  - Path and glob selection by the §12.8 rules, with binary search over sorted entries.
  - LIM-5 and step 11 apply only to the selected entries, so a damaged blob that isn't
    selected doesn't fail (N7).
  - Checks: AC-X-SEL-1.
  - Verify: `pass_only AC-X-SEL-1`.
- [ ] **X-6 Exclude patterns (#7)**
  - Depends: X-1.
  - The writer's input filter, using the §12.8 glob rules.
  - Checks: AC-X-EXCL-1.
  - Verify: `pass_only AC-X-EXCL-1`.
- [ ] **X-7 Extended negative fixtures complete**
  - Depends: X-1, X-2, X-4.
  - Checks: AC-X-NEG-1.
  - Verify: `pass_only AC-X-NEG-1`.
- [ ] **X-8 TypeScript reader**
  - Depends: X-7.
  - `ts-reader/`: read-only, with no runtime dependencies. It uses `node:crypto`,
    `String.prototype.normalize` and `node:zlib` zstd.
  - Node 24 LTS, and its ICU must be Unicode 16.0.
  - If `node:zlib` zstd is still experimental, or Node's ICU isn't 16.0, log it under
    "Needs decision" first (DESIGN §9g; the `fzstd` fallback needs its own decision).
  - Checks: AC-X-TS-1, AC-X-TS-2, AC-X-TS-3.
  - Verify: `pass_only AC-X-TS-1,AC-X-TS-2,AC-X-TS-3`.
- [ ] **X-9 Extended done run:** as C-20, with the Extended cut.
  - Depends: X-1 … X-8.
  - Verify: `grep -qx 'CURRENT_CUT = Extended' ACCEPTANCE.md; ./check.sh --done <ci-run-id>`,
    which must exit 0.

---

## Review-6 findings (`reviews/review-6.md`)

| ID | Disposition |
|---|---|
| R1 | Applied in 3ce9cae: the P5 note's `io` example no longer uses `quiet`; with `quiet`, extraction may complete with the mount's modes; a refusal comes from step 3, 4 or 5. |
| R2 | Applied in 3ce9cae: the DESIGN D10 amendment and the §9i known-limitation line say "(superseded by Q5: refused or io, non-normative)". |
| R3 | Sub-task of X-3. |
| R4 | Sub-tasks of C-16, C-19 and X-3. |
