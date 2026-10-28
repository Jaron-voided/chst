# Chst — Progress

Append-only log, one entry per task. Results are in EVIDENCE.md, not here.

## Needs decision

- **AC-X-TS-2 has no script in ACCEPTANCE.md** (§3.13). *Owner agreed to (b); tracked as TODO X-0. Open until ACCEPTANCE.md changes.* I derived `tools/acceptance/checks/AC-X-TS-2.sh` from its prose (see H-4).
  Options: (a) keep the derived script; (b) have ACCEPTANCE.md state the script. Recommendation: (b) before the cut becomes
  Extended, so the script is the document's, not mine. It's N/A under Core, so nothing is blocked.

- **Fuzz scope and DESIGN decision 18 (Windows).** The first full-mode run with the fuzz probe (run 40689182770, commit b94ca41) shows
  cargo-fuzz works on Linux and macOS and not on Windows. DESIGN D18's decision 18 already approves the Windows fallback (AC-ROB-4W)
  "provisionally, until the first full CI run", so this run settles it; no Core work is blocked either way.
  - **Evidence.** Windows: the nightly and cargo-fuzz 0.13.2 install, and `cargo fuzz init` and the build succeed. The fuzz binary then won't
    start: `Error: Fuzz target exited with exit code: 0xc0000135` (STATUS_DLL_NOT_FOUND). The log doesn't name the DLL. My reading is that
    the MSVC AddressSanitizer runtime isn't on `PATH`; that isn't confirmed. Linux and macOS: `fuzz probe ok` (1000 runs).
  - **Options.** (a) Confirm decision 18 as it stands: cargo-fuzz on Linux and macOS (AC-ROB-4), Windows on the `random_sweep` fallback
    (AC-ROB-4W). DESIGN's decision 18 changes from "provisional" to "confirmed", and nothing in ACCEPTANCE.md changes. (b) Scope fuzzing to
    Linux only, as the owner's condition said: AC-ROB-4's OS line (now `linux, macos`) would have to drop macOS, which is moving a check to
    another OS and so needs the owner's approval. The macOS probe passed, so the evidence doesn't call for it. (c) Try to fix Windows
    (for example by putting the ASan runtime directory on `PATH`); open-ended, and not needed for Core.
  - **Recommendation: (a).** I haven't edited DESIGN.md: the approved condition was "scope fuzzing to Linux", and (a) isn't that.

## Log

### H-1 `check.sh` runner core — 7987503
- Added `check.sh` (modes fast, `--full`, `--only`, `--list-ids`) and `.gitignore` (`target/`, so
  `report.json`'s `dirty` isn't set by build output).
- `--list-ids` reads the `#### AC-` headings of ACCEPTANCE.md, so it prints all 85 IDs even when no
  check script exists. An ID's tier, OS list and full-only/done-only kind are parsed from the line under
  its heading; CURRENT_CUT from §2.
- `$CHST` and `$CHST_CORE` are built lazily, only when a script uses them, and the scripts get copies in
  `target/acceptance/bin/`. AC-ENG-1 builds without default features into `target/release`, which would
  otherwise replace `$CHST` for the checks after it.
- Unknown `--only` IDs and bad usage exit 64; §1.1 doesn't define an exit code for that.
- Open issues: none. TODO.md's H-1 prose says "13 Extended and 6 excluded" N/A IDs; ACCEPTANCE.md has 12
  Extended IDs and 7 OS-excluded ones on Linux (AC-ROB-4W, AC-SAFE-5, -9, -10, -11, AC-PACK-7, -8). The total
  of 19 is right, so the Verify line passes.
- Acceptance IDs affected: none pass yet (no scripts).

### H-2 Shared shell helpers — 5f3a54e
- Added `tools/acceptance/lib.sh`: the §1.2 helpers and conventions, plus `pass_only` and `ci_pass`. It sets no
  shell options and avoids bash 4 features (macOS ships bash 3.2).
- `mk_sparse` falls back to `os.truncate` through `python3.14` where `truncate` is missing (stock macOS).
- `fixture_file` reads the size of a sparse recipe from its `file_length`.
- Open issues: `ci_pass` and the Windows branch of `mk_sparse` (`fsutil`) can't be tried locally.
- Acceptance IDs affected: none directly.

### H-3 `--self-test` — 25d4a29
- `check.sh --self-test` builds a throwaway crate under `mktemp -d` and runs the five `SELFTEST-*` IDs through
  `run_check`. The self-test exits 0 only if every ID reports its required status. The report keeps the actual
  statuses (4 FAIL, 1 PASS). The IDs never reach `--list-ids` or a normal report.
