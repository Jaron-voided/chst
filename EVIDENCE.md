# Chst — Evidence

This is the only record of check results. Its format and rules are defined in
[`ACCEPTANCE.md`](ACCEPTANCE.md) §2.1, and AC-XP-1 checks it mechanically.

- There's exactly one row per acceptance ID, in ACCEPTANCE.md order.
- Status cells use exactly PASS, FAIL, NOT RUN or N/A, and are copied from `report.json`.
  Nothing is marked PASS unless its check ran.
- **macOS and Windows statuses come only from the CI run linked in the row.** The Linux
  status may come from that run, or from a local WSL run, noted as `local` in the CI run
  column.

| ID | Linux | macOS | Windows | Command | Commit | CI run |
|---|---|---|---|---|---|---|
| AC-META-1 | PASS | NOT RUN | NOT RUN | ./check.sh --only AC-META-1 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-META-2 | PASS | NOT RUN | NOT RUN | ./check.sh --only AC-META-2 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-META-3 | PASS | NOT RUN | NOT RUN | ./check.sh --only AC-META-3 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-META-4 | PASS | NOT RUN | NOT RUN | ./check.sh --only AC-META-4 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-META-5 | PASS | NOT RUN | NOT RUN | ./check.sh --only AC-META-5 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-META-6 | PASS | NOT RUN | NOT RUN | ./check.sh --only AC-META-6 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-META-7 | PASS | NOT RUN | NOT RUN | ./check.sh --only AC-META-7 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-ENG-1 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-ENG-1 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-ENG-2 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-ENG-2 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-ENG-3 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-ENG-3 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-ENG-4 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-ENG-4 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-ENG-5 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-ENG-5 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-ENG-6 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-ENG-6 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-ENG-8 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-ENG-8 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-ENG-7 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-ENG-7 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-POS-1 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-POS-1 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-POS-2 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-POS-2 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-POS-3 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-POS-3 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-POS-4 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-POS-4 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-NEG-1 | PASS | NOT RUN | NOT RUN | ./check.sh --only AC-NEG-1 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-NEG-2 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-NEG-2 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-NEG-3 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-NEG-3 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-NEG-4 | PASS | NOT RUN | NOT RUN | ./check.sh --only AC-NEG-4 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-DET-1 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-DET-1 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-DET-2 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-DET-2 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-DET-3 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-DET-3 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-ROB-1 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-ROB-1 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-ROB-2 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-ROB-2 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-ROB-3 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-ROB-3 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-ROB-4 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-ROB-4 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-ROB-4W | N/A | NOT RUN | NOT RUN | ./check.sh --only AC-ROB-4W | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-ROB-5 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-ROB-5 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-ROB-6 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-ROB-6 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-ROB-7 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-ROB-7 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-ROB-8 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-ROB-8 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-ROB-9 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-ROB-9 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-SAFE-1 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-SAFE-1 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-SAFE-2 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-SAFE-2 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-SAFE-3 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-SAFE-3 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-SAFE-4 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-SAFE-4 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-SAFE-5 | N/A | NOT RUN | NOT RUN | ./check.sh --only AC-SAFE-5 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-SAFE-6 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-SAFE-6 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-SAFE-7 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-SAFE-7 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-SAFE-8 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-SAFE-8 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-SAFE-9 | N/A | NOT RUN | NOT RUN | ./check.sh --only AC-SAFE-9 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-SAFE-10 | N/A | NOT RUN | NOT RUN | ./check.sh --only AC-SAFE-10 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-SAFE-11 | N/A | NOT RUN | NOT RUN | ./check.sh --only AC-SAFE-11 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-SAFE-12 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-SAFE-12 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-SAFE-13 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-SAFE-13 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-SAFE-14 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-SAFE-14 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-SAFE-15 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-SAFE-15 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-PACK-1 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-PACK-1 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-PACK-2 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-PACK-2 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-PACK-3 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-PACK-3 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-PACK-4 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-PACK-4 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-PACK-6 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-PACK-6 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-PACK-7 | N/A | NOT RUN | NOT RUN | ./check.sh --only AC-PACK-7 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-PACK-8 | N/A | NOT RUN | NOT RUN | ./check.sh --only AC-PACK-8 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-PACK-9 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-PACK-9 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-PACK-5 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-PACK-5 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-PACK-10 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-PACK-10 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-PACK-11 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-PACK-11 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-PACK-12 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-PACK-12 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-LIM-1 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-LIM-1 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-LIM-2 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-LIM-2 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-LIM-4 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-LIM-4 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-LIM-3 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-LIM-3 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-CLI-1 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-CLI-1 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-CLI-2 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-CLI-2 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-CLI-3 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-CLI-3 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-COMPAT-1 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-COMPAT-1 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-XP-1 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-XP-1 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-XP-2 | PASS | NOT RUN | NOT RUN | ./check.sh --only AC-XP-2 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-X-NEG-1 | N/A | NOT RUN | NOT RUN | ./check.sh --only AC-X-NEG-1 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-X-ZSTD-1 | N/A | NOT RUN | NOT RUN | ./check.sh --only AC-X-ZSTD-1 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-X-ZSTD-2 | N/A | NOT RUN | NOT RUN | ./check.sh --only AC-X-ZSTD-2 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-X-ATTR-1 | N/A | NOT RUN | NOT RUN | ./check.sh --only AC-X-ATTR-1 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-X-ATTR-2 | N/A | NOT RUN | NOT RUN | ./check.sh --only AC-X-ATTR-2 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-X-ATTR-3 | N/A | NOT RUN | NOT RUN | ./check.sh --only AC-X-ATTR-3 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-X-KV-1 | N/A | NOT RUN | NOT RUN | ./check.sh --only AC-X-KV-1 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-X-SEL-1 | N/A | NOT RUN | NOT RUN | ./check.sh --only AC-X-SEL-1 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-X-EXCL-1 | N/A | NOT RUN | NOT RUN | ./check.sh --only AC-X-EXCL-1 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-X-TS-1 | N/A | NOT RUN | NOT RUN | ./check.sh --only AC-X-TS-1 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-X-TS-2 | N/A | NOT RUN | NOT RUN | ./check.sh --only AC-X-TS-2 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |
| AC-X-TS-3 | N/A | NOT RUN | NOT RUN | ./check.sh --only AC-X-TS-3 | d677036c965f85307ff2f1e7457165211bcae6c8 | local |

_Initial state: no check has run yet, because `check.sh` doesn't exist. Every status is NOT RUN._
