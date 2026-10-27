# Review 3 demonstration artifacts

These are the round-8 reviewer's scripts and demonstration files, copied unchanged from the
reviewer's working folder (only `__pycache__/` and a build log were left out), so later
reviewers can re-run them.

**Spec version.** They were written against FORMAT_SPEC, ACCEPTANCE and the fixtures at
commit `51c6a39`, which matches the round-7 text of commit `3853421`. That's *before* the
round-8 fixes (M1–M15).
- `rdr8.py`'s default `flg1='spec'` mode encodes the old two-way FLG-1 text. Pass
  `flg1='closure'` for the one-way rule FORMAT_SPEC now states (M4).
- `rdr8.py` is a reader only, so it has no extract behaviour (M1, M2, M5). Its LIM-6
  arithmetic is exact, because Python integers are, which is what M3 now requires.

**Paths.** Several scripts hardcode
`/home/jaron/projects/container-format-rs/fixtures` (and `fixtures/gen`): `adv.py`,
`adv2.py`, `describe.py`, `fuzz11.py`, `lax_oneshot.py`, `lim6_overflow.py`,
`bomb_uncapped.py`. Edit those to re-run them elsewhere. Run everything from this folder with
`python3.14`.

| File | What it is |
|---|---|
| `rdr8.py` | The reviewer's spec-only reader (an update of round 7's `rdr.py`) |
| `rdr7_orig.py` | Round 7's reader, unchanged |
| `run8.py` | Runs every fixture group: `python3.14 run8.py ../../fixtures spec\|closure`. It writes a 4 GiB **sparse** file `sparse-LIM-2` into this folder for the LIM-2 recipe; delete it afterwards. |
| `mk.py` | The reviewer's independent container and frame builder |
| `adv.py`, `adv2.py`, `adv/` | 36 crafted frames for N1's determinism (31 files in `adv/`); `adv/T.chst` and `adv/U.chst` are M7's cases |
| `fuzz11.py` | A 5,860-case differential over mutated frames |
| `describe.py` | Decodes every ZST and LIM-6 fixture frame |
| `n2_race.py` | M1: a spec-literal EXT-4 skeleton with a racing parent-writer (runs in its own temporary directory) |
| `blb6_vs_zst.py`, `M-early-corrupt.chst`, `M-bitflip-compressed.chst` | M2 |
| `lim6_overflow.py` | M3 |
| `n17_handle.py` | M5: `fchmod` on a mode-000 directory (runs in its own temporary directory) |
| `bomb_uncapped.py` | M6 |
| `lax_oneshot.py` | M7 |
| `A.chst`, `B.chst`, `C.chst`, `flg1-*.chst` | Copies of the round-7 files (see `../review-2-artifacts/`) |
