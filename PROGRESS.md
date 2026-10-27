# Chst — Progress

Append-only log, one entry per task. Results are in EVIDENCE.md, not here.

## Needs decision

(none yet)

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