- Added `tools/acceptance/checks/AC-META-7.sh`, copied verbatim from ACCEPTANCE.md. The other 84 scripts come in H-4.
- Each failing self-test ID was confirmed to fail for its own reason (0 tests passed, no script, command not found).
- Open issues: none.
- Acceptance IDs affected: AC-META-7.

### H-4 One check script per acceptance ID — 13d75cf
- Added the 84 remaining scripts in `tools/acceptance/checks/` (85 in all, one per ID, no extras), generated verbatim from the
  `sh` blocks under each `#### AC-` heading of ACCEPTANCE.md. AC-ROB-1 has two blocks, which are joined in order. No script has a
  line starting with `! `.
- **AC-X-TS-2 is a derived script.** ACCEPTANCE.md gives it no code block, only "the same script as AC-NEG-2 and AC-COMPAT-1, with
  `node ts-reader/dist/cli.js` in place of `$CHST`". The script sets `CHST` and `CHST_CORE` to that command, then holds AC-NEG-2.sh and
  AC-COMPAT-1.sh unchanged. It's N/A until the cut is Extended. Owner: please confirm that reading (see Needs decision).
- Preflight: `check.sh` runs `python3.14 -I tools/todo_coverage.py` before any ID, logs to `target/acceptance/logs/todo-coverage.log`
  and exits 1 if it fails (no report is left behind). TODO.md says fast and full mode; I also run it under `--only`, because H-4's
  Verify checks that the log exists straight after `pass_only`.
- Open issues: the two points above.
- Acceptance IDs affected: AC-META-1, AC-META-2, AC-META-4, AC-META-5 pass. AC-NEG-1 and AC-NEG-4 also pass, since they read only the
  fixtures.

### H-5 Python helper scripts — f6a04da
- Added the six helpers in `tools/acceptance/`. Each is standalone: `python3.14 -I` doesn't put the script's directory on
  `sys.path`, so they can't share a module.
- `trace.py` found 28 Core features, 18 decisions and 21 W/EXT/SEL rules, and none untraced. Its negative case (three traces removed)
  names all three. It also fails when an input is missing or yields nothing.
- `inspect_check.py` follows Appendix B's field kinds: ints are little-endian (signed for `mtime_seconds`) and become decimal strings
  beyond 2^53-1, hex fields are lowercase hex, and the PATH_POOL payload is UTF-8 text. My first version compared every string to hex,
  and failed on the PATH_POOL payload and on the bit-63 `optional_flags`; I fixed it from the spec's definition, not by loosening a
  check. It passes on the 10 valid fixtures and 6 exit-0 compat fixtures (the real `inspect` output doesn't exist yet; these are the
  fixtures' `inspect.json`).
- `tree_eq.py` walks by directory handle. It passes on all 10 fixtures' materialised trees, including `long-names` (paths beyond
  PATH_MAX; `cp -R` can't copy that tree, so I materialised it twice) and `deep`. Its Windows fallback (extended-length path
  strings) can't be run here.
- `flip_sweep.py` and `truncate_sweep.py` can't be run against the real CLI yet. I tried them against a throwaway mock `verify` that
  isn't in the repo: against a mock that accepts too much they reported the wrongly accepted flips, and against a mock that rejects any
  changed file they passed. A missing CHST exits 1 in both. In `--rehash` mode, `flip_sweep.py` parses the PATH_POOL range from the
  file itself (FORMAT_SPEC §5 and §6), not from `chst inspect`, to decide which flips may be accepted.
- AC-POS-3, AC-POS-4, AC-ROB-1 and AC-ROB-2 report FAIL because the CLI doesn't exist, as TODO.md expects.
- Also fixed stray backslashes in the "Needs decision" entry written in H-4.
- Open issues: none.
- Acceptance IDs affected: AC-META-3, AC-META-6 pass.

### H-6 `--done` mode — a4db6a6
- `./check.sh --done <ci-run-id>` downloads `acceptance-report-*` with `gh run download` (read-only), takes each ID's status from the report
  for this OS, runs AC-XP-1 for real with `$CI_RUN_ID` set, and exits by the usual rule (0 only if every ID is PASS or N/A). If the import
  fails, every ID that applies reports FAIL. It skips the TODO preflight.
