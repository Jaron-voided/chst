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
| AC-META-1 | PASS | PASS | PASS | ./check.sh --only AC-META-1 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-META-2 | PASS | PASS | PASS | ./check.sh --only AC-META-2 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-META-3 | PASS | PASS | PASS | ./check.sh --only AC-META-3 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-META-4 | PASS | PASS | PASS | ./check.sh --only AC-META-4 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-META-5 | PASS | N/A | N/A | ./check.sh --only AC-META-5 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-META-6 | PASS | PASS | PASS | ./check.sh --only AC-META-6 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-META-7 | PASS | PASS | PASS | ./check.sh --only AC-META-7 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-ENG-1 | FAIL | FAIL | FAIL | ./check.sh --only AC-ENG-1 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-ENG-2 | FAIL | FAIL | FAIL | ./check.sh --only AC-ENG-2 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-ENG-3 | FAIL | FAIL | FAIL | ./check.sh --only AC-ENG-3 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-ENG-4 | FAIL | FAIL | FAIL | ./check.sh --only AC-ENG-4 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-ENG-5 | FAIL | FAIL | FAIL | ./check.sh --only AC-ENG-5 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-ENG-6 | FAIL | FAIL | FAIL | ./check.sh --only AC-ENG-6 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-ENG-8 | FAIL | FAIL | FAIL | ./check.sh --only AC-ENG-8 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-ENG-7 | FAIL | FAIL | FAIL | ./check.sh --only AC-ENG-7 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-POS-1 | FAIL | FAIL | FAIL | ./check.sh --only AC-POS-1 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-POS-2 | FAIL | FAIL | FAIL | ./check.sh --only AC-POS-2 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-POS-3 | FAIL | FAIL | FAIL | ./check.sh --only AC-POS-3 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-POS-4 | FAIL | FAIL | FAIL | ./check.sh --only AC-POS-4 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-NEG-1 | PASS | PASS | PASS | ./check.sh --only AC-NEG-1 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-NEG-2 | FAIL | FAIL | FAIL | ./check.sh --only AC-NEG-2 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-NEG-3 | FAIL | FAIL | FAIL | ./check.sh --only AC-NEG-3 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-NEG-4 | PASS | PASS | PASS | ./check.sh --only AC-NEG-4 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-DET-1 | FAIL | FAIL | FAIL | ./check.sh --only AC-DET-1 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-DET-2 | FAIL | FAIL | FAIL | ./check.sh --only AC-DET-2 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-DET-3 | FAIL | FAIL | FAIL | ./check.sh --only AC-DET-3 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-ROB-1 | FAIL | FAIL | FAIL | ./check.sh --only AC-ROB-1 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-ROB-2 | FAIL | FAIL | FAIL | ./check.sh --only AC-ROB-2 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-ROB-3 | FAIL | FAIL | FAIL | ./check.sh --only AC-ROB-3 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-ROB-4 | NOT RUN | NOT RUN | N/A | ./check.sh --only AC-ROB-4 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-ROB-4W | N/A | N/A | NOT RUN | ./check.sh --only AC-ROB-4W | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-ROB-5 | FAIL | FAIL | FAIL | ./check.sh --only AC-ROB-5 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-ROB-6 | FAIL | N/A | N/A | ./check.sh --only AC-ROB-6 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-ROB-7 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-ROB-7 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-ROB-8 | FAIL | FAIL | FAIL | ./check.sh --only AC-ROB-8 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-ROB-9 | FAIL | FAIL | FAIL | ./check.sh --only AC-ROB-9 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-SAFE-1 | FAIL | FAIL | FAIL | ./check.sh --only AC-SAFE-1 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-SAFE-2 | FAIL | FAIL | FAIL | ./check.sh --only AC-SAFE-2 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-SAFE-3 | FAIL | FAIL | FAIL | ./check.sh --only AC-SAFE-3 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-SAFE-4 | FAIL | FAIL | N/A | ./check.sh --only AC-SAFE-4 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-SAFE-5 | N/A | FAIL | FAIL | ./check.sh --only AC-SAFE-5 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-SAFE-6 | FAIL | N/A | N/A | ./check.sh --only AC-SAFE-6 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-SAFE-7 | FAIL | FAIL | FAIL | ./check.sh --only AC-SAFE-7 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-SAFE-8 | FAIL | FAIL | FAIL | ./check.sh --only AC-SAFE-8 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-SAFE-9 | N/A | N/A | FAIL | ./check.sh --only AC-SAFE-9 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-SAFE-10 | N/A | N/A | FAIL | ./check.sh --only AC-SAFE-10 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-SAFE-11 | N/A | FAIL | N/A | ./check.sh --only AC-SAFE-11 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-SAFE-12 | FAIL | FAIL | FAIL | ./check.sh --only AC-SAFE-12 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-SAFE-13 | FAIL | FAIL | FAIL | ./check.sh --only AC-SAFE-13 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-SAFE-14 | FAIL | FAIL | FAIL | ./check.sh --only AC-SAFE-14 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-SAFE-15 | FAIL | FAIL | FAIL | ./check.sh --only AC-SAFE-15 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-PACK-1 | FAIL | N/A | N/A | ./check.sh --only AC-PACK-1 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-PACK-2 | FAIL | FAIL | N/A | ./check.sh --only AC-PACK-2 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-PACK-3 | FAIL | FAIL | FAIL | ./check.sh --only AC-PACK-3 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-PACK-4 | FAIL | FAIL | N/A | ./check.sh --only AC-PACK-4 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-PACK-6 | FAIL | FAIL | FAIL | ./check.sh --only AC-PACK-6 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-PACK-7 | N/A | N/A | FAIL | ./check.sh --only AC-PACK-7 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-PACK-8 | N/A | N/A | FAIL | ./check.sh --only AC-PACK-8 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-PACK-9 | FAIL | N/A | N/A | ./check.sh --only AC-PACK-9 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-PACK-5 | FAIL | FAIL | FAIL | ./check.sh --only AC-PACK-5 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-PACK-10 | FAIL | FAIL | FAIL | ./check.sh --only AC-PACK-10 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-PACK-11 | FAIL | FAIL | FAIL | ./check.sh --only AC-PACK-11 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-PACK-12 | FAIL | FAIL | FAIL | ./check.sh --only AC-PACK-12 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-LIM-1 | FAIL | FAIL | FAIL | ./check.sh --only AC-LIM-1 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-LIM-2 | FAIL | FAIL | FAIL | ./check.sh --only AC-LIM-2 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-LIM-4 | FAIL | FAIL | FAIL | ./check.sh --only AC-LIM-4 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-LIM-3 | FAIL | N/A | N/A | ./check.sh --only AC-LIM-3 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-CLI-1 | FAIL | FAIL | FAIL | ./check.sh --only AC-CLI-1 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-CLI-2 | FAIL | FAIL | N/A | ./check.sh --only AC-CLI-2 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-CLI-3 | FAIL | FAIL | FAIL | ./check.sh --only AC-CLI-3 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-COMPAT-1 | FAIL | FAIL | FAIL | ./check.sh --only AC-COMPAT-1 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-XP-1 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-XP-1 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-XP-2 | PASS | PASS | PASS | ./check.sh --only AC-XP-2 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-X-NEG-1 | N/A | N/A | N/A | ./check.sh --only AC-X-NEG-1 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-X-ZSTD-1 | N/A | N/A | N/A | ./check.sh --only AC-X-ZSTD-1 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-X-ZSTD-2 | N/A | N/A | N/A | ./check.sh --only AC-X-ZSTD-2 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-X-ATTR-1 | N/A | N/A | N/A | ./check.sh --only AC-X-ATTR-1 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-X-ATTR-2 | N/A | N/A | N/A | ./check.sh --only AC-X-ATTR-2 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-X-ATTR-3 | N/A | N/A | N/A | ./check.sh --only AC-X-ATTR-3 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-X-KV-1 | N/A | N/A | N/A | ./check.sh --only AC-X-KV-1 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-X-SEL-1 | N/A | N/A | N/A | ./check.sh --only AC-X-SEL-1 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-X-EXCL-1 | N/A | N/A | N/A | ./check.sh --only AC-X-EXCL-1 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-X-TS-1 | N/A | N/A | N/A | ./check.sh --only AC-X-TS-1 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-X-TS-2 | N/A | N/A | N/A | ./check.sh --only AC-X-TS-2 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
| AC-X-TS-3 | N/A | N/A | N/A | ./check.sh --only AC-X-TS-3 | c091a7285d221c2ea4a79db256f766cc0b19ded5 | https://github.com/Jaron-voided/chst/actions/runs/40592564145 |
