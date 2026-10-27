mkdir -p "$W/t" && printf 'ok\n' > "$W/t/f"
powershell -NoProfile -Command "Set-Content -LiteralPath '$(cygpath -w "$W/t/f")' -Stream s -Value hidden"
$CHST pack "$W/t" -o "$W/c.chst"
$CHST list --json "$W/c.chst" | jq -e '[.entries[] | {path, size}] == [{"path":"f","size":3}]'
