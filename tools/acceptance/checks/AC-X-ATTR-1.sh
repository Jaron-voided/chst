mkdir -p "$W/t" && echo x > "$W/t/f" && chmod 4755 "$W/t/f" && touch -d @1700000000.5 "$W/t/f"
$CHST pack --attrs "$W/t" -o "$W/c.chst"
$CHST list --json "$W/c.chst" | jq -e '.entries[0].mode == 493 and .entries[0].mtime_seconds == 1700000000 and .entries[0].mtime_nanos == 500000000'
$CHST extract "$W/c.chst" -C "$W/x"
test "$(stat -c %a "$W/x/f")" = 755
# F27: modes are applied as stored (not subject to umask); a read-only directory doesn't block
# its children; directory mtimes survive their children being written.
mkdir -p "$W/u/ro" && echo y > "$W/u/ro/g" && chmod 600 "$W/u/ro/g" && touch -d @1600000000 "$W/u/ro" && chmod 555 "$W/u/ro"
$CHST pack --attrs "$W/u" -o "$W/u.chst"
(umask 077; $CHST extract "$W/u.chst" -C "$W/y")
test "$(stat -c %a "$W/y/ro")" = 555 && test "$(stat -c %a "$W/y/ro/g")" = 600
test "$(stat -c %Y "$W/y/ro")" = 1600000000
chmod 755 "$W/u/ro" "$W/y/ro"
