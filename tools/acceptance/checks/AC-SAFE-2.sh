mkdir -p "$W/out" && echo keep > "$W/out/k"
expect_exit 9 $CHST extract $FX/core/valid/worked-example/container.chst -C "$W/out" 2> "$W/err"
grep -q 'error\[refused/extract.dest-exists\]' "$W/err"
test "$(ls -A "$W/out")" = k && test "$(cat "$W/out/k")" = keep
if [ "$CHST_OS" != windows ]; then                       # F16: a dangling symlink also "exists"
  ln -s "$W/nowhere" "$W/link"
  expect_exit 9 $CHST extract $FX/core/valid/worked-example/container.chst -C "$W/link"
  test -L "$W/link" && test ! -e "$W/nowhere"
fi
