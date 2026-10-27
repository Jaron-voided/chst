mkdir -p "$W/t" "$W/o" "$W/o2" && touch "$W/t/a:b"
echo original > "$W/o/c.chst"
expect_exit 9 $CHST pack --force "$W/t" -o "$W/o/c.chst"
test "$(ls -A "$W/o")" = c.chst && test "$(cat "$W/o/c.chst")" = original
expect_exit 9 $CHST pack "$W/t" -o "$W/o2/c.chst"
test -z "$(ls -A "$W/o2")"
