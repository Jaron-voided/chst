# Chst — Progress

Append-only log, one entry per task. Results are in EVIDENCE.md, not here.

## Needs decision

- **AC-X-TS-2 has no script in ACCEPTANCE.md** (§3.13). *Owner agreed to (b); tracked as TODO X-0. Open until ACCEPTANCE.md changes.* I derived `tools/acceptance/checks/AC-X-TS-2.sh` from its prose (see H-4).
  Options: (a) keep the derived script; (b) have ACCEPTANCE.md state the script. Recommendation: (b) before the cut becomes
  Extended, so the script is the document's, not mine. It's N/A under Core, so nothing is blocked.

- **RESOLVED: owner chose (a); recorded in DESIGN decision 18.** **Fuzz scope and DESIGN decision 18 (Windows).** The first full-mode run with the fuzz probe (run 40689182770, commit b94ca41) shows
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

- **AC-ENG-2 cannot pass as written** (ACCEPTANCE.md §3.2; owned by C-2, found while doing C-1). Its first line requires
  `#![forbid(unsafe_code)]` in `crates/chst-format/src/lib.rs`. Its second line, `if grep -rnE 'std::fs|std::env|std::process|std::net|unsafe'
  crates/chst-format/src; then exit 1; fi`, matches the word `unsafe` in that same line, so it always exits 1. AC-ENG-7 also requires the
  `forbid` line, so it can't be moved or reworded. The log shows `crates/chst-format/src/lib.rs:5:#![forbid(unsafe_code)]`.
  Options: (a) the second line ignores the `forbid` line:
  `if grep -rnE 'std::fs|std::env|std::process|std::net|unsafe' crates/chst-format/src | grep -vE ':[0-9]+:#!\[forbid\(unsafe_code\)\]$'; then exit 1; fi`
  (still exits 1 on any other match, including a real `unsafe` block, and works under `pipefail`); (b) check for `unsafe` as a whole word
  with `grep -w`, which doesn't match `unsafe_code` (this also stops a comment like "unsafe code" from passing; weaker on `std::` names, so
  it would be a separate grep); (c) leave it, which makes AC-ENG-2 unfixable and blocks the definition of done. Recommendation: (a), the
  smallest change that keeps every other match fatal. It needs the owner's approval (protected ACCEPTANCE.md and the check script).
  C-2 can't be ticked until this is settled.

- **RESOLVED (owner chose (a); applied with C-2): AC-ENG-4 cannot pass while the reader test needs `$CHST_LIM2`** (owned by C-2; the same applies to C-3 to C-5). TODO.md says
  `task_reader.rs` reads the sparse LIM-2 file from `$CHST_LIM2` and *fails if it's unset*, and that these tests stay in the workspace, which
  AC-ENG-4 runs. But AC-ENG-4's script, `cargo_test_nonempty --workspace --locked --release`, sets no `CHST_LIM2`, and `check.sh` doesn't
  either (grep finds the variable only in TODO.md). So AC-ENG-4 always FAILs on `core/invalid/LIM-2 is a sparse recipe and $CHST_LIM2 is not
  set`. Confirmed both ways: unset, the workspace run fails on that one test; with the variable set, all 10 workspace tests pass.
  Options: (a) AC-ENG-4's script creates the file the way TODO's Verify lines do:
  `CHST_LIM2=$(fixture_file $FX/core/invalid/LIM-2.expect.json) cargo_test_nonempty --workspace --locked --release`
  (one line in ACCEPTANCE.md §3.2 and `AC-ENG-4.sh`; Rust never creates a fixture, as CLAUDE.md requires); (b) the test creates the sparse file
  itself from the recipe (Rust code materialising a fixture, which CLAUDE.md rules out, and it needs a sparse-file call on Windows);
  (c) the test skips LIM-2 when the variable is unset (it silently stops testing LIM-2, which TODO.md rules out).
  Recommendation: (a). It needs the owner's approval (protected ACCEPTANCE.md and check script). C-2 can't be ticked until this is settled.
- **RESOLVED (owner chose (a); recorded in FORMAT_SPEC Appendix A with C-2): no detail code for a general I/O failure.** FORMAT_SPEC §16 gives category `io` (exit 3) but no detail code except
  `extract.no-atomic-rename`, while the CLI prints `error[<category>/<detail>]` and JSON reports carry `detail`. `chst-format` uses `io.read`
  for failing to read or seek the input, and (revised by the owner) `io.memory` for an index it can't allocate. Options: (a) `io.read` for
  the reader (writer and extractor I/O would get their own codes in C-9 and C-14); (b) one code, `io.error`, for every I/O failure;
  (c) no detail (empty), which breaks the `error[...]` format. Recommendation: (a), recorded in FORMAT_SPEC Appendix A. No check depends on it
  yet (AC-CLI-1 asserts only exit 3). Needs the owner's approval, because it adds a code to the spec's output.

