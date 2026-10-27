$GEN synth-amplify 1000 65536 "$W/amp.chst"      # 1000 files sharing one 64 KiB blob
test "$(wc -c < "$W/amp.chst" | tr -d ' ')" -lt 200000
$CHST verify --json "$W/amp.chst" | jq -e '.summary.blobs == 1 and .summary.raw_bytes == 65536 and .summary.extracted_bytes == 65536000'
mkdir -p "$W/p"
expect_exit 8 $CHST extract --max-total-bytes 65535999 "$W/amp.chst" -C "$W/p/out" 2> "$W/err"
grep -q 'error\[limit-exceeded/limit.total-size\]' "$W/err" && test -z "$(ls -A "$W/p")"
expect_exit 0 $CHST extract --max-total-bytes 65536000 "$W/amp.chst" -C "$W/p/out"
