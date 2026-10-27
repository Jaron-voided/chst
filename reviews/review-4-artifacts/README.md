# Review 4 demonstration artifacts

These are the round-9 reviewer's new scripts and outputs, copied unchanged from its working
folder. Its other inputs were unchanged copies of the round-8 files, which are in
`../review-3-artifacts/`. The scripts here are self-contained: `run9.py` and `extra9.py`
import only `rdr9.py`, which is in this folder.

**Spec version.** These scripts were written against commit `259e8dc`, which is *before*
the round-9 fixes (P1–P5).
- `p1_chmod_race.py` models the old EXT-4: staging set to `0755 & ~umask` before the rename.
  After P1, staging stays 0700 until after the rename, so the attack it demonstrates no
  longer applies to a spec-following extractor.
- `p2_setgid_umask.py` models the old "permission bits exactly 0700" check, before P2's
  `fchmod` and `& 0o777`.

**Paths.** `extra9.py` hardcodes `/home/jaron/projects/container-format-rs/fixtures`. Run
everything with `python3.14`. `p1_chmod_race.py` and `p2_setgid_umask.py` create
temporary directories (`p1-*`, `p1probe-*`, `p2-*`) next to themselves.

| File | What it is |
|---|---|
| `rdr9.py` | `rdr8.py` with FLG-1 made one-way, matching FORMAT_SPEC from round 8 on |
| `run9.py` | Runs every fixture group, including the compat Extended view and `extended/extract-cases`: `python3.14 -I run9.py <fixtures>`. It writes a 4 GiB **sparse** file `sparse-LIM-2` next to itself; delete it afterwards. |
| `extra9.py` | The time bomb, the LIM-6 boundary under exact, wrapping, checked and saturating multiplies (P3), the M7 one-shot decodes, and `zstd-corrupt-block`. It needs `tb.chst`: `python3.14 -I ../../fixtures/gen/gen.py synth-zstd-bomb tb.chst` |
| `p1_chmod_race.py`, `p1_chmod_race.out` | P1: the check-then-chmod race in cleanup, with rustix-style and glibc paths |
| `p2_setgid_umask.py`, `p2_setgid_umask.out` | P2: the exact-0700 check under a setgid parent and under umask 0277 |
