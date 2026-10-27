mkdir -p "$W/p"
expect_exit 9 $CHST extract $FX/core/extract-cases/unicode-case.chst -C "$W/p/out" 2> "$W/err"
grep -q 'error\[refused/extract.collision\]' "$W/err" && test -z "$(ls -A "$W/p")"
