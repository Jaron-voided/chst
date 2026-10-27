$CHST list $FX/core/valid/nonprinting/container.chst > "$W/out.txt"
grep -qF 'zero\u{200b}width.txt' "$W/out.txt"
if LC_ALL=C grep -q $'\xe2\x80\x8b' "$W/out.txt"; then exit 1; fi    # the raw U+200B must not appear
