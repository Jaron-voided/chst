mkdir -p "$W/t" && echo x > "$W/t/f"
$CHST pack --meta creator=me --meta comment='hi there' "$W/t" -o "$W/k.chst"
$CHST inspect --json "$W/k.chst" | jq -e '[.sections[].name] == ["BLOB_TABLE","ENTRY_TABLE","PATH_POOL","KV_METADATA"]'
$CHST pack "$W/t" -o "$W/n.chst"
$CHST inspect --json "$W/n.chst" | jq -e '[.sections[].name] | index("KV_METADATA") == null'
