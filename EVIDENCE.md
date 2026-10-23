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
| AC-META-1 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-META-1 | — | — |
| AC-META-2 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-META-2 | — | — |
| AC-META-3 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-META-3 | — | — |
| AC-META-4 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-META-4 | — | — |
| AC-META-5 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-META-5 | — | — |
| AC-META-6 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-META-6 | — | — |
| AC-META-7 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-META-7 | — | — |
| AC-ENG-1 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-ENG-1 | — | — |
| AC-ENG-2 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-ENG-2 | — | — |
| AC-ENG-3 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-ENG-3 | — | — |
| AC-ENG-4 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-ENG-4 | — | — |
| AC-ENG-5 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-ENG-5 | — | — |
| AC-ENG-6 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-ENG-6 | — | — |
| AC-ENG-7 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-ENG-7 | — | — |
| AC-POS-1 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-POS-1 | — | — |
| AC-POS-2 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-POS-2 | — | — |
| AC-POS-3 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-POS-3 | — | — |
| AC-POS-4 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-POS-4 | — | — |
| AC-NEG-1 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-NEG-1 | — | — |
| AC-NEG-2 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-NEG-2 | — | — |
| AC-NEG-3 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-NEG-3 | — | — |
| AC-NEG-4 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-NEG-4 | — | — |
| AC-DET-1 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-DET-1 | — | — |
| AC-DET-2 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-DET-2 | — | — |
| AC-DET-3 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-DET-3 | — | — |
| AC-ROB-1 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-ROB-1 | — | — |
| AC-ROB-2 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-ROB-2 | — | — |
| AC-ROB-3 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-ROB-3 | — | — |
| AC-ROB-4 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-ROB-4 | — | — |
| AC-ROB-4W | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-ROB-4W | — | — |
| AC-ROB-5 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-ROB-5 | — | — |
| AC-ROB-6 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-ROB-6 | — | — |
| AC-ROB-7 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-ROB-7 | — | — |
| AC-ROB-8 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-ROB-8 | — | — |
| AC-ROB-9 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-ROB-9 | — | — |
| AC-SAFE-1 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-SAFE-1 | — | — |
| AC-SAFE-2 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-SAFE-2 | — | — |
| AC-SAFE-3 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-SAFE-3 | — | — |
| AC-SAFE-4 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-SAFE-4 | — | — |
| AC-SAFE-5 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-SAFE-5 | — | — |
| AC-SAFE-6 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-SAFE-6 | — | — |
| AC-SAFE-7 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-SAFE-7 | — | — |
| AC-SAFE-8 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-SAFE-8 | — | — |
| AC-SAFE-9 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-SAFE-9 | — | — |
| AC-SAFE-10 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-SAFE-10 | — | — |
| AC-SAFE-11 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-SAFE-11 | — | — |
| AC-PACK-1 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-PACK-1 | — | — |
| AC-PACK-2 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-PACK-2 | — | — |
| AC-PACK-3 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-PACK-3 | — | — |
| AC-PACK-4 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-PACK-4 | — | — |
| AC-PACK-6 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-PACK-6 | — | — |
| AC-PACK-7 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-PACK-7 | — | — |
| AC-PACK-8 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-PACK-8 | — | — |
| AC-PACK-9 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-PACK-9 | — | — |
| AC-PACK-5 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-PACK-5 | — | — |
| AC-LIM-1 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-LIM-1 | — | — |
| AC-LIM-2 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-LIM-2 | — | — |
| AC-LIM-4 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-LIM-4 | — | — |
| AC-LIM-3 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-LIM-3 | — | — |
| AC-CLI-1 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-CLI-1 | — | — |
| AC-CLI-2 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-CLI-2 | — | — |
| AC-COMPAT-1 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-COMPAT-1 | — | — |
| AC-XP-1 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-XP-1 | — | — |
| AC-XP-2 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-XP-2 | — | — |
| AC-X-NEG-1 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-X-NEG-1 | — | — |
| AC-X-ZSTD-1 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-X-ZSTD-1 | — | — |
| AC-X-ZSTD-2 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-X-ZSTD-2 | — | — |
| AC-X-ATTR-1 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-X-ATTR-1 | — | — |
| AC-X-ATTR-2 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-X-ATTR-2 | — | — |
| AC-X-KV-1 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-X-KV-1 | — | — |
| AC-X-SEL-1 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-X-SEL-1 | — | — |
| AC-X-EXCL-1 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-X-EXCL-1 | — | — |
| AC-X-TS-1 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-X-TS-1 | — | — |
| AC-X-TS-2 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-X-TS-2 | — | — |
| AC-X-TS-3 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-X-TS-3 | — | — |

_Initial state: no check has run yet, because `check.sh` doesn't exist. Every status is NOT RUN._
