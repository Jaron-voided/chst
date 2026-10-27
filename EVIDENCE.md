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
| AC-META-1 | PASS | NOT RUN | NOT RUN | ./check.sh --only AC-META-1 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-META-2 | PASS | NOT RUN | NOT RUN | ./check.sh --only AC-META-2 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-META-3 | PASS | NOT RUN | NOT RUN | ./check.sh --only AC-META-3 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-META-4 | PASS | NOT RUN | NOT RUN | ./check.sh --only AC-META-4 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-META-5 | PASS | NOT RUN | NOT RUN | ./check.sh --only AC-META-5 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-META-6 | PASS | NOT RUN | NOT RUN | ./check.sh --only AC-META-6 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-META-7 | PASS | NOT RUN | NOT RUN | ./check.sh --only AC-META-7 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-ENG-1 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-ENG-1 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-ENG-2 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-ENG-2 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-ENG-3 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-ENG-3 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-ENG-4 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-ENG-4 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-ENG-5 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-ENG-5 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-ENG-6 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-ENG-6 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-ENG-8 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-ENG-8 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-ENG-7 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-ENG-7 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-POS-1 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-POS-1 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-POS-2 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-POS-2 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-POS-3 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-POS-3 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-POS-4 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-POS-4 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-NEG-1 | PASS | NOT RUN | NOT RUN | ./check.sh --only AC-NEG-1 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-NEG-2 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-NEG-2 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-NEG-3 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-NEG-3 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-NEG-4 | PASS | NOT RUN | NOT RUN | ./check.sh --only AC-NEG-4 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-DET-1 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-DET-1 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-DET-2 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-DET-2 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-DET-3 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-DET-3 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-ROB-1 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-ROB-1 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-ROB-2 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-ROB-2 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-ROB-3 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-ROB-3 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-ROB-4 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-ROB-4 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-ROB-4W | N/A | NOT RUN | NOT RUN | ./check.sh --only AC-ROB-4W | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-ROB-5 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-ROB-5 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-ROB-6 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-ROB-6 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-ROB-7 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-ROB-7 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-ROB-8 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-ROB-8 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-ROB-9 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-ROB-9 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-SAFE-1 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-SAFE-1 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-SAFE-2 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-SAFE-2 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-SAFE-3 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-SAFE-3 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-SAFE-4 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-SAFE-4 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-SAFE-5 | N/A | NOT RUN | NOT RUN | ./check.sh --only AC-SAFE-5 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-SAFE-6 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-SAFE-6 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-SAFE-7 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-SAFE-7 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-SAFE-8 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-SAFE-8 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-SAFE-9 | N/A | NOT RUN | NOT RUN | ./check.sh --only AC-SAFE-9 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-SAFE-10 | N/A | NOT RUN | NOT RUN | ./check.sh --only AC-SAFE-10 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-SAFE-11 | N/A | NOT RUN | NOT RUN | ./check.sh --only AC-SAFE-11 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-SAFE-12 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-SAFE-12 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-SAFE-13 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-SAFE-13 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-SAFE-14 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-SAFE-14 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-SAFE-15 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-SAFE-15 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-PACK-1 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-PACK-1 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-PACK-2 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-PACK-2 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-PACK-3 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-PACK-3 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-PACK-4 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-PACK-4 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-PACK-6 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-PACK-6 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-PACK-7 | N/A | NOT RUN | NOT RUN | ./check.sh --only AC-PACK-7 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-PACK-8 | N/A | NOT RUN | NOT RUN | ./check.sh --only AC-PACK-8 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-PACK-9 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-PACK-9 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-PACK-5 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-PACK-5 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-PACK-10 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-PACK-10 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-PACK-11 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-PACK-11 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-PACK-12 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-PACK-12 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-LIM-1 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-LIM-1 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-LIM-2 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-LIM-2 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-LIM-4 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-LIM-4 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-LIM-3 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-LIM-3 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-CLI-1 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-CLI-1 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-CLI-2 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-CLI-2 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-CLI-3 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-CLI-3 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-COMPAT-1 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-COMPAT-1 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-XP-1 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-XP-1 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-XP-2 | FAIL | NOT RUN | NOT RUN | ./check.sh --only AC-XP-2 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-X-NEG-1 | N/A | NOT RUN | NOT RUN | ./check.sh --only AC-X-NEG-1 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-X-ZSTD-1 | N/A | NOT RUN | NOT RUN | ./check.sh --only AC-X-ZSTD-1 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-X-ZSTD-2 | N/A | NOT RUN | NOT RUN | ./check.sh --only AC-X-ZSTD-2 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-X-ATTR-1 | N/A | NOT RUN | NOT RUN | ./check.sh --only AC-X-ATTR-1 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-X-ATTR-2 | N/A | NOT RUN | NOT RUN | ./check.sh --only AC-X-ATTR-2 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-X-ATTR-3 | N/A | NOT RUN | NOT RUN | ./check.sh --only AC-X-ATTR-3 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-X-KV-1 | N/A | NOT RUN | NOT RUN | ./check.sh --only AC-X-KV-1 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-X-SEL-1 | N/A | NOT RUN | NOT RUN | ./check.sh --only AC-X-SEL-1 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-X-EXCL-1 | N/A | NOT RUN | NOT RUN | ./check.sh --only AC-X-EXCL-1 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-X-TS-1 | N/A | NOT RUN | NOT RUN | ./check.sh --only AC-X-TS-1 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-X-TS-2 | N/A | NOT RUN | NOT RUN | ./check.sh --only AC-X-TS-2 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |
| AC-X-TS-3 | N/A | NOT RUN | NOT RUN | ./check.sh --only AC-X-TS-3 | 200f44bf052cc4b52753ce75868d3bf79b70c34c | local |

_Initial state: no check has run yet, because `check.sh` doesn't exist. Every status is NOT RUN._
