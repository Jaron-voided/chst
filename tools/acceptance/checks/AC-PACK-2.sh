mkdir -p "$W/t" "$W/outside" && echo secret > "$W/outside/s" && echo ok > "$W/t/f"
ln -s "$W/outside" "$W/t/link" && mkfifo "$W/t/fifo"
expect_exit 0 $CHST pack "$W/t" -o "$W/c.chst" 2> "$W/err"
test "$(grep -c 'pack.skipped' "$W/err")" -eq 2
test "$($CHST list --json "$W/c.chst" | jq -c '[.entries[].path]')" = '["f"]'
