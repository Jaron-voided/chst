mkdir -p "$W/t" && echo x > "$W/t/$(printf 'e\xcc\x81')"          # NFD é
$CHST pack "$W/t" -o "$W/c.chst"
$CHST list --json "$W/c.chst" | jq -e '[.entries[].path] == ["\u00e9"]'
$CHST extract "$W/c.chst" -C "$W/x"
python3.14 -I tools/acceptance/tree_eq.py --nfc "$W/t" "$W/x"
