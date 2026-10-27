z=crates/chst-format/tests/zstd_bombs.rs          # AC-ENG-7 skips a missing allocator user; this MUST NOT
test -f $z                                         # exists
grep -q 'counting_alloc' $z                        # registered with the counting allocator
grep -qx '#!\[deny(unsafe_code)\]' $z              # AC-ENG-7 part 3
grep -nw 'unsafe' $z > "$W/zu" || true             # AC-ENG-7 part 5: no unsafe beyond the deny line
if grep -vE '^[0-9]+:#!\[deny\(unsafe_code\)\]$' "$W/zu"; then exit 1; fi
cargo_test_nonempty --release -p chst-format --test zstd_bombs   # at least one real test runs and passes
for t in ZST-2-window:6:zstd.frame ZST-2-dictid:6:zstd.frame ZST-1:7:zstd.raw-length LIM-6:8:limit.ratio \
         ZST-2-no-fcs-overflow:6:zstd.frame ZST-2-bomb:6:zstd.frame; do
  IFS=: read -r n code det <<< "$t"
  set +e; /usr/bin/time -f '%M' -o "$W/rss" timeout 10 $CHST verify --json $FX/extended/invalid/$n.chst > "$W/r.json"; rc=$?; set -e
  test $rc = $code && test "$(jq -r .error.detail "$W/r.json")" = "$det"
  test "$(cat "$W/rss")" -lt 65536                                      # peak RSS < 64 MiB, C allocations included
done
$GEN synth-zstd-bomb "$W/tb.chst"                                      # M6: 1 TiB of output in 32 MiB
set +e; /usr/bin/time -f '%M' -o "$W/rss" timeout 10 $CHST verify --json "$W/tb.chst" > "$W/r.json"; rc=$?; set -e
test $rc = 6 && test "$(jq -r .error.detail "$W/r.json")" = zstd.frame
test "$(cat "$W/rss")" -lt 65536
expect_exit 0 $CHST verify --max-ratio 18446744073709551615 $FX/extended/valid/zstd-compressed/container.chst   # M3
expect_exit 0 $CHST verify --max-ratio 54738112978366623 $FX/extended/valid/zstd-compressed/container.chst      # P3
