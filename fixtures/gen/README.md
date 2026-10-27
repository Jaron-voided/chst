# Chst fixture generator

This is the independent test oracle (see `CLAUDE.md`, "Fixtures are the independent test
oracle"). It builds everything under `fixtures/` from `FORMAT_SPEC.md`, using the Python 3.14
standard library only: SHA-256 from `hashlib`, NFC from `unicodedata`. It shares no code with
the Rust implementation, and never runs it.

```
python3.14 -I fixtures/gen/gen.py                # rebuild fixtures/ (never touches gen/)
python3.14 -I fixtures/gen/gen.py --out DIR      # build into DIR (AC-META-5)
python3.14 -I fixtures/gen/gen.py materialize TREE.json DIR [--reverse]
python3.14 -I fixtures/gen/gen.py materialize-sparse RECIPE.json FILE
python3.14 -I fixtures/gen/gen.py synth-entries N FILE
python3.14 -I fixtures/gen/gen.py synth-amplify N SIZE FILE
python3.14 -I fixtures/gen/gen.py synth-zstd-bomb FILE
python3.14 -I fixtures/gen/gen.py worked-example-hexdump
```

| File | Role |
|---|---|
| `chst.py` | The format model (a Plan holds every on-disk field), canonical layout, serialization, and a Raw/RLE-only Zstandard frame writer |
| `catalog.py` | Every fixture: valid trees, and one mutation per bad fixture |
| `check.py` | A rule checker that follows FORMAT_SPEC §13. It's used only to prove the fixtures are what they claim to be. |
| `reports.py` | Expected `chst-report/1` JSON (Appendix B) for list, verify and inspect |
| `gen.py` | The command line. It also reads rule categories, detail codes and exit codes from FORMAT_SPEC.md Appendix A and §16. |

## Guarantees checked on every build

- **Valid fixtures:** the checker finds no violation, with an Extended reader and, for
  `core/valid`, with a Core-only reader too.
- **Bad fixtures:** each one changes one thing in a valid base. The **first** violation in
  FORMAT_SPEC §13's total order must be the targeted rule. That's the only one a conforming
  reader may report, so each `expect.json` has exactly one `detail`. Later violations, if
  any, are recorded in `also_violates` for information only.
- **No early stopping:** the checker evaluates every step-8 to step-11 rule it can, step 11
  included even after an earlier violation (N18), so co-violations are visible in
  `also_violates`. Two exceptions: a file that hits HDR-6 or SEC-2, for which nothing
  further is evaluated (§13); and a blob whose declared bytes run past the end of the file,
  which has nothing to hash.
- **Expected values come from the catalog:** for attacks and hostile fixtures, the expected
  rule is written in `catalog.py`, never taken from the checker's output.
- **Compatibility:** compat expectations are proven by running the checker as a Core-only
  reader (`reader="core"`). Their reports are that reader's view (Appendix B). Each
  `expect.json` also records, under `extended`, what a full (Extended) reader must give (M4).
- **Extended extract-cases:** `extended/extract-cases/zstd-corrupt-block` breaks both BLB-6 and
  ZST-2; the build proves its frame alone fails ZST-2, and that the file's first violation
  is BLB-6 (M2).
- **On-demand files:** `synth-zstd-bomb` writes a 32 MiB container whose zeros.bin frame would
  decode to 1 TiB (M6). It isn't stored, but every build constructs it and proves it's ZST-2.
- **Reaching the rule:** the structure hash is recomputed after every mutation, so the reader
  reaches the targeted rule (TRL-3's own fixture excepted). Blob keys and entry references
  are recomputed whenever stored bytes change.
- **Worked example:** `core/valid/worked-example/container.chst` must equal the hex dump in
  FORMAT_SPEC §18.3 byte for byte, or the build fails.
- **Reproducible output:** no timestamps, no unseeded randomness. Pseudo-random file content
  comes from SHA-256 in counter mode. `materialize --reverse` is seeded from
  `CHST_DET_SEED` (default `chst-det-1`) and prints the seed.
- **`MANIFEST.sha256`** lists every file under `fixtures/`, including this directory.

## Zstandard

- **The generator's own frames:** it writes Raw and RLE blocks only, independent of any
  zstd library.
- **One real Compressed-block frame:** `catalog.COMPRESSED_FRAME`, with a content checksum,
  was produced once by libzstd and is embedded as fixed bytes. It proves readers handle real
  compressed frames.
- **Checking frames:** the checker follows FORMAT_SPEC §13 step 11 (N1). It parses frame
  headers itself (RFC 8878: window, dictionary ID, content size), then walks the blocks
  with the output capped at `raw_length`, checking Block_Size against
  min(Window_Size, 128 KiB). It verifies content checksums with its own XXH64.
- **XXH64 cross-check, on every build:** for 79 sizes (0–64 bytes and 14 larger sizes up to
  1,000,000), a Raw-block frame carrying the checker's checksum must decode with libzstd,
  and the same frame with one checksum bit flipped must be rejected.
- **`compression.zstd`:** the standard library's libzstd binding is used only to decode:
  Compressed blocks, with the checksum flag cleared so the checksum is verified
  independently, and the XXH64 cross-check above. The generator never compresses with it.
  The build also asserts that the one embedded Compressed frame decodes to
  exactly `COMPRESSED_TEXT`. CPython includes this module only when built with libzstd;
  AC-ENG-6 checks that it's present (N19).

## Readings recorded for review

- **Conditions no fixture can reach**, because an earlier rule always fires first (listed in
  ACCEPTANCE AC-NEG-1):
  - FLG-1 for an encoded blob without the `ZSTD` flag (BLB-2 fires first).

  FLG-1 for `ENTRY_ATTRS` is one direction only since round 7 (N9), and is reachable:
  `FLG-1-attrs-short`.
- **LIM-2's fixture** is a sparse recipe (`core/invalid/LIM-2.recipe.json`), because the
  index has to exceed 2³² bytes. The generator proves it against steps 1–6, using only the
  header, the trailer and the file length.