- **RESOLVED (owner chose (a); committed with "Mutation suites" in the log): keeping the mutation suites in the repo** (owner's request during C-5). C-3 and C-4 used throwaway scripts in
  the session scratchpad, so their mutations can't be re-run after later changes. For C-5 I wrote the proposed form and used it:
  `tools/mutants/mutate.py` (Python 3.14 standard library only) runs a suite file, `tools/mutants/<task>.toml`. Each mutant is one or
  more exact text replacements; an old text that doesn't occur exactly once is an error before anything is changed, so a suite that has
  gone stale fails loudly instead of skipping. The unmutated code must pass every command first. Each mutant must compile, and is
  caught if any of the suite's commands fails (a timeout counts as caught). Sources are restored after every mutant, also on Ctrl-C,
  and their SHA-256 is compared with the originals at the end. Exit 0 only if every mutant was caught. Run:
  `python3.14 -I tools/mutants/mutate.py tools/mutants/C-5.toml [--only TEXT] [--list]`. The files are in the session scratchpad
  for review.
  Options: (a) add `tools/mutants/` as standalone tools, run by hand whenever the mutated files change, with results logged in
  PROGRESS.md; not a check, so `check.sh`, ACCEPTANCE.md and EVIDENCE.md don't change; (b) as (a), plus a new `check.sh` mode or a
  manual CI job that runs every suite (a new check: slow, about 5 minutes for C-5's 43 mutants locally, and every code change that
  touches a mutated line means updating the suite); (c) `cargo-mutants`, which isn't on D15's list and generates mutants by syntax rather
  than by spec rule. Recommendation: (a), and also rewrite C-3's 10 and C-4's 93 mutations as `C-3.toml` and `C-4.toml` against the
  current code, so all three tasks can be re-run. Needs the owner's approval before anything is committed.

- **The mutation-suite rule in CLAUDE.md** (owner asked for the rule "where future sessions will see it, CLAUDE.md if that's allowed").
  CLAUDE.md is protected, so I may only propose a diff. The rule is in TODO.md now ("How this file works", the "Mutation suites" bullet),
  which every session reads before it picks a task. Proposed diff for CLAUDE.md, "Implementation rules", after the "Never delete, skip,
  ignore, or loosen a test" bullet:
  ```diff
   - Never delete, skip, ignore, or loosen a test or check to make it pass. Placeholder or empty tests
     never count as passing.
  +- Mutation suites (tools/mutants/): a task that changes code a suite mutates updates the suite and
  +  re-runs it before the task is ticked; a task that adds tested code adds its own suite. Every mutant
  +  that isn't skipped must be caught, and a mutant is skipped only with a written reason.
  ```
  Options: (a) apply it, so the rule sits next to the other test rules; (b) leave it in TODO.md only. Recommendation: (a). TODO.md ranks
  below CLAUDE.md and is edited every task, so the rule is easier to lose there.

- **Detail codes the CLI needs but the spec doesn't define** (found in C-6a; nothing blocked). Appendix C says usage errors use detail
  codes beginning `usage.`, but FORMAT_SPEC defines only `usage.limit` and `usage.pattern`. C-6a uses, provisionally (in
  `crates/chst-cli/src/args.rs` and `main.rs`): `usage.command` (no command, or an unknown one), `usage.option` (an option the command
  doesn't take, or a value given to one that takes none), `usage.argument` (FILE missing, or one operand too many), and `io.write`
  (stdout can't be written; Appendix A lets writers define their own `io` details). Two temporary ones go away as tasks land:
  `internal.not-implemented` (exit 70) for `pack`, `list`, `inspect` and `extract` until C-6b, C-6c, C-9 and C-14. No check depends on
  any of them: AC-CLI-1 asserts only exit 2.
  Also a reporting choice: with `--json`, a failure prints the JSON failure report whenever the command is known, even if the error comes
  before `--json` on the line; an unknown command gets only the stderr line, because a report's `command` field needs a command.
  Options: (a) add the four codes to FORMAT_SPEC Appendix A as they are; (b) one code, `usage.syntax`, for every usage error other than
  `usage.limit` and `usage.pattern` (simpler, less useful to scripts); (c) leave them out of the spec as tool-specific. Recommendation:
  (a), as was done for `io.read` and `io.memory` in C-2. Needs the owner's approval (protected FORMAT_SPEC.md).

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

### CI-1: fuzz scope decision recorded
Owner chose option (a): decision 18 is confirmed. cargo-fuzz covers Linux and macOS (AC-ROB-4) and Windows uses the AC-ROB-4W fallback.
DESIGN.md's decision log row 18 now says so, and cites run 40689182770. Only that row changed.
- Left as written: two "provisional" notes remain in ACCEPTANCE.md (§1.3's table, line 137, and AC-ROB-4W's heading, line 675). They're
  protected and now out of date; the owner may want to approve dropping the word. DESIGN §9g's list (line 801) is a historical review note.
- Acceptance IDs affected: none.

### C-1 Workspace skeleton — 6e450f2
- Added `rust-toolchain.toml` (1.99.1, rustfmt and clippy), the root `Cargo.toml` (resolver 3, edition 2024, `rust-version = "1.99"`, members
  `chst-format`, `chst-fs`, `chst-cli`, `fuzz` excluded), the three crates, and committed `Cargo.lock` and `fuzz/Cargo.lock`.
- Lint headers per D18: `forbid(unsafe_code)` in `chst-format/src/lib.rs` and `chst-cli/src/main.rs`; in `chst-fs`, `deny(unsafe_code)`,
  `deny(clippy::undocumented_unsafe_blocks, clippy::missing_safety_doc)` and the single `#[cfg(windows)] #[allow(unsafe_code)] mod windows;`
  (with an empty `windows.rs`, so the module exists when it compiles on Windows). `chst-fs` has the non-default `test-hooks` feature.
- **No external dependencies yet.** They come with the first task that uses them (C-2: `sha2`; and so on), which keeps AC-ENG-2's exact
  dependency list in view. `fuzz/` alone depends on `libfuzzer-sys` 0.4 (D15) and `chst-format`.
- **`fuzz/` is a skeleton, ahead of C-8.** AC-ENG-5 and AC-ENG-6 (C-1's checks) read `fuzz/Cargo.toml`, `fuzz/Cargo.lock` and
  `fuzz/rust-toolchain.toml`, which TODO lists under C-8. I added only the manifest (its own `[workspace]`), the nightly pin, the lockfile and an
  empty library, because cargo rejects a package with no target. C-8 adds the cargo-fuzz targets. A side effect for CI: with
  `fuzz/rust-toolchain.toml` present, the full-mode Linux and macOS nightly and cargo-fuzz install becomes gating (it worked in run
  40689182770), and the throwaway probe no longer runs.
- **The `chst` binary is a stub** that prints `chst: not implemented yet` and exits 70 (`internal`), a code no check expects, so a check can't
  pass because the stub happens to exit as the check wants. Checked: the only new PASSes are below.
- Verify: `pass_only AC-ENG-1,AC-ENG-5,AC-ENG-6; cargo build --release --locked; test -x target/release/chst` passes. AC-ENG-5 needed the
  lockfiles to be tracked, so the files were `git add`ed before the Verify ran, as they are at commit time.
- Fast run on the clean tree at 6e450f2: 14 PASS, 49 FAIL, 3 NOT RUN, 19 N/A. New PASSes: AC-ENG-1, -5, -6, and **AC-ENG-3**, which belongs to
  C-6a. It is an absence check (the CLI must not depend directly on `sha2`, `unicode-normalization` or `zstd`), and it holds because the CLI
  depends on nothing yet. It passes honestly but early; it stays meaningful for C-6a.
- Re-check: AC-ENG-7 FAILs as expected (`counting_alloc.rs` doesn't exist until C-7).
- EVIDENCE.md: only the four rows whose status changed were updated (Linux PASS, `local`); their macOS and Windows cells are NOT RUN until a
  CI run covers this commit. Other rows keep the results of the earlier CI runs.
- Open issues: the AC-ENG-2 item under "Needs decision".
- Acceptance IDs affected: AC-ENG-1, AC-ENG-5, AC-ENG-6 (PASS); AC-ENG-3 (PASS early).

### C-1 CI result — run 40694068794 (fast, commit 8543aa6)
- Complete 85-result reports on all three OSes, clean tree. AC-ENG-1, -3, -5 and -6 are PASS on Linux, macOS and Windows. AC-ENG-1 includes
  clippy with the SAFETY lints and `mod windows;` compiling on Windows. AC-ENG-2, -4, -7 and -8 FAIL on all three, as expected (their tasks
  don't exist yet). The jobs are red only at the "Job result" step. The only PASS differences between the OSes are AC-META-5, which has a
  Linux-only OS line.
- EVIDENCE.md: the four C-1 rows now carry this run (macOS and Windows from CI). Other rows keep their earlier CI results, which this run
  doesn't change (every other status is the same).
- AC-ENG-2 fix (a) is approved by the owner and prepared, but not committed: the owner asked to see the diff first.
- Open issues: none new.
- Acceptance IDs affected: AC-ENG-1, AC-ENG-3, AC-ENG-5, AC-ENG-6 (PASS on all three OSes).

### C-2 Header, trailer and structure hash — 483e1b5
- `chst-format`: `error.rs` (the nine §16 categories with exit codes, the detail codes for steps 1 to 8, and an `Error` that displays as
  `error[<category>/<detail>]: <message>`), `limits.rs` (LIM-3 to LIM-6 with their defaults), `format.rs` (header and trailer parsing at
  constant offsets in fixed-size arrays, so no input can make them fail), `reader.rs` (`open`: §13 steps 1 to 8 in order, with all
  arithmetic checked, and the index allocated with `try_reserve_exact` only after TRL-2, LIM-2 and LIM-4 and bounded by the real file length).
  No `std::fs` and no `unsafe`; AC-ENG-2 passes.
- 10 unit tests (header and trailer field offsets, every step-1 to step-8 rule's order, the overflow cases of TRL-2, LIM-2 before LIM-4 with
  a virtual 4 GiB source that holds only a header and a trailer, and a failing source).
- `chst-cli/tests/task_reader.rs` with `reader_step_8`: it classifies all 128 files (118 expectations plus 10 valid) by the §13 step of
  the first violation, from the rule, or for `compat/` from the detail; 19 are rejected with exactly their expected detail, exit code and
  category, and 109 pass. It fails if `$CHST_LIM2` is unset, as TODO.md says.
- **The test can fail.** Mutating the reader made it fail each time: TRL-3 reported as the wrong category; HDR-5 skipped (`core/invalid/HDR-5`
  accepted); LIM-4 checked before LIM-2 (`core/invalid/LIM-2` got `limit.index-size`); the magic check disabled (`core/invalid/HDR-2` accepted).
  `reader.rs` was restored and diffed against the saved original afterwards. My first mutation run stopped before restoring (`set -e` with
  `pipefail`), which I noticed from the output and fixed by restoring from the saved copy before going on.
- **`unicode-normalization` is pinned to `=0.1.24`.** `chst-format` lists it now because AC-ENG-2 demands exactly `sha2` and
  `unicode-normalization`, but it isn't used until C-4. The version cargo picked, 0.1.26, has **Unicode 18.0.0** tables; 0.1.25 has 17.0 and
  0.1.24 has 16.0.0, which D16 requires. I checked each version's `UNICODE_VERSION` and pinned 0.1.24 in the manifest with a comment, so a
  `cargo update` can't drift to the wrong tables. AC-ENG-8 (C-4) will test the tables.
- **Spec changes, approved by the owner and shown as a diff first.** (1) AC-ENG-4 (ACCEPTANCE.md §3.2 and `AC-ENG-4.sh`) now runs
  `CHST_LIM2=$(fixture_file $FX/core/invalid/LIM-2.expect.json) cargo_test_nonempty --workspace --locked --release`, with a note under the block.
  The owner asked whether C-3 to C-5 need more variables, so one change covers them. I searched TODO.md, ACCEPTANCE.md, DESIGN.md,
  FORMAT_SPEC.md, `check.sh` and the helpers: `CHST_LIM2` is the only fixture variable the plan names, and `fixtures/` holds one sparse
  recipe (`LIM-2.recipe.json`). Every `reader_step_*` Verify line in C-2 to C-5 uses that same variable. The other workspace tests read
  in-tree files (`hostile/`, `fuzz-regressions/`, `valid/*/tree.json`). One rule for later tasks, to avoid the same trap: a config
  variable such as `CHST_PROP_CASES` (C-14b) must have a default in the test, because AC-ENG-4 runs it without setting anything.
  (2) FORMAT_SPEC Appendix A has rows for `io.read` (read or seek failure, input ends early) and, after the owner's review, `io.memory`
  (the reader can't allocate the memory it needs). Memory failure was first grouped under `io.read`, which would send a user looking for a
  disk problem. Both stay in category `io` (§16: an operating-system failure); other `io` details come with the tasks that need them (C-9, C-14).
  The owner also widened §16's `io` definition to cover it ("Operating-system I/O or resource failure: reading, writing or seeking fails, or
  memory can't be obtained"). The allocation is a helper, `allocate_index`, and a unit test covers `io.memory`: asking for `u64::MAX` and
  `usize::MAX` bytes fails at once with `CapacityOverflow` (more than `isize::MAX`), before the allocator is asked for anything; a 16-byte
  request succeeds. The test is portable, because on a narrower `usize` the conversion fails instead.
- Verify: `pass_only AC-ENG-2,AC-ENG-4` and `CHST_LIM2=… reader_step_8` both pass. The META and NEG checks still pass after the spec edits.
- Fast run on the clean tree at 483e1b5: 16 PASS, 47 FAIL, 3 NOT RUN, 19 N/A. AC-ENG-1 to -6 are PASS.
- EVIDENCE.md: the AC-ENG-2 and AC-ENG-4 rows (Linux PASS, `local`); macOS and Windows stay NOT RUN until a CI run covers this commit.
- Acceptance IDs affected: AC-ENG-2, AC-ENG-4 (PASS). EVIDENCE.md follows in the next commit, from a clean-tree run.

### C-2 CI result — run 40699772200 (fast, commit 3025d62)
- Complete 85-result reports on all three OSes, clean tree. AC-ENG-2 and AC-ENG-4 are PASS on Linux, macOS and Windows, and AC-ENG-1, -3, -5
  and -6 stay PASS everywhere. The jobs are red only at the "Job result" step, by design.
- **Line endings on Windows: not a problem.** AC-ENG-2's exact-line `forbid` match passes there, so the checkout is LF (the workflow's
  "No line-ending conversion" step).
- **LIM-2 fixture cost on Windows: not noticeable.** `reader_step_8` runs in 0.01s there. AC-ENG-4 takes 9s on Windows against 4s on Linux and
  macOS, mostly the 6.9s compile; Windows is about 2x slower throughout (AC-ENG-1 12s vs 6s; all checks 83s vs 28s and 26s). The per-ID
  `duration_s` in the reports is the source.
- EVIDENCE.md: the AC-ENG-2 and AC-ENG-4 rows now carry this run. Nothing to fix in C-2.
- Acceptance IDs affected: AC-ENG-2, AC-ENG-4 (PASS on all three OSes).

### C-3 Sections — 008019b
- Added `chst-format/src/sections.rs`: `parse_sections(index, header, limits)` (also `Opened::sections(&limits)`), which runs §13 step 9 as
  one pass per rule over the index, in §13's order: SEC-1 frames every section (checked `u32 * u64` product, then `usize` conversion, then
  the bounds), SEC-2 (unsupported, so a later `malformed` file isn't reached), SEC-3, SEC-4 for every section, SEC-5 for every section, then
  LIM-3 on the entry count. Nothing is allocated in proportion to the number of sections: the passes re-walk the index. The result is the
  three required tables with their payload ranges, for C-4.
- **A Core reader's flag knowledge is "none".** `KNOWN_OPTIONAL_FLAGS = 0` (next to `KNOWN_REQUIRED_FLAGS`): SEC-5 fixes the record size only if
  the header sets no flag this reader doesn't know. So the compat files `unknown-optional-wider-entries`, `entry-attrs` and `kv-metadata` pass
  in a Core reader (their wider records and the `KV_METADATA` section, type `0x10`, are accepted and skipped), and `SEC-5` and `SEC-5-entry`,
  which set no flag, are rejected. The Extended features change these constants later.
- 9 unit tests, with hand-built indexes: payload ranges, the SEC-1 failures (cut-off header, payload past the end, overflow, a product that
  wraps to exactly 2^64), and the order of the passes (SEC-1 before SEC-2, SEC-2 before SEC-3, SEC-4 before SEC-5, the layout before LIM-3).
- `reader_step_9` in `task_reader.rs`: the running total is 32 rejections (19 + 13) with 96 files passing, as TODO.md says.
- **Mutation checks, all caught** (ten, one at a time, each restored by a `trap`): SEC-2 off; SEC-5 off; SEC-5 without the unknown-flag
  exemption; SEC-3 allowing equal types; SEC-3 allowing a repeated required type; the SEC-4 blob minimum off by one; the path pool allowing any
  size; LIM-3 off by one; SEC-1 allowing a payload one byte past the end; SEC-1 with a wrapping product. The last one was **not caught** at
  first: my overflow cases wrapped to a huge value that still didn't fit, and the 2^60 fixture only fails later by coincidence (the framing
  after the wrapped section goes wrong). I added the case `65536 * 2^48 = 2^64`, which wraps to 0, and it is caught. After a refactor (the
  three required sections are taken one at a time by `take_required`, which removed a `Vec` and an impossible `Internal` branch) I ran all
  ten again: all caught.
- Verify: `CHST_LIM2=… cargo_test_nonempty --release -p chst-cli --test task_reader -- reader_step_` passes (`reader_step_8` and `reader_step_9`).
- C-3 has no acceptance ID of its own. Local fast run: AC-ENG-1 to -6 and the rest unchanged (16 PASS), clippy with `-D warnings` is clean.
- Clean-tree fast run at 008019b: 16 PASS, 47 FAIL, 3 NOT RUN, 19 N/A, the same as before C-3.
- Open issues: none.
- Acceptance IDs affected: none directly. EVIDENCE.md is unchanged, because no status changed.

### D1 confirmed after the readiness audit; recovery notes — 6d4a3f2
Not a TODO task: an owner decision and owner-approved spec changes, shown as a diff before committing.
- **Owner decision:** an independent, read-only audit of FORMAT_SPEC.md and the code at 42e318e confirmed D1: no per-record headers; names and
  blob boundaries are reached only through the index, which only the trailer locates. Damage inside file data stays local (blob keys,
  BLB-6), but damage to the index or trailer, including truncation, loses names and boundaries. The owner kept D1 for v1 and put recovery
  of damaged archives out of scope for Chst, to be handled by a separate tool.
- **DESIGN.md:** an owner-approved amendment at the end of D1 records the above.
- **FORMAT_SPEC.md Appendix D, "Recovery notes (non-normative)":** the byte-level anchors an external recovery tool can rely on, each with the
  rule that guarantees it: header magic (HDR-1, HDR-2), trailer magic (TRL-1), index location (TRL-2, LIM-2), structure hash (TRL-3), section
  headers (§6, SEC-1, SEC-3), record sizes (SEC-4, SEC-5), blob layout from offset 32 (§3, BLB-4), blob keys (BLB-5, BLB-6, ENT-4) and order
  (CAN-1 to CAN-3). The owner approved the last two rows I added beyond the requested list. No anchor needed a new rule: section order, the
  owner's example of a possible gap, is fixed by SEC-3. The one conditional anchor is the exact record sizes, which hold only for a reader that
  knows every flag (SEC-5), so the appendix tells scanners to accept larger sizes. It also says section-header patterns and both magics can
  occur inside file data or the path pool, and how a scanner confirms a candidate. No rule ID was added or changed; the appendix has no
  capitalised RFC 2119 keywords and no bold rule IDs.
- **FORMAT_SPEC.md status line:** "Approved at `plan-v1`. Implementation is in progress. Normative and language-neutral; Appendix D is
  non-normative." (The owner reworded my "except Appendix D", which read as if the appendix weren't language-neutral.)
- Checks after the change: `tools/todo_coverage.py` passes; AC-META-1 to -7, AC-NEG-1 and AC-NEG-4 PASS; `trace.py` still counts 28 features,
  18 decisions and 21 rules, none untraced.
- Acceptance IDs affected: none. EVIDENCE.md is unchanged.
- Next: C-4, in a fresh session.

### C-4 Blobs, entries, paths and canonical form — 1fdb8ad
- Added `chst-format/src/tables.rs`: `parse_tables(opened, sections, limits, purpose)` (also `Opened::tables`) runs §13 step 10, (a) to (p),
  as one pass per item in order. Each per-record item checks every rule of one record before the next record. It returns the blob table,
  the entries (directory, or file with its blob's index) and the paths, for C-5.
  - **What a Core reader checks.** It knows no flag, so BLB-2 rejects every encoding but 0. ZST-2, ZST-3 and LIM-6 apply only to encoding 1
    and never run, and neither do FLG-1, ATT-1 or KV-1 ((m) to (o)).
  - **`Purpose`** (List, Inspect, Verify, Extract) decides LIM-5: only Verify and Extract check it. The sum is checked u64; overflow
    exceeds every limit.
  - **Allocation.** Per-blob and per-entry vectors are allocated only after step 9 (SEC-1 bounds the counts by the index, and LIM-3 bounds the
    entries), and every one is fallible (`io.memory`).
  - **Lookups without extra passes.** ENT-4 reuses BLB-5's key-sorted index for a binary search. ENT-6 binary-searches the canonically sorted
    entries. PATH-11 sorts entry indexes by fold key.
  - **CAN-2 needs no set:** keys are unique after BLB-5, so the blobs referenced so far are exactly `0..seen`.
- Added `chst-format/src/paths.rs`: PATH-1 to PATH-10 in §13's order 1, 2, 4, 3, 5, 6, 7, 8, 9, 10. PATH-2 is
  `unicode_normalization::is_nfc` (the authoritative check: the quick check, then full NFC on "maybe"). Paths in error messages are escaped,
  so a bidi or control character in a hostile name can't change what's printed.
- Added `chst-format/tests/unicode_tables.rs` (AC-ENG-8, `forbid(unsafe_code)`). It asserts `UNICODE_VERSION == (16, 0, 0)` and that U+113CE
  has ccc 9. It reads the entry paths of `core/invalid/PATH-2-unicode16` directly (steps 1 to 9, then its own decoding of the entry table)
  and asserts that exactly one is not NFC, `docs/x` U+0301 U+113CE. Then it asserts that the reader rejects the file with `path.nfc` for all
  four purposes.
- Added `reader_step_10` to `task_reader.rs`, in Verify mode so LIM-5 runs with its `args`. All 128 files are classified on the first run:
  108 rejected with exactly their expected detail, exit and category, including all 23 `core/attacks`, and 20 passing.
- 44 unit tests in `chst-format` (17 new in `tables`, 8 in `paths`), built from hand-made tables. Step 10 never reads blob data, so a test can
  declare blobs of 2^62 or 2^63 bytes without allocating them.
- **Mutation checks: 93 one-at-a-time mutations, all caught in the end.** I used a throwaway script in the session scratchpad, not in the repo.
  It applies each mutation as exact replacements, each of which must match once. It requires the mutant to compile, runs the `chst-format`
  tests and `reader_step_10` separately, and restores both files from saved copies. A hash check confirmed the sources were identical
  afterwards.
  - **What was mutated:** every rule turned off or narrowed (each PATH-6 code point or range, each PATH-7 character, each PATH-9 name
    family); off-by-one limits (PATH-3, PATH-10, LIM-5); wrapping instead of checked arithmetic (BLB-4, ENT-5, LIM-5); LIM-5 for the wrong
    purposes, or counting each blob once; ENT-6 or PATH-9 or PATH-8 on the wrong segment; NFC by the quick check alone; records read at
    the base size; 13 order changes between the step-10 items and between the path rules; and per-rule passes in place of per-record ones
    for (a) and (d).
  - **First run: 86 caught, 7 survived.** All seven were real gaps in my tests, not equivalent mutants:
    - **CAN-3 allowing a gap, or allowing an overlap.** Each of my cases also broke the other direction later in the walk, so they were still
      caught as CAN-3. Paths sharing pool bytes (`ab` and `bc` in the pool `abc`), and an unused byte between paths (`a` and `c` in `axc`),
      had no test, and each mutant accepts its case completely.
    - **BLB-4 with a wrapping add.** My overflow case was rejected later anyway; it needs a wrap that lands on an otherwise exact tiling.
    - **Blob records always read at 64 bytes.** No fixture has a wider blob table, and my helper only built 64-byte records.
    - **Three order swaps** (BLB-5 before BLB-4, ENT-6 before CAN-1, PATH-10 before PATH-9), for lack of a case that breaks both rules.
  - I added a test for each, including wider blob (72) and entry (64) records under an unknown optional flag, with the extra bytes filled.
    **Second full run: 93 of 93 caught.** 47 are caught by both the unit tests and `reader_step_10`. 45 are caught only by the unit tests,
    not by the fixtures: for example the PATH-7 characters no fixture uses, LIM-5 overflow and purpose, the per-record order, and most order
    swaps. One, a blob offset allowed beyond the running offset (BLB-4), is caught only by the fixtures.
- **AC-ENG-8 can fail.** Offline, with the crate pinned to 0.1.23 (Unicode 15.1), both of its tests fail. The PATH-2-unicode16 path is judged
  NFC there, which is the disagreement F12 describes. With 0.1.25 (17.0), the version assertion fails. `Cargo.toml` and `Cargo.lock` were
  restored from saved copies, and `git diff` shows them unchanged.
- **Test mistakes found while writing (not code faults):** my PATH-3 boundary case lengthened the last segment to 256 bytes, so it tested the
  segment limit instead of the path limit; and a huge-blob tiling case ran in Verify mode and hit LIM-5. Both tests were corrected.
- Verify: `pass_only AC-ENG-8; CHST_LIM2=… cargo_test_nonempty --release -p chst-cli --test task_reader -- reader_step_` exits 0
  (`reader_step_8`, `_9`, `_10`). clippy `-D warnings` over all targets and `cargo fmt --check` are clean.
- Clean-tree fast run at 1fdb8ad: 17 PASS, 46 FAIL, 3 NOT RUN, 19 N/A. The only status that changed is AC-ENG-8 (FAIL → PASS).
- EVIDENCE.md: the AC-ENG-8 row (Linux PASS, `local`). macOS and Windows stay NOT RUN until a CI run covers this commit.
- Open issues: none.
- Acceptance IDs affected: AC-ENG-8 (PASS on Linux).

### C-4 CI result — run 40733189070 (fast, commit 320e4c0)
- Complete 85-result reports on all three OSes, clean tree. **AC-ENG-8 is PASS on Linux, macOS and Windows**, so the pinned
  `unicode-normalization` 0.1.24 gives Unicode 16.0.0 tables everywhere. The jobs are red only at the "Job result" step, by design.
- Compared every status with EVIDENCE.md: AC-ENG-8 is the only change. AC-ROB-4, AC-ROB-4W and AC-ROB-7 are NOT RUN here because they're
  full-only; their rows keep full-mode run 40689182770.
- EVIDENCE.md: the AC-ENG-8 row now carries this run.
- Acceptance IDs affected: AC-ENG-8 (PASS on all three OSes).

### C-5 Step 11 and structured reports — 1652c9c
- Added `chst-format/src/blobs.rs`: `check_blobs`, §13 step 11. BLB-6 runs per blob in table order, and the first blob whose data doesn't
  match its key is reported as `integrity` / `blob.hash` (new detail constant; FORMAT_SPEC Appendix A already lists it). Data is read
  through one 64 KiB stack buffer (`BLOB_BUFFER_LEN`), so memory doesn't grow with a blob's size (G6). An input that ends inside a blob is
  `io.read`. A Core reader only ever sees stored blobs (BLB-2), so the ZST parts of step 11 never apply.
- Added `chst-format/src/report.rs`: `list`, `inspect` and `verify`, each from a `Read + Seek` source. List and inspect run steps 1 to 10
  with their own `Purpose` (so no LIM-5) and never step 11 (F34); verify runs all eleven. They return library values, and the CLI will
  render them (D13): list entries (path, type, size, stored size, encoding, key), the verify summary (counts, byte totals as `u128`, and flag
  names), and the inspect report (header, data region, every section with its fields and records, trailer). JSON encoding (number or
  decimal string, hex) is left to the CLI.
  - **What the reader implements shapes the report (F33).** Flag names follow `KNOWN_REQUIRED_FLAGS` and `KNOWN_OPTIONAL_FLAGS`: a bit
    gets its §12.1 name only if the reader implements it, so a Core reader names every set bit `bit<N>`. Section names are given only to
    the three required types, so KV_METADATA is `unknown`; entry records wider than 48 bytes show the rest as `extra`.
- `sections.rs` gained `section_headers`, an iterator over every section of a checked index (inspect also needs the ones after the
  required three). It allocates nothing.
- Tests: 12 new unit tests (5 in `blobs`, 7 in `report`), built on a test-only builder of complete files with real blob data and structure
  hashes. They cover blob order, changes at chunk boundaries, a source that records the largest read asked of it (at most 64 KiB), a
  truncated input, the summary's counting, flag naming with and without the reader implementing the flag, LIM-5 only for verify, and
  inspect covering every byte with values that equal the bytes they cover, including wider records and unknown sections with empty and
  non-empty payloads.
- `task_reader.rs`: `reader_step_11` (verify over all 128 files: 110 rejected, each with its exact detail, exit and category, and 18 pass)
  and `reports`. `reports` checks the 16 containers (10 `core/valid`, 6 exit-0 `compat`) as TODO.md says: list entries against
  `list.json` and verify summaries against `verify.json`. **Beyond TODO.md** it also compares each inspect report with `inspect.json`
  (`file_length`, `header`, `data`, `sections`, `trailer`), and it checks that list and inspect succeed on `core/invalid/BLB-6` while verify
  rejects it with `blob.hash`. The test renders the library values to JSON by Appendix B's rules itself, independently of the CLI.
- **Mutation checks: 43 mutants, all caught**, with the proposed `tools/mutants/mutate.py` and a `C-5.toml` suite (see "Needs decision";
  not committed). Commands: the `chst-format` unit tests, and `reader_step_` plus `reports`. What was mutated: BLB-6 off, wrong order,
  first blob only, seek one byte late, one byte short, whole blob buffered, chunk not capped, short read ignored, wrong category or
  detail; step 11 skipped by verify or run by list or inspect; LIM-5 for list or inspect, or not for verify; each summary count and total;
  optional flags named from the required bits; the known-flag check ignored or never true; wrong bit number; bit 63 missed; encoding
  inverted; key not listed; KV_METADATA named; empty payload shown; path pool as hex; `extra` dropped; record offset and index; data region
  length; a trailer offset; section offsets relative to the index; section length without the header; integers read big-endian;
  `minor_version` showing the major version; `stored_length` and `raw_length` swapped; `path_length` read as 8 bytes; and
  `section_headers` giving the payload start. 35 are caught by both commands, 7 only by the unit tests (blob order, the three G6 and short
  read mutants, LIM-5 for list and for inspect, and an implemented flag left unnamed), and 1 only by the fixtures (the swapped blob
  fields, whose values are equal in Core because BLB-3 makes them so).
  - **Not mutated, equivalent in Core:** `stored_bytes` summing `raw_length` and the list `size` using `stored_length`. BLB-3 makes the two
    lengths equal for every blob a Core reader accepts, so no test can tell them apart until ZSTD (Phase X).
  - **Failures along the way (real):** (1) one mutant didn't compile (my replacement for "extracted_bytes counts each blob once" was badly
    typed); I rewrote it, and it is caught. (2) **A bug in the runner:** it restored files with `shutil.copy2`, which keeps their old mtime,
    so cargo didn't rebuild after a restore and the next baseline ran the last mutant's build (three inspect unit tests failed on
    unmutated code, at the line `section-header-at` breaks). I found it because the baseline failed although the sources' SHA-256 matched
    the saved copies. Within a run the results were valid, since every mutant writes a new mtime and so forces a rebuild; only the state
    after a run was stale. The runner now restores contents only and sets a new mtime. I ran the whole suite again after the fix, and
    again after a final lint fix in the test file: 43 of 43 caught both times, sources byte-identical afterwards, and the unit tests pass
    on the restored code.
- Verify: `CHST_LIM2=$(fixture_file …) cargo_test_nonempty --release -p chst-cli --test task_reader -- reader_step_ reports` passes (5 tests:
  `reader_step_8` to `_11` and `reports`). clippy `-D warnings` over the workspace and all targets, and `cargo fmt --check`, are clean.
- Local fast run before committing: 17 PASS, 46 FAIL, 3 NOT RUN, 19 N/A; every status is the same as the Linux report of CI run 40733189070.
- C-5 has no acceptance ID of its own. EVIDENCE.md is unchanged.
- Open issues: the mutation-suite item under "Needs decision".
- Acceptance IDs affected: none directly (C-6a to C-6c build on these reports: AC-POS-2, AC-POS-3, AC-NEG-3, AC-CLI-3 and others).
- Clean-tree fast run at 1652c9c: 17 PASS, 46 FAIL, 3 NOT RUN, 19 N/A (exit 1, as expected while features are missing); the TODO coverage
  preflight passes with C-5 ticked. No status changed.

### Mutation suites in `tools/mutants/` — commit "C-5: mutation suites for C-3, C-4 and C-5"
Owner's choice (a) after the C-5 review. Not a TODO task; nothing in `check.sh`, ACCEPTANCE.md or EVIDENCE.md changes.
- **Added** `tools/mutants/mutate.py` (Python 3.14 standard library only) and three suites: `C-3.toml` (10 mutants on `sections.rs`),
  `C-4.toml` (113 on `tables.rs` and `paths.rs`) and `C-5.toml` (45 on `blobs.rs`, `report.rs` and `sections.rs`, 2 of them skipped).
  Each suite has two commands: the `chst-format` unit tests, and `task_reader`'s `reader_step_` and `reports` with `$CHST_LIM2`.
- **The runner now supports skipped mutants:** `skip = "<reason>"`. A skipped mutant isn't run, but its edits must still match the code,
  so it stays current, and every run lists it with its reason. C-5's two equivalent mutants are skipped this way (`stored_bytes` summing
  `raw_length`; the listed `size` being `stored_length`), each with "equivalent until stored and raw lengths can differ (ZSTD, Phase X)".
- **C-3 and C-4 are rebuilt, not copied.** Their mutation scripts were throwaway and weren't kept. C-3's ten are the ten PROGRESS.md
  describes. C-4's are rebuilt from its description, kind by kind, against the current code, so the list isn't C-4's original one and
  the count differs: 113 rather than 93. The extra ones are mostly more order swaps (17: 9 between step-10 items and 8 between adjacent path
  rules) and both directions of BLB-4 and CAN-3. The order swaps are cut at the code's `// (x)` and `// PATH-n` comments by a one-off
  generator in the session scratchpad; the committed suite is the generated TOML.
- **Results.** C-3: 10 of 10 caught (3 only by the unit tests, 1 only by the fixtures). C-5: 43 of 43 caught, 2 skipped. C-4, first run:
  **112 of 113, one survived:** `can2-advance-on-repeat` (CAN-2 counts a repeated reference to an earlier blob as a new blob, so a later
  out-of-order blob is accepted). It's a real gap in C-4's tests: none had a repeated reference *before* an out-of-order blob. I added that
  case to `can_2_orders_blobs_by_first_reference` (entries referencing blobs 0, 0, 2, 1); it passes on the real code and catches the mutant.
  Full C-4 re-run after the fix: **113 of 113 caught** (55 only by the unit tests, 1 only by the fixtures: `blb4-gap`, as in C-4).
  Sources were byte-identical after every run.
- **The rule for later tasks** is in TODO.md ("How this file works", "Mutation suites"). A CLAUDE.md diff is proposed under
  "Needs decision", because CLAUDE.md is protected.
- Acceptance IDs affected: none.

### C-6a CLI: argument parsing and `verify` — 8f2b4ce
- `chst-cli` now depends on `lexopt` 0.3 (0.3.2 in `Cargo.lock`, the only new package) and on `serde_json` as a normal dependency, both
  on D15's list. AC-ENG-5 and AC-ENG-3 pass.
- `src/args.rs`: `chst <command> FILE [--json] [limits]` with `lexopt`. The command must come first; options and FILE in any order after
  it; `--` ends the options. Limit flags take ASCII digits only, no sign, no whitespace, no leading zeros except a lone `0`, from 0 to
  2^64 − 1 (M12, N23); anything else, a missing value included, is `usage` / `usage.limit`. Every usage error exits 2 and opens nothing.
  `--json` is found by a scan before parsing (before any `--`), so a usage error is reported as JSON however the line is ordered.
- `src/render.rs`: reports through `serde_json::Value`: the common fields of Appendix B, the failure report with only those, and the verify
  `summary`. Integers beyond 2^53 − 1 become decimal strings. Text mode prints a one-line summary, plus a line for any flags set.
- `src/main.rs`: opens FILE (`io` / `io.read` if it can't, exit 3), runs `chst_format::verify` with the parsed limits, prints the report,
  and on failure writes `chst: error[<category>/<detail>]: <message>` as the first stderr line and exits with the category's code (§16).
  A stdout write failure is `io` / `io.write`. Nothing in the CLI panics on a broken pipe (no `println!`).
- The commands not implemented yet (`pack`, `list`, `inspect`, `extract`) fail as the C-1 stub did, with exit 70, a code no check expects.
- Detail codes not in the spec are under "Needs decision".
- Tests: 12 CLI unit tests (the parser, every M12 case and more, usage details, `--json` ordering, the renderer, `run` for JSON, text,
  limits and a missing file). By hand: every mode's output looks right; `verify --json` equals `verify.json` (message aside) for all 16
  containers that have one.
- **Mutation suite `tools/mutants/C-6a.toml`: 31 mutants.** Commands: the CLI unit tests, and the Verify line's `pass_only` over the
  nine IDs. First run: **30 of 31 caught; `json-ignored-on-success` survived** (verify printing text despite `--json`). No C-6a check reads
  a successful `verify --json`, and `run` had no unit test. I added three unit tests for `run`. Full re-run: **31 of 31 caught** (14 only by
  the unit tests, 4 only by the acceptance checks), sources byte-identical afterwards.
- Verify: `pass_only AC-ENG-3,AC-NEG-1,AC-NEG-2,AC-NEG-4,AC-CLI-1,AC-LIM-3,AC-ROB-1,AC-ROB-2,AC-ROB-8` passes (all nine PASS on the first
  run, before and after the test additions). clippy `-D warnings` over the workspace and `cargo fmt --check` are clean.
- Local fast run before committing: 24 PASS, 39 FAIL, 3 NOT RUN, 19 N/A. Changed from CI run 40733189070 (all FAIL → PASS): AC-NEG-2,
  AC-CLI-1, AC-LIM-3, AC-ROB-1, AC-ROB-2, AC-ROB-8, and **AC-DET-2**, which belongs to a later task but only runs `verify --json` on
  `dedup` and checks two counts, so it passes honestly and early.
- Open issues: the detail-code item under "Needs decision".
- Acceptance IDs affected: AC-NEG-2, AC-CLI-1, AC-LIM-3, AC-ROB-1, AC-ROB-2, AC-ROB-8 (PASS on Linux); AC-DET-2 (PASS early); AC-ENG-3,
  AC-NEG-1, AC-NEG-4 stay PASS.
- Clean-tree fast run at 8f2b4ce: 24 PASS, 39 FAIL, 3 NOT RUN, 19 N/A, the same as before committing. EVIDENCE.md: the seven rows that
  changed (AC-NEG-2, AC-CLI-1, AC-LIM-3, AC-ROB-1, AC-ROB-2, AC-ROB-8, AC-DET-2) now have Linux PASS (`local`); their macOS and Windows cells
  are NOT RUN until a CI run covers this commit (AC-LIM-3's stay N/A, its OS line being Linux only).
