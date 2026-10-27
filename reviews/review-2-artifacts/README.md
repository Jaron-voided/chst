# Review 2 demonstration artifacts

Copied unchanged from the round-7 reviewer's working folder, so later reviewers can re-run them.

- `A.chst`, `B.chst`, `C.chst`: the N1 demonstration (ZST-1/ZST-2 order).
- `flg1-attrs-rs48.chst`, `flg1-noattrs-rs64.chst`: the N9 demonstration (FLG-1 reachability).
- `rdr.py`: the reviewer's spec-only reader. It implements FORMAT_SPEC as it stood *before*
  the round-7 fixes, so its step-11 order and FLG-1 check predate N1 and N9.
  Use: `python3.14 -c "import rdr; r = rdr.check(open('A.chst','rb').read()); print(rdr.first(r))"`