- With no such run (`--done 1`: HTTP 404 from `gh`), it exits 1, AC-XP-1 is FAIL and the mode is `done`, as the Verify line expects.
- I also tried the success path of the import with a fake `gh` (not in the repo): statuses came through, and an ID missing from the
  report became FAIL.
- Open issues: the real import and AC-XP-1's `gh run view` can only be tried after the first CI run.
- Acceptance IDs affected: AC-XP-1 stays FAIL, until C-20.

### H-7 First honest local run — bf44911
- `./check.sh` on Linux (WSL, ext4, not `/mnt`), at commit 200f44b with a clean tree: **9 PASS, 54 FAIL, 3 NOT RUN, 19 N/A** (85 IDs).
  EVIDENCE.md's Linux column was filled from `report.json` with `local` in the CI column. The macOS and Windows columns are untouched
  (NOT RUN), because only a CI run can set them.
- PASS: AC-META-1, -2, -3, -4, -5, -6, -7, and AC-NEG-1 and AC-NEG-4 (these two read only the fixtures).
- NOT RUN: AC-ROB-4 and AC-ROB-7 (full-only), AC-XP-1 (done-only). N/A: 12 Extended IDs, and 7 IDs whose OS line excludes Linux.
- FAIL: the other 54. Each log shows a missing feature: no `Cargo.toml`, no `crates/`, no `rust-toolchain.toml`, no binary, no workflow
  file. None is a harness fault.
- A failing check's log was sometimes empty, because the script's own `test` fails silently under `-e` (AC-NEG-2 expects exit 6 and
  gets 127). So `check.sh` now appends "<script> exited N" to the log of a failing check.
- The Verify's EVIDENCE comparison was shown to fail on a tampered cell.
- Open issues: none.
- Acceptance IDs affected: all rows' Linux cells.

### CI-1 CI workflow — d677036
- Added `.github/workflows/check.yml`. Not run: the owner pushes. What it does:
  - **Triggers and runners:** `push`, `pull_request` and `workflow_dispatch`; `ubuntu-latest`, `macos-latest` and `windows-latest`, all
    `shell: bash`, `fail-fast: false`. Fast mode (`./check.sh`) runs on push and PR, `./check.sh --full` on manual trigger.
  - **Job result (D17):** GitHub fails a step on any non-zero exit, so the check step has `continue-on-error` and a final "Job result" step
    applies the rule from `report.json`: any FAIL fails; in full mode, a NOT RUN other than AC-XP-1 fails; no report fails. I ran that step's
    script against seven crafted reports, one for each rule.
  - **Every runner:** Python 3.14 from `setup-python` (on Windows, a `python3.14` shim script in `$HOME/bin`), `jq` 1.7 or later (installed
    if missing), the toolchain from `rust-toolchain.toml` once it exists (C-1), `CHST_BIG_ROOT=$RUNNER_TEMP`, GNU `time` on Ubuntu, and the
    disk-space cleanup on Ubuntu as the first step.
  - **Full mode:** the pinned nightly and `cargo-fuzz` 0.13.2 `--locked` on Linux and macOS, and a non-gating, `continue-on-error` cargo-fuzz
    try on Windows. The nightly, cargo-fuzz and Rust steps skip when `fuzz/` or `rust-toolchain.toml` doesn't exist yet (before C-1 and C-8).
  - **Artifacts:** `acceptance-report-<os>` holds `report.json` alone, as AC-XP-1 expects. Logs go to `acceptance-logs-<os>`.
- `git config --global core.autocrlf false` runs before checkout. Windows runners default to CRLF conversion, which would break the
  fixture hashes (AC-META-2) and the shell scripts. I used this step rather than a `.gitattributes` file, which would be a new repo file.
- Checked locally: the YAML parses, every `run:` block passes `bash -n`, and `pass_only AC-XP-2` passes. EVIDENCE.md's Linux column was
  refreshed from a new fast run at d677036 (10 PASS, 53 FAIL, 3 NOT RUN, 19 N/A).
- Not verified, since it needs the owner's push: the second half of the Verify line (three complete 85-result reports from the first run),
  and everything about the runners. The open items of DESIGN §9g–§9i (runner feasibility, nightly components, the Windows
  `FILE_SHARE_DELETE` behaviour, whether the Windows and Ubuntu Python 3.14 builds include `compression.zstd`) are to be recorded here from the first run.
- Open issues: action versions (`checkout@v4`, `setup-python@v5`, `upload-artifact@v4`) are my choice, by major tag, and I couldn't check
  them against GitHub. The owner may want them pinned to commit SHAs.
