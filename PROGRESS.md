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
