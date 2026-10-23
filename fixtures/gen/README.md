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

- **Valid fixtures:** the checker finds no violation.
- **Bad fixtures:** each one changes one thing in a valid base, and the checker finds the
  targeted rule and nothing else. The only exceptions are where the spec makes a second
  violation unavoidable; those list every acceptable detail in `details`.
- **Reaching the rule:** the structure hash is recomputed after every mutation, so the reader
  reaches the targeted rule (TRL-3's own fixture excepted). Blob keys and entry references
  are recomputed whenever stored bytes change.
- **Worked example:** `core/valid/worked-example/container.chst` must equal the hex dump in
  FORMAT_SPEC §18.3 byte for byte, or the build fails.
- **Reproducible output:** no timestamps, no unseeded randomness. Pseudo-random file content
  comes from SHA-256 in counter mode.
- **`MANIFEST.sha256`** lists every file under `fixtures/`, including this directory.

## Choices the spec left open

The independent review should confirm or reject each of these.

1. **inspect report shape.** Appendix B defines `inspect` only loosely. The generator emits:
   - `header`, `data`, `sections[]` and `trailer`, each with `offset`, `length` and
     `fields[]` entries of `{name, offset, length, value}`;
   - per-record `records[]` for BLOB_TABLE and ENTRY_TABLE;
   - a single `payload` field for byte sections; KV_METADATA's payload is hex;
   - `data.fields[]` with one `blob[i].data` field per blob, which has no `value`.

   Together the fields cover every byte exactly once, which AC-POS-3 relies on.
2. **CAN-2 and unreferenced blobs.** CAN-2 is read as applying to referenced blobs, which
   must come first and in first-reference order. Unreferenced blobs are BLB-7's concern
   only. With that reading, the BLB-5 (duplicate key) and BLB-7 fixtures each break one rule.
3. **Zstandard frames** are written with Raw and RLE blocks only. They're valid RFC 8878
   frames (libzstd decodes them), deterministic, and independent of libzstd. Fixture trees
   are chosen so both this writer and a real compressor make the same stored-or-compressed
   decision: long zero runs compress, while random data and tiny files stay stored.
4. **Unavoidable double violations** (recorded in each fixture's `details`):
   - ENT-5 together with CAN-3;
   - PATH-4 together with PATH-3 (an empty segment) and ENT-6;
   - PATH-5 together with PATH-8 (`.` and `..` end in a dot);
   - the hostile64 path-offset trap (ENT-5 together with CAN-3).
5. **Rules with no small single-violation fixture.**
   - **LIM-1:** an entry count over 2³²−1 can't fit within SEC-1's bounds in a small file,
     and SEC-1 is checked first.
   - **LIM-2:** an index over 2³² bytes needs a file of over 4 GiB.

   Both are reported as open items instead of being faked.
6. **FLG-1 and LIM-6** concern Extended features (flags, encoded blobs), so their fixtures
   live under `extended/invalid/`.
