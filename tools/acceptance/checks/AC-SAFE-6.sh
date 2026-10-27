expect_exit 0 $CHST extract $FX/core/extract-cases/unicode-case.chst -C "$W/x"
test -f "$W/x/é" && test -f "$W/x/É"
