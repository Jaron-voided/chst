d=$FX/core/valid/worked-example
$GEN materialize $d/tree.json "$W/t" && echo original > "$W/c.chst" && mkdir "$W/dir.chst"
expect_exit 9 $CHST pack "$W/t" -o "$W/c.chst" 2> "$W/err"
grep -q 'error\[refused/pack.output-exists\]' "$W/err" && test "$(cat "$W/c.chst")" = original
expect_exit 0 $CHST pack --force "$W/t" -o "$W/c.chst" && cmp "$W/c.chst" $d/container.chst
expect_exit 9 $CHST pack --force "$W/t" -o "$W/dir.chst" && test -d "$W/dir.chst"
