mkdir -p "$W/t" && mkfifo "$W/t/p" && echo x > "$W/t/f"
expect_exit 0 $CHST pack --json "$W/t" -o "$W/c.chst" > "$W/r.json"
jq -e '.warnings[0].detail == "pack.skipped" and .summary.skipped == 1' "$W/r.json"
