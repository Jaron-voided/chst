mkdir -p "$W/t/logs" "$W/t/src" && echo a > "$W/t/src/a.rs" && echo b > "$W/t/x.log" && echo c > "$W/t/logs/y"
$CHST pack --exclude '*.log' --exclude 'logs' "$W/t" -o "$W/c.chst"
test "$($CHST list --json "$W/c.chst" | jq -c '[.entries[].path]')" = '["src","src/a.rs"]'
if [ "$CHST_OS" = linux ]; then                    # F26: excluded names are never checked (W-3) or descended
  touch "$W/t/logs/a:b"; chmod 000 "$W/t/logs"
  expect_exit 0 $CHST pack --exclude 'logs' --exclude '*.log' "$W/t" -o "$W/d.chst"
  chmod 755 "$W/t/logs"
fi
