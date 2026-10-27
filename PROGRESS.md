# Chst — Progress

Append-only log, one entry per task. Results are in EVIDENCE.md, not here.

## Needs decision

- **AC-X-TS-2 has no script in ACCEPTANCE.md** (§3.13). I derived \`tools/acceptance/checks/AC-X-TS-2.sh\` from its prose (see H-4).
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
