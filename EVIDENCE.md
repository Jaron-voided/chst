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
| AC-META-1 | PASS | PASS | PASS | ./check.sh --only AC-META-1 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-META-2 | PASS | PASS | PASS | ./check.sh --only AC-META-2 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-META-3 | PASS | PASS | PASS | ./check.sh --only AC-META-3 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-META-4 | PASS | PASS | PASS | ./check.sh --only AC-META-4 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-META-5 | PASS | N/A | N/A | ./check.sh --only AC-META-5 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-META-6 | PASS | PASS | PASS | ./check.sh --only AC-META-6 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-META-7 | PASS | PASS | PASS | ./check.sh --only AC-META-7 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-ENG-1 | PASS | PASS | PASS | ./check.sh --only AC-ENG-1 | 8543aa65e18edab129667ec22f1e6e7cbc982d5f | https://github.com/Jaron-voided/chst/actions/runs/40694068794 |
| AC-ENG-2 | PASS | PASS | PASS | ./check.sh --only AC-ENG-2 | 3025d6212bfbdc33e58e24113124502743d090b7 | https://github.com/Jaron-voided/chst/actions/runs/40699772200 |
| AC-ENG-3 | PASS | PASS | PASS | ./check.sh --only AC-ENG-3 | 8543aa65e18edab129667ec22f1e6e7cbc982d5f | https://github.com/Jaron-voided/chst/actions/runs/40694068794 |
| AC-ENG-4 | PASS | PASS | PASS | ./check.sh --only AC-ENG-4 | 3025d6212bfbdc33e58e24113124502743d090b7 | https://github.com/Jaron-voided/chst/actions/runs/40699772200 |
| AC-ENG-5 | PASS | PASS | PASS | ./check.sh --only AC-ENG-5 | 8543aa65e18edab129667ec22f1e6e7cbc982d5f | https://github.com/Jaron-voided/chst/actions/runs/40694068794 |
| AC-ENG-6 | PASS | PASS | PASS | ./check.sh --only AC-ENG-6 | 8543aa65e18edab129667ec22f1e6e7cbc982d5f | https://github.com/Jaron-voided/chst/actions/runs/40694068794 |
| AC-ENG-8 | PASS | PASS | PASS | ./check.sh --only AC-ENG-8 | 320e4c031af91719ae572f623ed47d3794294268 | https://github.com/Jaron-voided/chst/actions/runs/40733189070 |
| AC-ENG-7 | FAIL | FAIL | FAIL | ./check.sh --only AC-ENG-7 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-POS-1 | FAIL | FAIL | FAIL | ./check.sh --only AC-POS-1 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-POS-2 | FAIL | FAIL | FAIL | ./check.sh --only AC-POS-2 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-POS-3 | FAIL | FAIL | FAIL | ./check.sh --only AC-POS-3 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-POS-4 | FAIL | FAIL | FAIL | ./check.sh --only AC-POS-4 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-NEG-1 | PASS | PASS | PASS | ./check.sh --only AC-NEG-1 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-NEG-2 | PASS | NOT RUN | NOT RUN | ./check.sh --only AC-NEG-2 | 8f2b4ce73dbc8e1c2cb7c599a9a5107fd7eafd2c | local |
| AC-NEG-3 | FAIL | FAIL | FAIL | ./check.sh --only AC-NEG-3 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-NEG-4 | PASS | PASS | PASS | ./check.sh --only AC-NEG-4 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-DET-1 | FAIL | FAIL | FAIL | ./check.sh --only AC-DET-1 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-DET-2 | PASS | NOT RUN | NOT RUN | ./check.sh --only AC-DET-2 | 8f2b4ce73dbc8e1c2cb7c599a9a5107fd7eafd2c | local |
| AC-DET-3 | FAIL | FAIL | FAIL | ./check.sh --only AC-DET-3 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-ROB-1 | PASS | NOT RUN | NOT RUN | ./check.sh --only AC-ROB-1 | 8f2b4ce73dbc8e1c2cb7c599a9a5107fd7eafd2c | local |
| AC-ROB-2 | PASS | NOT RUN | NOT RUN | ./check.sh --only AC-ROB-2 | 8f2b4ce73dbc8e1c2cb7c599a9a5107fd7eafd2c | local |
| AC-ROB-3 | FAIL | FAIL | FAIL | ./check.sh --only AC-ROB-3 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-ROB-4 | FAIL | FAIL | N/A | ./check.sh --only AC-ROB-4 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-ROB-4W | N/A | N/A | FAIL | ./check.sh --only AC-ROB-4W | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-ROB-5 | FAIL | FAIL | FAIL | ./check.sh --only AC-ROB-5 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-ROB-6 | FAIL | N/A | N/A | ./check.sh --only AC-ROB-6 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-ROB-7 | FAIL | FAIL | FAIL | ./check.sh --only AC-ROB-7 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-ROB-8 | PASS | NOT RUN | NOT RUN | ./check.sh --only AC-ROB-8 | 8f2b4ce73dbc8e1c2cb7c599a9a5107fd7eafd2c | local |
| AC-ROB-9 | FAIL | FAIL | FAIL | ./check.sh --only AC-ROB-9 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-SAFE-1 | FAIL | FAIL | FAIL | ./check.sh --only AC-SAFE-1 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-SAFE-2 | FAIL | FAIL | FAIL | ./check.sh --only AC-SAFE-2 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-SAFE-3 | FAIL | FAIL | FAIL | ./check.sh --only AC-SAFE-3 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-SAFE-4 | FAIL | FAIL | N/A | ./check.sh --only AC-SAFE-4 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-SAFE-5 | N/A | FAIL | FAIL | ./check.sh --only AC-SAFE-5 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-SAFE-6 | FAIL | N/A | N/A | ./check.sh --only AC-SAFE-6 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-SAFE-7 | FAIL | FAIL | FAIL | ./check.sh --only AC-SAFE-7 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-SAFE-8 | FAIL | FAIL | FAIL | ./check.sh --only AC-SAFE-8 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-SAFE-9 | N/A | N/A | FAIL | ./check.sh --only AC-SAFE-9 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-SAFE-10 | N/A | N/A | FAIL | ./check.sh --only AC-SAFE-10 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-SAFE-11 | N/A | FAIL | N/A | ./check.sh --only AC-SAFE-11 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-SAFE-12 | FAIL | FAIL | FAIL | ./check.sh --only AC-SAFE-12 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-SAFE-13 | FAIL | FAIL | FAIL | ./check.sh --only AC-SAFE-13 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-SAFE-14 | FAIL | FAIL | FAIL | ./check.sh --only AC-SAFE-14 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-SAFE-15 | FAIL | FAIL | FAIL | ./check.sh --only AC-SAFE-15 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-PACK-1 | FAIL | N/A | N/A | ./check.sh --only AC-PACK-1 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-PACK-2 | FAIL | FAIL | N/A | ./check.sh --only AC-PACK-2 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-PACK-3 | FAIL | FAIL | FAIL | ./check.sh --only AC-PACK-3 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-PACK-4 | FAIL | FAIL | N/A | ./check.sh --only AC-PACK-4 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-PACK-6 | FAIL | FAIL | FAIL | ./check.sh --only AC-PACK-6 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-PACK-7 | N/A | N/A | FAIL | ./check.sh --only AC-PACK-7 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-PACK-8 | N/A | N/A | FAIL | ./check.sh --only AC-PACK-8 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-PACK-9 | FAIL | N/A | N/A | ./check.sh --only AC-PACK-9 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-PACK-5 | FAIL | FAIL | FAIL | ./check.sh --only AC-PACK-5 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-PACK-10 | FAIL | FAIL | FAIL | ./check.sh --only AC-PACK-10 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-PACK-11 | FAIL | FAIL | FAIL | ./check.sh --only AC-PACK-11 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-PACK-12 | FAIL | FAIL | FAIL | ./check.sh --only AC-PACK-12 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-LIM-1 | FAIL | FAIL | FAIL | ./check.sh --only AC-LIM-1 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-LIM-2 | FAIL | FAIL | FAIL | ./check.sh --only AC-LIM-2 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-LIM-4 | FAIL | FAIL | FAIL | ./check.sh --only AC-LIM-4 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-LIM-3 | PASS | N/A | N/A | ./check.sh --only AC-LIM-3 | 8f2b4ce73dbc8e1c2cb7c599a9a5107fd7eafd2c | local |
| AC-CLI-1 | PASS | NOT RUN | NOT RUN | ./check.sh --only AC-CLI-1 | 8f2b4ce73dbc8e1c2cb7c599a9a5107fd7eafd2c | local |
| AC-CLI-2 | FAIL | FAIL | N/A | ./check.sh --only AC-CLI-2 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-CLI-3 | FAIL | FAIL | FAIL | ./check.sh --only AC-CLI-3 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-COMPAT-1 | FAIL | FAIL | FAIL | ./check.sh --only AC-COMPAT-1 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-XP-1 | NOT RUN | NOT RUN | NOT RUN | ./check.sh --only AC-XP-1 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-XP-2 | PASS | PASS | PASS | ./check.sh --only AC-XP-2 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-X-NEG-1 | N/A | N/A | N/A | ./check.sh --only AC-X-NEG-1 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-X-ZSTD-1 | N/A | N/A | N/A | ./check.sh --only AC-X-ZSTD-1 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-X-ZSTD-2 | N/A | N/A | N/A | ./check.sh --only AC-X-ZSTD-2 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-X-ATTR-1 | N/A | N/A | N/A | ./check.sh --only AC-X-ATTR-1 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-X-ATTR-2 | N/A | N/A | N/A | ./check.sh --only AC-X-ATTR-2 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-X-ATTR-3 | N/A | N/A | N/A | ./check.sh --only AC-X-ATTR-3 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-X-KV-1 | N/A | N/A | N/A | ./check.sh --only AC-X-KV-1 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-X-SEL-1 | N/A | N/A | N/A | ./check.sh --only AC-X-SEL-1 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-X-EXCL-1 | N/A | N/A | N/A | ./check.sh --only AC-X-EXCL-1 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-X-TS-1 | N/A | N/A | N/A | ./check.sh --only AC-X-TS-1 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-X-TS-2 | N/A | N/A | N/A | ./check.sh --only AC-X-TS-2 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
| AC-X-TS-3 | N/A | N/A | N/A | ./check.sh --only AC-X-TS-3 | b94ca4141da1c9e56858828e491caffa580eb3d2 | https://github.com/Jaron-voided/chst/actions/runs/40689182770 |