- Acceptance IDs affected: AC-XP-2 passes.
- **Status: the TODO box stays unticked.** The first half of the Verify line (`pass_only AC-XP-2`) passes. The second half
  (the three reports of the newest CI run) can't be run until the owner pushes and a run exists. Tick it after that.

### CI-1 follow-up: diagnostics, nightly fallback, Node 24 actions, expect_exit 127 — commit "CI-1: diagnostics, nightly fallback, Node 24 actions, expect_exit 127"
Applies fixes 1, 2, 3, 5 and 6 from the review of the first CI run (run 40584612828, commit 0054e3d). Fix 4 (dropping the Ubuntu
disk cleanup) and SHA-pinning were skipped on request. No status logic, check script or expected result changed.
- **Fix 1, diagnostics (check.yml):** a non-gating `Diagnostics` step (`continue-on-error`) prints the bash version, Python's version
  and Unicode version, whether `compression.zstd` imports (it prints MISSING if not), the jq version, `rustup show`, and on Windows
  `fsutil 8dot3name query C:`. The Ubuntu cleanup step now also prints `df -h /` before it deletes anything.
- **Fix 2, nightly fallback (check.yml):** in full mode, the Linux and macOS fuzz-toolchain step uses D16's pin
  `nightly-2026-10-01` when `fuzz/rust-toolchain.toml` doesn't exist yet. It installs it, lists the installed components, installs
  cargo-fuzz 0.13.2 `--locked`, and runs `cargo fuzz --help`. While it's using the fallback, a failure is a `::warning::` and doesn't
  fail the job; once `fuzz/rust-toolchain.toml` exists (C-8), a failure fails the job. The Windows try-step does the same, stays
  non-gating, and runs the fuzz target only if `fuzz/fuzz_targets` exists.
- **Fix 3, Node 24 actions (check.yml):** `checkout@v4`, `setup-python@v5` and `upload-artifact@v4` (twice) became `@v7`. Latest
  releases (via read-only `gh api`) were v7.0.1, v7.1.0 and v7.0.2; their `action.yml` at tag `v7` says `using: node24`. Pinned by major
  tag, not SHA.
- **Fix 5, `expect_exit` (lib.sh):** a command that `command -v` can't find now gives exit 127 on every OS. macOS's bash 3.2 reported 1.
  Runnable commands are unchanged, and a mismatch still returns 1.
- **Fix 6, failure diagnostics (check.sh):** when a check fails, the first 4 KiB of `$W/err`, `$W/*.err` and `$W/*.log` are appended to its
  log before `$W` is removed. This runs only after the exit code is known, so it can't change a status. AC-NEG-2's log now shows
  `target/release/chst: No such file or directory`.
