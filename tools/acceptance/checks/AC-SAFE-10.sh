f=$FX/core/extract-cases/short-name.chst; mkdir -p "$W/p"
vol=$(cygpath -w "$W" | cut -c1-2)
fsutil 8dot3name set "$vol" 0                                # enable 8.3 names on this volume (runner is admin)
fsutil 8dot3name query "$vol"                                # logged
expect_exit 9 $CHST extract "$f" -C "$W/p/out" 2> "$W/err"
grep -q 'error\[refused/extract.collision\]' "$W/err" && test -z "$(ls -A "$W/p")"
