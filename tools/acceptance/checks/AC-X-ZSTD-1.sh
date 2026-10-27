for d in $FX/extended/valid/zstd-*/; do
  rm -rf "$W/t" "$W/x"; $GEN materialize "$d/tree.json" "$W/t"
  $CHST pack --compress zstd "$W/t" -o "$W/c.chst"
  diff <($CHST list --json "$W/c.chst" | jq -S '[.entries[] | {path,type,size,encoding}]') \
       <(jq -S '[.entries[] | {path,type,size,encoding}]' "$d/list.json")
  $CHST extract "$W/c.chst" -C "$W/x" && python3.14 -I tools/acceptance/tree_eq.py "$W/t" "$W/x"
done
mkdir -p "$W/big" && head -c 2097152 /dev/zero > "$W/big/zeros.bin"      # N8: over 1000:1 when compressed
$CHST pack --compress zstd "$W/big" -o "$W/big.chst"
$CHST list --json "$W/big.chst" | jq -e '.entries[0].encoding == "stored"'
$CHST verify "$W/big.chst"
e=$FX/extended/extract-cases/zstd-corrupt-block                        # M2: verify and extract agree
expect_exit 7 $CHST verify $e.chst
mkdir -p "$W/p" && expect_exit 7 $CHST extract $e.chst -C "$W/p/out" 2> "$W/err"
grep -q 'error\[integrity/blob.hash\]' "$W/err" && test -z "$(ls -A "$W/p")"
