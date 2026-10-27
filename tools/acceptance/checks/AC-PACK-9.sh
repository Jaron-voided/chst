mkdir -p "$W/a" "$W/b"; touch "$W/a/$(printf 'e\xcc\x81')"
$CHST pack "$W/a" -o "$W/a.chst"
$CHST list --json "$W/a.chst" | jq -e '[.entries[].path] == ["\u00e9"]'
touch "$W/b/$(printf 'e\xcc\x81')" "$W/b/$(printf '\xc3\xa9')"
expect_exit 9 $CHST pack "$W/b" -o "$W/b.chst" 2> "$W/err" && grep -q pack.unportable-name "$W/err"
