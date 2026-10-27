mkdir -p "$W/p"
expect_exit 7 $CHST extract $FX/core/extract-cases/late-blob-hash.chst -C "$W/p/out" 2> "$W/err"
grep -q 'error\[integrity/blob.hash\]' "$W/err"
test -z "$(ls -A "$W/p")"
cargo_test_nonempty --release -p chst-fs --features test-hooks --test late_failure
