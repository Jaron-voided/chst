mkdir -p "$W/t" "$W/outside" && echo secret > "$W/outside/s" && echo ok > "$W/t/f"
MSYS_NO_PATHCONV=1 cmd /c mklink /J "$(cygpath -w "$W/t/j")" "$(cygpath -w "$W/outside")"
expect_exit 0 $CHST pack --json "$W/t" -o "$W/c.chst" > "$W/r.json"
jq -e '[.warnings[] | .detail] == ["pack.skipped"] and .warnings[0].path == "j"' "$W/r.json"
test "$($CHST list --json "$W/c.chst" | jq -c '[.entries[].path]')" = '["f"]'
