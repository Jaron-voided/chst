# Chst — Progress

Append-only log, one entry per task. Results are in EVIDENCE.md, not here.

## Needs decision

- **AC-X-TS-2 has no script in ACCEPTANCE.md** (§3.13). I derived `tools/acceptance/checks/AC-X-TS-2.sh` from its prose (see H-4).
  Options: (a) keep the derived script; (b) have ACCEPTANCE.md state the script. Recommendation: (b) before the cut becomes
  Extended, so the script is the document's, not mine. It's N/A under Core, so nothing is blocked.

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