- **Verified locally:** YAML parses and all 12 `run:` blocks pass `bash -n`. `expect_exit` tried with a missing command (wanted 127 passes,
  wanted 0 fails), a runnable command (right and wrong code), and a shell function. The Verify lines of H-1 (in a copy with the scripts
  removed, since H-1's counts assume none exist), H-2, H-3, H-4 and H-6, and `pass_only AC-XP-2`, all pass. A full `./check.sh` gives
  10 PASS, 53 FAIL, 3 NOT RUN, 19 N/A, and every ID's status and exit code matches the Linux report of the first CI run.
- **Not verified:** the workflow itself (it needs a push), and the new Node 24 action versions.
- EVIDENCE.md is unchanged: no status changed.
- Open issues: none.

### CI-1 follow-up: fuzz probe — commit "CI-1: fuzz probe"
Run #3 (full mode, commit 5057d70) showed that the D16 nightly (`nightly-2026-10-01`, components `cargo`, `rust-std`, `rustc`) and
cargo-fuzz 0.13.2 install on all three runners, but not whether `cargo fuzz run` can build and run a target. This adds a probe for that.
Only `.github/workflows/check.yml` changed. `check.sh`, the check scripts, the status logic and the expected results are untouched.
- **Linux and macOS (`Fuzz toolchain (full mode)`):** while the D16 fallback is in use (no `fuzz/rust-toolchain.toml`), after the
  toolchain setup it runs a probe: `cargo new --lib $RUNNER_TEMP/fuzz-probe --vcs none`, then in that directory
  `cargo +"$tc" fuzz init` and `cargo +"$tc" fuzz run fuzz_target_1 -- -runs=1000`. `$RUNNER_TEMP` is outside the checkout, so no repo
  file is touched. A failure prints a `::warning::` and doesn't fail the job. Once `fuzz/rust-toolchain.toml` exists (C-8), the probe
  doesn't run, because the real fuzz targets take over.
- **Windows (`Try cargo-fuzz on Windows (non-gating)`):** the same probe, with the path converted by `cygpath -u`. The step stays
  `continue-on-error`, and a failure prints `fuzz probe FAILED: ...` and lets the step finish.
- **Verified locally:** the YAML parses and all `run:` blocks pass `bash -n`. With stub `rustup`, `cargo` and `cygpath` commands, both steps
  were run once with everything succeeding (`fuzz probe ok`, step exit 0) and once with the fuzz run failing (a warning on Linux/macOS,
  `fuzz probe FAILED` on Windows, step exit 0). The Linux/macOS step with `fuzz/rust-toolchain.toml` present doesn't run the probe.
  `pass_only AC-XP-2` passes. A full `./check.sh` gives 10 PASS, 53 FAIL, 3 NOT RUN, 19 N/A, and every status and exit code is identical to
  the Linux report of the first CI run. Against run #3, the only differences are AC-ROB-4 and AC-ROB-7, which are NOT RUN in fast mode and
  FAIL in full mode.
- **Not verified:** the probe against the real nightly and cargo-fuzz. That needs a full-mode run after the push, and it's what
  this change is for. In particular the Windows MSVC AddressSanitizer case is unknown.
- EVIDENCE.md is unchanged: no status changed.
- Open issues: none.

### Pre-`checks-v1` review items — commit "CI-1: evidence from run 40592564145, TODO corrections"
Owner's seven requests before approving `checks-v1`. Nothing in `check.sh`, a check script, ACCEPTANCE.md, DESIGN.md or fixtures changed.
- **AC-NEG-1 and AC-NEG-4 are not vacuous, so I left them alone.** Neither script runs `$CHST` (`grep -c CHST` gives 0 for both). They check
  that the fixture set is complete (a fixture for every FORMAT_SPEC rule, the named sub-condition fixtures) and that each `expect.json`
  documents its base, its mutation and its rule. They pass because those fixtures exist, never because a command failed. Mutation test on a
  copy of `fixtures/`: with `PATH-6-alm.expect.json` removed, AC-NEG-1 exits 1 ("missing sub-condition fixture PATH-6-alm"); with one
  `mutation` field emptied, AC-NEG-4 exits 1. The check on exit codes, category and detail is AC-NEG-2, and it FAILs now (no binary).
  Tightening these two to need `$CHST` would duplicate AC-NEG-2 and change protected ACCEPTANCE.md text, so I didn't.
- **The 53 FAILs by reason** (fast run at c091a72, from each ID's own log): all fit "the product doesn't exist yet".
  - 16: no Cargo workspace (`could not find Cargo.toml`): AC-ENG-1, -3, -4, -8, AC-DET-3, AC-ROB-3, -5, AC-SAFE-8, -12, -13, -14, -15,
    AC-PACK-3, -10, -12, AC-LIM-1.
  - 4: a repo file the task creates is missing: AC-ENG-2 and AC-ENG-7 (`crates/*/src/lib.rs`), AC-ENG-5 (`Cargo.lock` not tracked), AC-ENG-6
    (`rust-toolchain.toml`).
  - 33: no `chst` binary (`target/release/chst: No such file`, or `wanted exit N, got 127`): AC-POS-1 to -4, AC-NEG-2, -3, AC-DET-1, -2,
    AC-ROB-1, -2, -6, -8, -9, AC-SAFE-1, -2, -3, -4, -6, -7, AC-PACK-1, -2, -4, -5, -6, -9, -11, AC-LIM-2, -3, -4, AC-CLI-1, -2, -3,
    AC-COMPAT-1.
  - A grep of all 53 logs for missing tools, Python tracebacks, shell syntax errors and unbound variables found nothing. None doesn't fit.
    AC-DET-2 and AC-LIM-4 exit 4 because `jq -e` gets empty input after the binary is missing; the cause is still the missing binary.
- **12/7 vs 13/6:** counted from ACCEPTANCE.md: 12 Extended IDs, and 7 Core IDs whose OS line excludes Linux (AC-ROB-4W, AC-SAFE-5, -9, -10,
  -11, AC-PACK-7, -8): 19. ACCEPTANCE.md was right; TODO.md's H-1 Verify prose said 13 and 6, and now says 12 and 7.
- **H-5 sub-task boxes ticked.** All six scripts exist, and H-5's own Verify commands were re-run and pass (tree_eq on equal and unequal
  trees, flip_sweep and truncate_sweep rejecting a missing CHST, AC-META-3 and AC-META-6 PASS).
- **X-0 added to TODO.md** (AC-X-TS-2 script to be stated in ACCEPTANCE.md before the cut changes). Its Verify fails today, as it should.
- **EVIDENCE.md** is now filled from run 40592564145 (fast mode, commit c091a72, clean tree): three complete 85-result reports (linux
  10 PASS, 53 FAIL; macos 9 PASS, 50 FAIL; windows 9 PASS, 49 FAIL), checked row by row. AC-META-7 (the `--self-test`) is PASS on all
  three. The jobs are red only at the "Job result" step, as designed. The stale "Initial state" line is removed. The OS differences are all
  OS-line N/A (e.g. AC-META-5 is Linux-only).
- **Not done:** the full-mode run with the fuzz probe. `gh workflow run` was refused in this session, so no full-mode run exists at or after
  7a69b42. Run 40587076660 (full mode) is at 5057d70, before the probe. The Windows MSVC AddressSanitizer answer and the fuzz-scope decision
  in DESIGN (request 4) wait for that run.
- Acceptance IDs affected: none changed status.

### CI-1 first full-mode run and the §9g–§9i open items — run 40689182770 (workflow_dispatch, commit b94ca41, clean tree)
Closes CI-1: both halves of its Verify pass (`pass_only AC-XP-2`; the newest run has `linux macos windows` reports with 85 results each).
Nothing in `check.sh`, the check scripts, ACCEPTANCE.md, DESIGN.md or fixtures changed. EVIDENCE.md is now filled from this run's reports.
- **Run result.** Complete 85-result full-mode reports on all three OSes. Linux 10 PASS, 55 FAIL, 19 N/A, 1 NOT RUN; macOS 9, 52, 23, 1;
  Windows 9, 51, 24, 1. The one NOT RUN is AC-XP-1 on each (the done-only check). The jobs are red only at the "Job result" step, by design.
  AC-META-7 (`--self-test`) is PASS on all three.
- **Full-only IDs, first run.** AC-ROB-4 (Linux, macOS): FAIL, `fuzz/rust-toolchain.toml` doesn't exist (C-8). AC-ROB-4W (Windows): FAIL, no
  `Cargo.toml`. AC-ROB-7 (all three): FAIL, `target/release/chst` doesn't exist. Each is the product missing, not the harness.
- **§9g runner feasibility.** All three runners complete the whole run. Ubuntu has 88 GiB free before the cleanup step and 105 GiB after.
  The Windows workspace is on D: with 220 GiB free; macOS has 95 GiB free. Enough for AC-ROB-7's 4 GiB file on each.
- **§9g nightly components.** `nightly-2026-10-01` (rustc 1.101.0-nightly, 21b707e3f) installs on Linux, macOS and Windows with exactly
  `cargo`, `rust-std` and `rustc` (minimal profile). cargo-fuzz 0.13.2 `--locked` installs on all three. The probe (`cargo fuzz init` and
  `cargo fuzz run fuzz_target_1 -- -runs=1000`) passes on Linux and macOS, so no further component is needed there. The "nearest earlier date"
  fallback isn't needed.
- **§9g Python.** 3.14.9 on Linux and Windows, 3.14.8 on macOS; `unicodedata` is Unicode 16.0.0 and `compression.zstd` imports on all three.
- **Tool versions.** jq 1.8.1 (Linux) and 1.8.2 (macOS, Windows). bash 5.3.9 on Linux, 3.2.57 on macOS (so the bash-3.2 rule in `lib.sh`
  matters), 5.3.15 under Git for Windows.
- **Windows 8.3 names.** `fsutil 8dot3name query C:` reports creation ENABLED on C:. The checkout is on D:, which I didn't query. Relevant to
  AC-SAFE-10 when C-15 exists.
- **§9h M5 (`AT_SYMLINK_NOFOLLOW`) and §9i P4 (`FILE_SHARE_DELETE`).** Not answered. Both need code that doesn't exist yet (C-14c, C-17), and
  the run doesn't print kernel versions. Still open.
- Open issues: the fuzz-scope item under "Needs decision".
- Acceptance IDs affected: AC-ROB-4, AC-ROB-4W and AC-ROB-7 moved from NOT RUN to FAIL (they ran for the first time); no PASS changed.
